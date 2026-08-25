from sqlalchemy.orm import Session

from app.models.manner import MannerHistory, MannerFactorEnum
from app.models.report import Report
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

    # report_count를 넘기지 않으면 기본값 0이 쓰여 warning 등급 분기가
    # 영원히 성립하지 않는다 — 실제 누적 신고 수를 세어 넘긴다.
    report_count = db.query(Report).filter(Report.reported_id == user.id).count()
    user.profile.trust_grade = recalculate_trust_grade(user.profile, report_count)

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


def has_factor_history(db: Session, user: User, factor: MannerFactorEnum) -> bool:
    """해당 사유로 이미 가점/감점이 부여된 적이 있는지.

    update_trust_score는 멱등하지 않다(호출할 때마다 이력 추가 + 점수 누적).
    한 번만 줘야 하는 가점은 호출 전에 이 함수로 걸러야 한다.
    """
    return (
        db.query(MannerHistory)
        .filter(MannerHistory.user_id == user.id, MannerHistory.factor == factor)
        .first()
        is not None
    )
