# 시니어 더미 유저 시드 스크립트
# 매칭 테스트용으로 남성 10명, 여성 10명(총 20명)의 User/UserProfile/Point를 생성한다.
# 실행: uv run python scripts/seed.py

import random
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()

from app.core.database import SessionLocal  # noqa: E402
from app.models.point import Point  # noqa: E402
from app.models.user import GenderEnum, User, UserProfile  # noqa: E402

REGIONS = ["서울", "부산", "대구", "인천", "광주"]

MALE_NAMES = [
    "김영수", "이정훈", "박재호", "최성민", "정승우",
    "강대식", "윤병철", "조현우", "한기범", "오민석",
]

FEMALE_NAMES = [
    "김순자", "이영희", "박미경", "최은주", "정수진",
    "강혜정", "윤서영", "조명숙", "한지혜", "오정아",
]

BIO_TEMPLATES_60S_PLUS = [
    "건강하게 하루하루를 즐기며 살고 있습니다. 함께 산책할 분 찾아요.",
    "퇴직 후 여유로운 삶을 보내고 있어요. 좋은 인연 만나고 싶습니다.",
    "등산과 여행을 좋아합니다. 마음 맞는 분과 함께하고 싶어요.",
    "텃밭 가꾸기와 요리가 취미예요. 소박하지만 따뜻한 만남 원합니다.",
    "손주들 보는 재미로 살지만, 이제는 제 짝도 찾고 싶어요.",
]

BIO_TEMPLATES_50S = [
    "아직 일도 하고 운동도 다니며 활기차게 지내고 있습니다.",
    "주말마다 등산이나 자전거를 타요. 같이 다닐 분 환영합니다.",
    "음악 감상과 영화 보기를 좋아합니다. 편하게 대화 나눠요.",
    "사람 만나는 걸 좋아해서 모임도 자주 다닙니다.",
    "이제는 외로움보다 즐거움을 나눌 사람이 필요해요.",
]


def make_bio(age: int) -> str:
    pool = BIO_TEMPLATES_50S if age < 60 else BIO_TEMPLATES_60S_PLUS
    return random.choice(pool)


def build_dummy_users() -> list[dict]:
    users = []
    for i, name in enumerate(MALE_NAMES, start=1):
        users.append({"index": i, "name": name, "gender": GenderEnum.male})
    for i, name in enumerate(FEMALE_NAMES, start=1):
        users.append({"index": i + 10, "name": name, "gender": GenderEnum.female})
    return users


def seed() -> None:
    db = SessionLocal()
    created_count = 0
    try:
        for data in build_dummy_users():
            phone = f"010-9000-{data['index']:04d}"

            existing = db.query(User).filter(User.phone == phone).first()
            if existing is not None:
                continue

            age = random.randint(55, 75)
            user = User(
                phone=phone,
                name=data["name"],
                nickname=data["name"],
                age=age,
                gender=data["gender"],
                region=random.choice(REGIONS),
            )
            db.add(user)
            db.flush()

            profile = UserProfile(
                user_id=user.id,
                bio=make_bio(age),
                trust_score=random.randint(50, 90),
            )
            db.add(profile)

            point = Point(user_id=user.id, balance=100)
            db.add(point)

            created_count += 1

        db.commit()
    finally:
        db.close()

    print(f"생성된 더미 유저 수: {created_count}명")


if __name__ == "__main__":
    seed()
