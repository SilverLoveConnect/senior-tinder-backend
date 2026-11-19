from sqlalchemy.orm import Session

from app.models.manner import MannerHistory, MannerFactorEnum
from app.models.report import Report
from app.models.user import User, UserProfile, MannerGradeEnum

# ── 신뢰점수 규칙 ─────────────────────────────────────────────────────────────
# 점수 규칙은 여기 한 곳에서만 정한다. 기본값(DEFAULT_TRUST_SCORE)은 컬럼
# 기본값과 묶여 있어 app/models/user.py에 둔다.
# 환경변수로 빼지 않는 이유: 운영 중 값만 바꾸면 이미 쌓인 점수·등급과 기준이
# 어긋난다. 바꿀 때는 코드 리뷰를 거친다.
TRUST_SCORE_MIN = 0
TRUST_SCORE_MAX = 100

# 등급 경계 (이상)
GRADE_GOLD_MIN_SCORE = 90
GRADE_SILVER_MIN_SCORE = 70
# 누적 신고가 이 수 이상이면 점수와 상관없이 warning 등급
GRADE_WARNING_REPORT_COUNT = 3

# 가감점
DELTA_PROFILE_COMPLETE = 10   # 프로필 완성 (계정당 1회)
DELTA_PHOTO_APPROVED = 15     # 프로필 사진 승인 (AI 자동·관리자 수동 공통)
DELTA_REPORTED = -10          # 신고 접수

# 프로필 완성 조건 (둘 중 하나)
PROFILE_COMPLETE_MIN_PHOTOS = 3
PROFILE_COMPLETE_MIN_BIO_LENGTH = 100


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

    new_score = max(
        TRUST_SCORE_MIN, min(TRUST_SCORE_MAX, user.profile.trust_score + delta)
    )
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
    if report_count >= GRADE_WARNING_REPORT_COUNT:
        return MannerGradeEnum.warning
    if score >= GRADE_GOLD_MIN_SCORE:
        return MannerGradeEnum.gold
    elif score >= GRADE_SILVER_MIN_SCORE:
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
