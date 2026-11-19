"""신뢰점수 규칙 테스트.

상수 스냅샷 테스트는 "값을 바꾸면 안 된다"가 아니라 "바꿀 때는 의도적으로 바꿔라"는
뜻이다. 규칙을 바꾸는 PR은 이 테스트도 함께 고치게 되므로 리뷰에서 바로 보인다.
"""
from types import SimpleNamespace

import pytest

from app.models.user import DEFAULT_TRUST_SCORE, MannerGradeEnum, UserProfile
from app.services import manner
from app.services.manner import recalculate_trust_grade
from app.services.report import AUTO_BAN_REPORT_COUNT


def test_policy_snapshot():
    assert DEFAULT_TRUST_SCORE == 50
    assert (manner.TRUST_SCORE_MIN, manner.TRUST_SCORE_MAX) == (0, 100)
    assert (manner.GRADE_GOLD_MIN_SCORE, manner.GRADE_SILVER_MIN_SCORE) == (90, 70)
    assert manner.GRADE_WARNING_REPORT_COUNT == 3
    assert manner.DELTA_PROFILE_COMPLETE == 10
    assert manner.DELTA_PHOTO_APPROVED == 15
    assert manner.DELTA_REPORTED == -10
    assert (manner.PROFILE_COMPLETE_MIN_PHOTOS, manner.PROFILE_COMPLETE_MIN_BIO_LENGTH) == (3, 100)
    assert AUTO_BAN_REPORT_COUNT == 3


def test_column_default_uses_constant():
    assert UserProfile.__table__.c.trust_score.default.arg == DEFAULT_TRUST_SCORE


@pytest.mark.parametrize(
    "score, reports, expected",
    [
        (100, 0, MannerGradeEnum.gold),
        (90, 0, MannerGradeEnum.gold),
        (89, 0, MannerGradeEnum.silver),
        (70, 0, MannerGradeEnum.silver),
        (69, 0, MannerGradeEnum.normal),
        (DEFAULT_TRUST_SCORE, 0, MannerGradeEnum.normal),
        (100, 2, MannerGradeEnum.gold),
        (100, 3, MannerGradeEnum.warning),
    ],
)
def test_grade_boundaries(score, reports, expected):
    assert recalculate_trust_grade(SimpleNamespace(trust_score=score), reports) == expected
