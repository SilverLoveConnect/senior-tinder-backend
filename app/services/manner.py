from sqlalchemy.orm import Session

from app.models.manner import MannerHistory, MannerFactorEnum
from app.models.user import User, UserProfile, MannerGradeEnum


def update_trust_score(
    db: Session, user: User, factor: MannerFactorEnum, delta: int, reason: str
) -> None:
    history = MannerHistory(
        user_id=user.id,
        factor=factor,
        delta=delta,
        reason=reason,
    )
    db.add(history)

    new_score = max(0, min(100, user.profile.trust_score + delta))
    user.profile.trust_score = new_score

    user.profile.trust_grade = recalculate_trust_grade(user.profile)

    db.flush()


def recalculate_trust_grade(
    user_profile: UserProfile, report_count: int = 0
) -> MannerGradeEnum:
    score = user_profile.trust_score
    if report_count >= 3:
        return MannerGradeEnum.warning
    if score >= 90:
        return MannerGradeEnum.gold
    elif score >= 70:
        return MannerGradeEnum.silver
    else:
        return MannerGradeEnum.normal
