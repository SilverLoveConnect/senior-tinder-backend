from uuid import UUID

from sqlalchemy.orm import Session
from app.models.user import UserProfile

from app.models.user import User
from app.models.matching import Like, Block


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
