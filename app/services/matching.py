from uuid import UUID

from sqlalchemy.orm import Session
from app.models.user import UserProfile
from sqlalchemy import or_
from app.models.user import User
from app.models.matching import Like, Block, LikeStatusEnum, Match, ChatRoom
from fastapi import HTTPException, status


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
        UserProfile.manner_score.desc(), User.id.asc()
    )
    users = query.limit(size + 1).all()

    has_next = len(users) > size

    if has_next:
        users = users[:size]

    next_cursor = str(users[-1].id) if has_next else None

    return {
        "users": users,
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

        chat_room = ChatRoom(match_id=match.id, supabase_channel=match.id)
        db.add(chat_room)
        db.commit()
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
    result = []
    for match in matches:

        opponent = match.user2 if match.user1_id == current_user.id else match.user1

        result.append(
            {
                "match_id": match.id,
                "user": {
                    "id": opponent.id,
                    "name": opponent.name,
                    "age": opponent.age,
                    "region": opponent.region,
                    "manner_grade": (
                        opponent.profile.manner_grade if opponent.profile else "normal"
                    ),
                },
                "matched_at": match.matched_at,
                "chat_room_id": match.chat_room.id,
            }
        )

    return {"matches": result}
