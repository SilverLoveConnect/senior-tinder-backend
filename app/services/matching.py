from uuid import UUID

from sqlalchemy.orm import Session
from app.models.user import UserProfile
from sqlalchemy import and_, func, or_
from app.models.user import User
from app.models.matching import Like, Block, LikeStatusEnum, Match, ChatRoom, ChatMessage
from fastapi import HTTPException, status

from app.services.fcm import notify_new_match


def blocked_user_ids(db: Session, user: User):
    """user와 차단 관계로 얽힌 모든 상대의 id.

    차단은 양방향으로 취급한다 — 내가 차단한 사람뿐 아니라 나를 차단한 사람도
    서로 노출되지 않아야 차단이 실효를 갖는다(한쪽만 거르면 차단당한 쪽 피드에는
    상대가 계속 뜨고, 좋아요를 보내 매칭까지 성사시킬 수 있다).
    """
    return (
        db.query(Block.blocked_id)
        .filter(Block.blocker_id == user.id)
        .union(db.query(Block.blocker_id).filter(Block.blocked_id == user.id))
        .scalar_subquery()
    )


def _parse_cursor(cursor: str) -> tuple[int, str] | None:
    """커서 "<trust_score>:<user_id>" 를 분해한다. 형식이 깨졌으면 None."""
    score, _, user_id = cursor.partition(":")
    if not user_id:
        return None
    try:
        return int(score), user_id
    except ValueError:
        return None


def get_matching_users(
    db: Session,
    current_user: User,
    cursor: str | None,
    size: int,
    min_age: int | None,
    max_age: int | None,
    region: str | None,
) -> dict:
    query = db.query(User).join(UserProfile, User.id == UserProfile.user_id).filter(
        User.id != current_user.id,
        User.is_active == True,
        User.is_banned == False,
        User.gender != current_user.gender,
    )

    query = query.filter(User.id.notin_(blocked_user_ids(db, current_user)))

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

    # 커서는 정렬키(trust_score DESC, id ASC)와 같은 축으로 잘라야 한다.
    # id만으로 자르면 "점수는 낮지만 id가 작은" 유저가 어느 페이지에도
    # 들어가지 못하고 영구히 누락된다.
    if cursor is not None:
        parsed = _parse_cursor(cursor)
        if parsed is not None:
            cursor_score, cursor_id = parsed
            query = query.filter(
                or_(
                    UserProfile.trust_score < cursor_score,
                    and_(
                        UserProfile.trust_score == cursor_score,
                        User.id > cursor_id,
                    ),
                )
            )

    query = query.order_by(UserProfile.trust_score.desc(), User.id.asc())
    users = query.limit(size + 1).all()

    has_next = len(users) > size

    if has_next:
        users = users[:size]

    next_cursor = None
    if has_next and users:
        last = users[-1]
        last_score = last.profile.trust_score if last.profile else 50
        next_cursor = f"{last_score}:{last.id}"

    result_users = [
        {
            "id": user.id,
            "nickname": user.nickname or user.name,
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
    # 차단 관계면 좋아요 자체를 막는다. 피드에서 걸러도 API를 직접 부르면
    # 매칭이 성사돼 채팅방까지 생기므로 여기서도 검사해야 한다.
    blocked = (
        db.query(Block)
        .filter(
            or_(
                and_(
                    Block.blocker_id == current_user.id,
                    Block.blocked_id == target_user_id,
                ),
                and_(
                    Block.blocker_id == target_user_id,
                    Block.blocked_id == current_user.id,
                ),
            )
        )
        .first()
    )
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="차단된 회원입니다.",
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

        return {
            "is_matched": True,
            "match_id": str(match.id),
            "chat_room_id": str(chat_room.id),
        }

    db.commit()
    return {"is_matched": False, "match_id": None, "chat_room_id": None}


def get_matches(db: Session, current_user: User) -> dict:
    # 차단한(또는 나를 차단한) 상대와의 대화는 목록에서 사라져야 한다 —
    # 앱이 차단 시 "서로 추천과 대화에 더 이상 나타나지 않아요"라고 안내한다.
    blocked_ids = blocked_user_ids(db, current_user)

    matches = (
        db.query(Match)
        .filter(
            or_(Match.user1_id == current_user.id, Match.user2_id == current_user.id),
            Match.user1_id.notin_(blocked_ids),
            Match.user2_id.notin_(blocked_ids),
        )
        .all()
    )

    # 나간 대화는 목록에 남지 않는다 (chat.leave_room이 is_active를 내린다)
    matches = [m for m in matches if m.chat_room is None or m.chat_room.is_active]

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
                    "nickname": opponent.nickname or opponent.name,
                    "age": opponent.age,
                    "region": opponent.region,
                    "trust_grade": (
                        opponent.profile.trust_grade if opponent.profile else "normal"
                    ),
                    # 대화 목록·채팅방에 상대 얼굴을 띄우려면 사진이 필요하다.
                    # 없어서 앱이 전원 기본 아이콘(👤)으로 그리고 있었다.
                    "photo": next(
                        (p.s3_url for p in opponent.photos if p.is_approved), None
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
