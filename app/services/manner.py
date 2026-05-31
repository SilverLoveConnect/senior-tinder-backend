from sqlalchemy.orm import Session

from app.models.manner import MannerHistory, MannerFactorEnum
from app.models.user import User, UserProfile, MannerGradeEnum


def update_manner_score(
    db: Session, user: User, factor: MannerFactorEnum, delta: int, reason: str
) -> None:
    history = MannerHistory(
        user_id=user.id,
        factor=factor,
        delta=delta,
        reason=reason,
    )
    db.add(history)

    new_score = max(0, min(100, user.profile.manner_score + delta))
    user.profile.manner_score = new_score

    user.profile.manner_grade = recalculate_manner_grade(user.profile)

    db.flush()


def recalculate_manner_grade(user_profile: UserProfile) -> MannerGradeEnum:
    score = user_profile.manner_score
    if score >= 90:
        return MannerGradeEnum.gold
    elif score >= 70:
        return MannerGradeEnum.silver
    else:
        return MannerGradeEnum.normal
