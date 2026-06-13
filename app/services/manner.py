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


def recalculate_trust_grade(user_profile: UserProfile) -> MannerGradeEnum:
    # 신고 횟수는 MannerHistory에서 집계 — report 타입 delta 합산으로 판단
    # warning은 trust_score 기준이 아닌 별도 강제 지정 경로로 처리
    # 현재 update_trust_score 호출 시 warning 필요한 경우 직접 설정
    score = user_profile.trust_score
    if user_profile.trust_grade == MannerGradeEnum.warning:
        return MannerGradeEnum.warning
    if score >= 90:
        return MannerGradeEnum.gold
    elif score >= 70:
        return MannerGradeEnum.silver
    else:
        return MannerGradeEnum.normal
