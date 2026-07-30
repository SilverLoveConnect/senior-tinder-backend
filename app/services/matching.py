from uuid import UUID

from sqlalchemy.orm import Session
from app.models.user import UserProfile
from sqlalchemy import func, or_
from app.models.user import User
from app.models.matching import Like, Block, LikeStatusEnum, Match, ChatRoom, ChatMessage
from fastapi import HTTPException, status

from app.services.fcm import notify_new_match


def get_matching_users(
    db: Session,
    current_user: User,
    cursor: str | None,
    size: int,
    min_age: int | None,
    max_age: int | None,
    region: str | None,
) -> dict:
    query = db.query(User).filter(
        User.id != current_user.id,
        User.is_active == current_user.is_active,
        User.is_banned == False,
        User.gender != current_user.gender,
    )
    blocked_ids = (
        db.query(Block.blocked_id)
        .filter(Block.blocker_id == current_user.id)
        .scalar_subquery()
    )

    query = query.filter(User.id.notin_(blocked_ids))

    liked_ids = (
        db.query(Like.to_user_id)
        .filter(Like.from_user_id == current_user.id)
        .scalar_subquery()
    )
    query = query.filter(User.id.notin_(liked_ids))

    if min_age is not None:
        query = query.filter(User.age >= min_age)
    if max_age is not None:
        query = query.filter(User.age <= max_age)
    if region is not None:
        query = query.filter(User.region == region)
    if cursor is not None:
        query = query.filter(User.id > cursor)

    query = query.join(UserProfile, User.id == UserProfile.user_id).order_by(
        UserProfile.trust_score.desc(), User.id.asc()
    )
    users = query.limit(size + 1).all()

    has_next = len(users) > size

    if has_next:
        users = users[:size]

    next_cursor = str(users[-1].id) if has_next else None

    result_users = [
        {
            "id": user.id,
            "nickname": user.name,
            "age": user.age,
            "region": user.region,
            "bio": user.profile.bio if user.profile else None,
            "interests": user.profile.interests if user.profile else None,
            "trust_score": user.profile.trust_score if user.profile else 50,
            "trust_grade": user.profile.trust_grade if user.profile else "normal",
            "is_verified": user.profile.is_verified if user.profile else False,
            "photos": [p.s3_url for p in user.photos if p.is_approved],
        }
        for user in users
    ]

    return {
        "users": result_users,
        "next_cursor": next_cursor,
        "has_next": has_next,
    }


def like_user(db: Session, current_user: User, target_user_id: str) -> dict:
    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="존재하지 않는 유저입니다."
        )
    existing_like = (
        db.query(Like)
        .filter(Like.from_user_id == current_user.id, Like.to_user_id == target_user_id)
        .first()
    )
    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 좋아요를 보낸 유저입니다.",
        )

    like = Like(from_user_id=current_user.id, to_user_id=target_user_id)
    db.add(like)
    db.flush()

    reverse_like = (
        db.query(Like)
        .filter(
            Like.from_user_id == target_user_id,
            Like.to_user_id == current_user.id,
            Like.status == LikeStatusEnum.pending,
        )
        .first()
    )

    if reverse_like:
        like.status = LikeStatusEnum.matched
        reverse_like.status = LikeStatusEnum.matched

        match = Match(user1_id=current_user.id, user2_id=target_user_id)
        db.add(match)
        db.flush()

        chat_room = ChatRoom(match_id=match.id, supabase_channel=str(match.id))
        db.add(chat_room)
        db.commit()

        if target_user.fcm_token:
            notify_new_match(
                token=target_user.fcm_token,
                matched_user_nickname=current_user.nickname or current_user.name,
            )

        return {"is_matched": True, "match_id": str(match.id)}

    db.commit()
    return {"is_matched": False, "match_id": None}


def get_matches(db: Session, current_user: User) -> dict:
    matches = (
        db.query(Match)
        .filter(
            or_(Match.user1_id == current_user.id, Match.user2_id == current_user.id)
        )
        .all()
    )

    if not matches:
        return {"matches": []}

    room_ids = [match.chat_room.id for match in matches if match.chat_room]

    # 채팅방별 최근 메시지 1건 — DISTINCT ON으로 room당 한 번씩 조회 (N+1 방지)
    last_message_by_room: dict[UUID, tuple[str, object]] = {}
    if room_ids:
        last_message_rows = (
            db.query(
                ChatMessage.room_id,
                ChatMessage.content,
                ChatMessage.created_at,
            )
            .filter(ChatMessage.room_id.in_(room_ids))
            .order_by(ChatMessage.room_id, ChatMessage.created_at.desc())
            .distinct(ChatMessage.room_id)
            .all()
        )
        last_message_by_room = {
            row.room_id: (row.content, row.created_at) for row in last_message_rows
        }

    # 채팅방별 안 읽은 메시지 수 — 단일 GROUP BY 쿼리로 조회 (N+1 방지)
    unread_count_by_room: dict[UUID, int] = {}
    if room_ids:
        unread_rows = (
            db.query(ChatMessage.room_id, func.count(ChatMessage.id))
            .filter(
                ChatMessage.room_id.in_(room_ids),
                ChatMessage.is_read == False,
                ChatMessage.sender_id != current_user.id,
            )
            .group_by(ChatMessage.room_id)
            .all()
        )
        unread_count_by_room = {row[0]: row[1] for row in unread_rows}

    result = []
    for match in matches:

        opponent = match.user2 if match.user1_id == current_user.id else match.user1
        chat_room_id = match.chat_room.id if match.chat_room else None
        last_message, last_message_at = last_message_by_room.get(
            chat_room_id, (None, None)
        )

        result.append(
            {
                "match_id": match.id,
                "user": {
                    "id": opponent.id,
                    "nickname": opponent.name,
                    "age": opponent.age,
                    "region": opponent.region,
                    "trust_grade": (
                        opponent.profile.trust_grade if opponent.profile else "normal"
                    ),
                },
                "matched_at": match.matched_at,
                "chat_room_id": chat_room_id,
                "last_message": last_message,
                "last_message_at": last_message_at,
                "unread_count": unread_count_by_room.get(chat_room_id, 0),
            }
        )

    return {"matches": result}
