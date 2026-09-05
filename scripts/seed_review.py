"""심사(App Store / Play Console) 제출용 데모 데이터 시드 — 생성/롤백 겸용.

왜 필요한가
-----------
기존 `seed.py`는 더미 유저 20명의 User/UserProfile/Point만 만든다. 사진도, 좋아요도,
매칭도 만들지 않는다. 그 결과 심사관이 심사용 계정으로 로그인하면

  1. 매칭 피드의 카드가 전부 사진 없는 이모지 플레이스홀더로 뜬다
     (`matching.py`가 `[p.s3_url for p in user.photos if p.is_approved]`를 내려주는데 비어 있음)
  2. 매칭은 상호 좋아요라야 성립하는데 더미 유저는 좋아요를 되돌려주지 않으므로
     채팅 화면에 **영영 도달할 수 없다**

사진 없는 데이팅 앱 + 핵심 기능(대화) 시연 불가는 Apple 2.1(App Completeness) /
4.2(Minimum Functionality) 단골 반려 사유다. 이 스크립트가 그 구멍을 메운다.

안전장치
--------
- **기본이 dry-run이다.** 실제로 반영하려면 `--apply`를 붙여야 한다.
- 손대는 행은 전부 결정적으로 식별된다:
      데모 유저  = phone LIKE '010-9000-%'
      심사 계정  = phone == REVIEW_TEST_PHONE (환경변수)
      데모 사진  = s3_url에 '/review-demo/' 포함
  실존 가입자 데이터는 어떤 경로로도 건드리지 않는다.
- `--rollback`이 위 범위를 정확히 되돌린다. 되돌릴 대상을 먼저 세어 보여주고,
  `--apply`가 없으면 세기만 하고 끝난다.

사용법
------
    # 미리보기 (아무것도 안 바꿈)
    railway run python scripts/seed_review.py

    # 실제 생성
    railway run python scripts/seed_review.py --apply

    # 되돌리기 미리보기 → 실행
    railway run python scripts/seed_review.py --rollback
    railway run python scripts/seed_review.py --rollback --apply

    # 심사 계정 행까지 함께 삭제
    railway run python scripts/seed_review.py --rollback --include-review-account --apply

사진 URL은 `upload_review_photos.py`가 만든 `review_photos.json`에서 읽는다.
그 파일이 없으면 사진 없이 매칭·대화만 만들고 경고한다.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()

from sqlalchemy import or_  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.manner import MannerHistory  # noqa: E402
from app.models.matching import (  # noqa: E402
    Block,
    ChatMessage,
    ChatRoom,
    Like,
    LikeStatusEnum,
    Match,
)
from app.models.point import Point, PointHistory  # noqa: E402
from app.models.report import Report  # noqa: E402
from app.models.user import (  # noqa: E402
    GenderEnum,
    MannerGradeEnum,
    PhotoReviewStatusEnum,
    User,
    UserPhoto,
    UserProfile,
)

DEMO_PHONE_PREFIX = "010-9000-"
DEMO_PHONE_LIKE = f"{DEMO_PHONE_PREFIX}%"
DEMO_PHOTO_MARKER = "/review-demo/"
PHOTOS_MANIFEST = Path(__file__).resolve().parent / "review_photos.json"

# ---------------------------------------------------------------------------
# 데모 유저 명단
# gen_photos.py의 프롬프트와 나이·이름이 1:1로 대응한다.
# 사진 속 인물이 60대인데 프로필이 55세로 뜨면 심사관 눈에 바로 걸리므로
# 여기서 나이를 고정한다(기존 seed.py는 55~75 랜덤이라 어긋난다).
# index 1~10 남성, 11~20 여성.
# ---------------------------------------------------------------------------
ROSTER = [
    (1, "김영수", GenderEnum.male, 58, "서울", ["등산", "여행"],
     "주말마다 산에 오릅니다. 같이 걸으며 이야기 나눌 분이면 좋겠습니다."),
    (2, "이정훈", GenderEnum.male, 62, "서울", ["커피", "독서"],
     "퇴직 후 여유로운 삶을 보내고 있어요. 좋은 인연 만나고 싶습니다."),
    (3, "박재호", GenderEnum.male, 55, "인천", ["텃밭", "요리"],
     "텃밭 가꾸기와 요리가 취미예요. 소박하지만 따뜻한 만남 원합니다."),
    (4, "최성민", GenderEnum.male, 67, "부산", ["자전거", "산책"],
     "강변 자전거길을 매일 달립니다. 건강하게 함께 나이 들 분 찾아요."),
    (5, "정승우", GenderEnum.male, 60, "서울", ["독서", "영화"],
     "책과 영화를 좋아합니다. 편하게 대화 나눠요."),
    (6, "강대식", GenderEnum.male, 71, "대구", ["산책", "바둑"],
     "건강하게 하루하루를 즐기며 살고 있습니다. 함께 산책할 분 찾아요."),
    (7, "윤병철", GenderEnum.male, 64, "광주", ["요리", "음악"],
     "직접 요리해서 나눠 먹는 걸 좋아합니다. 소탈한 분이면 좋겠어요."),
    (8, "조현우", GenderEnum.male, 56, "부산", ["바다", "여행"],
     "바닷가 산책을 즐깁니다. 아직 일도 하고 운동도 다니며 활기차게 지냅니다."),
    (9, "한기범", GenderEnum.male, 69, "인천", ["낚시", "등산"],
     "새벽 낚시가 낙입니다. 조용하지만 다정한 사람입니다."),
    (10, "오민석", GenderEnum.male, 57, "서울", ["음악", "기타"],
     "복지관에서 기타를 배우고 있어요. 음악 좋아하는 분 환영합니다."),
    (11, "김순자", GenderEnum.female, 68, "서울", ["원예", "꽃"],
     "베란다에서 꽃 키우는 게 큰 즐거움이에요. 따뜻한 분 만나고 싶습니다."),
    (12, "이영희", GenderEnum.female, 59, "서울", ["도예", "공예"],
     "도예 공방에 다니고 있어요. 손으로 무언가 만드는 걸 좋아합니다."),
    (13, "박미경", GenderEnum.female, 63, "대구", ["여행", "사찰"],
     "고즈넉한 곳으로 여행 다니는 걸 좋아해요. 함께할 분 찾습니다."),
    (14, "최은주", GenderEnum.female, 55, "인천", ["카페", "베이킹"],
     "빵 굽고 차 마시는 시간이 좋아요. 편안한 만남을 원합니다."),
    (15, "정수진", GenderEnum.female, 70, "부산", ["등산", "건강"],
     "일주일에 두 번은 산에 갑니다. 건강하게 함께 다닐 분이면 좋겠어요."),
    (16, "강혜정", GenderEnum.female, 61, "광주", ["요리", "살림"],
     "정성껏 밥상 차리는 걸 좋아합니다. 소박한 일상 나눌 분 찾아요."),
    (17, "윤서영", GenderEnum.female, 57, "서울", ["시장", "요리"],
     "시장 구경이 취미예요. 사람 만나는 걸 좋아해서 모임도 자주 다닙니다."),
    (18, "조명숙", GenderEnum.female, 73, "서울", ["독서", "음악감상"],
     "책 읽으며 보내는 오후가 가장 좋습니다. 대화가 통하는 분이면 좋겠어요."),
    (19, "한지혜", GenderEnum.female, 65, "인천", ["산책", "봄꽃"],
     "강변 산책을 매일 합니다. 이제는 즐거움을 나눌 사람이 필요해요."),
    (20, "오정아", GenderEnum.female, 60, "부산", ["댄스", "운동"],
     "복지관 댄스 교실에 다녀요. 활기찬 분이면 더 좋겠습니다."),
]

# 심사관 계정이 열게 될 대화. 자연스럽되 개인정보·외부 연락처가 없어야 한다
# (스캠 감지 룰에 걸리면 경고 배너가 떠서 심사관이 오해할 수 있다).
DEMO_CONVERSATION = [
    ("peer", "안녕하세요. 프로필 보고 반가워서 인사드립니다."),
    ("me", "안녕하세요, 연락 주셔서 고맙습니다."),
    ("peer", "등산 좋아하신다고 쓰셨더라고요. 저도 주말마다 다닙니다."),
    ("me", "네, 요즘은 가까운 둘레길 위주로 걷고 있어요."),
    ("me", "무리하지 않고 걷는 게 좋더라고요."),
    ("peer", "둘레길도 좋지요. 혹시 다음에 날 좋을 때 같이 걸어보실래요?"),
]

REVIEW_ACCOUNT = {
    "name": "심사용",
    "nickname": "심사용계정",
    "age": 58,
    "region": "서울",
    "bio": "앱 심사를 위한 데모 계정입니다.",
}


# ---------------------------------------------------------------------------
# 조회 헬퍼
# ---------------------------------------------------------------------------
def demo_users(db):
    return db.query(User).filter(User.phone.like(DEMO_PHONE_LIKE)).all()


def review_phone() -> str | None:
    raw = os.getenv("REVIEW_TEST_PHONE", "").strip()
    return raw or None


def get_review_user(db):
    phone = review_phone()
    if not phone:
        return None
    return db.query(User).filter(User.phone == phone).first()


def scoped_user_ids(db, include_review: bool) -> list:
    ids = [u.id for u in demo_users(db)]
    if include_review:
        ru = get_review_user(db)
        if ru:
            ids.append(ru.id)
    return ids


# ---------------------------------------------------------------------------
# 생성
# ---------------------------------------------------------------------------
def load_photo_urls() -> dict[str, str]:
    if not PHOTOS_MANIFEST.exists():
        return {}
    with open(PHOTOS_MANIFEST) as f:
        return json.load(f)


def upsert_user(db, *, phone, name, nickname, age, gender, region, bio,
                interests, trust_score, verified, log):
    user = db.query(User).filter(User.phone == phone).first()
    if user is None:
        user = User(phone=phone, name=name, nickname=nickname, age=age,
                    gender=gender, region=region)
        db.add(user)
        db.flush()
        log.append(f"  + 유저 생성  {phone} {name}({age}, {gender.value}, {region})")
    else:
        # 데모 유저는 전적으로 이 스크립트 소유라 갱신해도 안전하다.
        # 사진 속 나이와 프로필 나이를 맞추기 위해 반드시 필요하다.
        changed = []
        if user.age != age:
            changed.append(f"age {user.age}→{age}")
            user.age = age
        if user.region != region:
            changed.append(f"region {user.region}→{region}")
            user.region = region
        if user.nickname != nickname:
            changed.append("nickname")
            user.nickname = nickname
        user.is_active = True
        user.is_banned = False
        log.append(f"  = 유저 존재  {phone} {name}" + (f" (갱신: {', '.join(changed)})" if changed else ""))

    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        db.flush()
        log.append(f"    + 프로필 생성")
    profile.bio = bio
    profile.interests = interests
    profile.trust_score = trust_score
    profile.is_verified = verified
    profile.trust_grade = (
        MannerGradeEnum.gold if trust_score >= 90
        else MannerGradeEnum.silver if trust_score >= 70
        else MannerGradeEnum.normal
    )

    if db.query(Point).filter(Point.user_id == user.id).first() is None:
        db.add(Point(user_id=user.id, balance=100))
        log.append(f"    + 포인트 100 지급")

    return user


def attach_photo(db, user, url, log):
    """데모 사진 1장을 승인 상태로 붙인다.

    실제 업로드 경로(users.py)는 is_approved=False로 넣고 AI 분석 콜백을 기다리지만,
    여기서는 AI 파이프라인을 태우지 않으므로 승인 상태로 직접 넣는다.
    (Modal에 SafeSearch를 아직 배포하지 않은 상태라 분석을 태우면 오히려 위험하다.)
    """
    existing = (
        db.query(UserPhoto)
        .filter(UserPhoto.user_id == user.id,
                UserPhoto.s3_url.like(f"%{DEMO_PHOTO_MARKER}%"))
        .first()
    )
    if existing:
        if existing.s3_url != url:
            existing.s3_url = url
            log.append(f"    = 사진 URL 갱신")
        existing.is_approved = True
        existing.review_status = PhotoReviewStatusEnum.approved
        existing.is_primary = True
        return
    db.add(UserPhoto(user_id=user.id, s3_url=url, order=0,
                     is_primary=True, is_approved=True,
                     review_status=PhotoReviewStatusEnum.approved))
    log.append(f"    + 사진 부착 (승인 상태)")


def ensure_match(db, a, b, log):
    """a와 b 사이에 상호 좋아요 + 매칭 + 채팅방을 만든다. 이미 있으면 재사용."""
    for frm, to in ((a, b), (b, a)):
        like = (db.query(Like)
                .filter(Like.from_user_id == frm.id, Like.to_user_id == to.id)
                .first())
        if like is None:
            db.add(Like(from_user_id=frm.id, to_user_id=to.id,
                        status=LikeStatusEnum.matched))
        else:
            like.status = LikeStatusEnum.matched

    match = (db.query(Match)
             .filter(or_(
                 (Match.user1_id == a.id) & (Match.user2_id == b.id),
                 (Match.user1_id == b.id) & (Match.user2_id == a.id)))
             .first())
    if match is None:
        match = Match(user1_id=a.id, user2_id=b.id, is_active=True)
        db.add(match)
        db.flush()
        log.append(f"  + 매칭 생성  {a.nickname or a.name} ↔ {b.nickname or b.name}")
    else:
        match.is_active = True
        log.append(f"  = 매칭 존재  {a.nickname or a.name} ↔ {b.nickname or b.name}")

    room = db.query(ChatRoom).filter(ChatRoom.match_id == match.id).first()
    if room is None:
        room = ChatRoom(match_id=match.id, supabase_channel=str(match.id), is_active=True)
        db.add(room)
        db.flush()
        log.append(f"    + 채팅방 생성")
    return match, room


def fill_conversation(db, room, me, peer, log):
    """데모 대화를 넣는다.

    created_at을 명시적으로 벌려서 넣는 게 핵심이다. TimestampMixin의
    server_default=func.now()는 **트랜잭션 시작 시각**이라 한 트랜잭션에서 넣은
    메시지가 전부 같은 타임스탬프를 갖는다. 채팅방은 `created_at ASC`(chat.py:143),
    대화 목록은 `DISTINCT ON(room_id) ... created_at DESC`(matching.py)로 정렬하므로
    타임스탬프가 같으면 **순서가 비결정적**이 된다 — 심사관에게 대화가 뒤섞여
    보이거나 목록의 '마지막 메시지'로 첫 인사가 뜬다(실제로 그렇게 나왔다).

    마지막 상대 메시지는 읽지 않은 상태로 둔다. 대화 목록에 안 읽음 배지가
    떠서 심사관이 기능을 바로 확인할 수 있다.
    """
    existing = db.query(ChatMessage).filter(ChatMessage.room_id == room.id).count()
    if existing:
        log.append(f"    = 메시지 {existing}건 이미 있음 (건너뜀)")
        return

    n = len(DEMO_CONVERSATION)
    base = datetime.now(timezone.utc) - timedelta(hours=3)
    last_index = n - 1
    for i, (who, text) in enumerate(DEMO_CONVERSATION):
        sender = me if who == "me" else peer
        ts = base + timedelta(minutes=7 * i)
        is_last_from_peer = (i == last_index and who == "peer")
        db.add(ChatMessage(
            room_id=room.id, sender_id=sender.id, content=text,
            is_scam=False,
            is_read=not is_last_from_peer,
            created_at=ts, updated_at=ts,
        ))
    log.append(f"    + 메시지 {n}건 생성 (7분 간격, 마지막 1건은 안 읽음)")


def do_seed(db, apply: bool) -> int:
    log: list[str] = []
    photo_urls = load_photo_urls()

    if not photo_urls:
        print("⚠️  review_photos.json 이 없습니다 — 사진 없이 매칭·대화만 만듭니다.")
        print("    먼저 `railway run python scripts/upload_review_photos.py --apply` 를 실행하세요.\n")

    phone = review_phone()
    if not phone:
        print("❌ REVIEW_TEST_PHONE 환경변수가 없습니다. 심사 계정을 만들 수 없습니다.")
        print("   Railway 백엔드 프로젝트에 REVIEW_TEST_PHONE / REVIEW_TEST_CODE 를 먼저 설정하세요.")
        return 1
    if not os.getenv("REVIEW_TEST_CODE", "").strip():
        print("❌ REVIEW_TEST_CODE 환경변수가 없습니다.")
        print("   auth.py의 _is_review_phone()은 두 값이 모두 있을 때만 활성화됩니다.")
        print("   코드가 없으면 심사관은 실제 SMS를 받아야 하고, 결국 로그인하지 못합니다.")
        return 1

    print("=" * 72)
    print("데모 유저 20명")
    print("=" * 72)
    demo_by_index = {}
    for idx, name, gender, age, region, interests, bio in ROSTER:
        user = upsert_user(
            db, phone=f"{DEMO_PHONE_PREFIX}{idx:04d}", name=name, nickname=name,
            age=age, gender=gender, region=region, bio=bio, interests=interests,
            # 신뢰점수를 골고루 흩어 배지(골드/실버/일반)가 전부 보이게 한다.
            trust_score=[92, 88, 74, 71, 68][idx % 5],
            verified=(idx % 3 != 0), log=log,
        )
        url = photo_urls.get(f"{idx:04d}")
        if url:
            attach_photo(db, user, url, log)
        demo_by_index[idx] = user

    print("\n".join(log)); log.clear()

    print()
    print("=" * 72)
    print("심사용 계정")
    print("=" * 72)
    review_user = upsert_user(
        db, phone=phone, name=REVIEW_ACCOUNT["name"],
        nickname=REVIEW_ACCOUNT["nickname"], age=REVIEW_ACCOUNT["age"],
        gender=GenderEnum.male, region=REVIEW_ACCOUNT["region"],
        bio=REVIEW_ACCOUNT["bio"], interests=["등산", "독서"],
        trust_score=85, verified=True, log=log,
    )
    print("\n".join(log)); log.clear()

    print()
    print("=" * 72)
    print("매칭 · 대화")
    print("=" * 72)
    # 심사 계정은 남성 → 피드에는 여성이 뜬다. 매칭 상대도 여성으로 잡는다.
    partner_a = demo_by_index[11]   # 김순자 — 대화가 있는 매칭
    partner_b = demo_by_index[15]   # 정수진 — 매칭만 있고 대화 없음(빈 상태 확인용)

    _, room_a = ensure_match(db, review_user, partner_a, log)
    fill_conversation(db, room_a, review_user, partner_a, log)
    ensure_match(db, review_user, partner_b, log)
    print("\n".join(log))

    print()
    if apply:
        db.commit()
        print("✅ 반영 완료 (커밋)")
    else:
        db.rollback()
        print("🔎 dry-run — 아무것도 저장하지 않았습니다. 실제 반영은 --apply")
    return 0


# ---------------------------------------------------------------------------
# 롤백
# ---------------------------------------------------------------------------
def do_rollback(db, apply: bool, include_review: bool) -> int:
    ids = scoped_user_ids(db, include_review=True)  # 관계 정리는 심사계정 포함
    if not ids:
        print("삭제할 데모 유저가 없습니다.")
        return 0

    demo_ids = [u.id for u in demo_users(db)]
    review_user = get_review_user(db)

    print("=" * 72)
    print("롤백 대상")
    print("=" * 72)
    print(f"데모 유저(010-9000-*)          : {len(demo_ids)}명")
    print(f"심사 계정                       : {'있음' if review_user else '없음'}"
          f"{' (User 행까지 삭제)' if include_review and review_user else ' (User 행은 보존)'}")

    # 1) 채팅 메시지 — 관련 매칭의 방에 속한 것
    matches = (db.query(Match)
               .filter(or_(Match.user1_id.in_(ids), Match.user2_id.in_(ids)))
               .all())
    match_ids = [m.id for m in matches]
    rooms = (db.query(ChatRoom).filter(ChatRoom.match_id.in_(match_ids)).all()
             if match_ids else [])
    room_ids = [r.id for r in rooms]
    msg_count = (db.query(ChatMessage).filter(ChatMessage.room_id.in_(room_ids)).count()
                 if room_ids else 0)

    likes = (db.query(Like)
             .filter(or_(Like.from_user_id.in_(ids), Like.to_user_id.in_(ids))).count())
    blocks = (db.query(Block)
              .filter(or_(Block.blocker_id.in_(ids), Block.blocked_id.in_(ids))).count())
    reports = (db.query(Report)
               .filter(or_(Report.reporter_id.in_(ids), Report.reported_id.in_(ids))).count())

    # 사진: 데모 유저는 전부, 심사 계정은 데모 마커가 붙은 것만
    demo_photos = (db.query(UserPhoto).filter(UserPhoto.user_id.in_(demo_ids)).count()
                   if demo_ids else 0)
    review_photos = 0
    if review_user:
        review_photos = (db.query(UserPhoto)
                         .filter(UserPhoto.user_id == review_user.id,
                                 UserPhoto.s3_url.like(f"%{DEMO_PHOTO_MARKER}%")).count())

    print(f"채팅 메시지                     : {msg_count}건")
    print(f"채팅방                          : {len(room_ids)}개")
    print(f"매칭                            : {len(match_ids)}건")
    print(f"좋아요                          : {likes}건")
    print(f"차단/신고                       : {blocks}/{reports}건")
    print(f"사진 (데모유저 전체 / 심사계정 데모분): {demo_photos} / {review_photos}장")

    if not apply:
        print("\n🔎 dry-run — 아무것도 삭제하지 않았습니다. 실제 삭제는 --rollback --apply")
        return 0

    # FK 순서대로 삭제
    if room_ids:
        db.query(ChatMessage).filter(ChatMessage.room_id.in_(room_ids)).delete(
            synchronize_session=False)
        db.query(ChatRoom).filter(ChatRoom.id.in_(room_ids)).delete(
            synchronize_session=False)
    if match_ids:
        db.query(Match).filter(Match.id.in_(match_ids)).delete(synchronize_session=False)
    db.query(Like).filter(or_(Like.from_user_id.in_(ids),
                              Like.to_user_id.in_(ids))).delete(synchronize_session=False)
    db.query(Block).filter(or_(Block.blocker_id.in_(ids),
                               Block.blocked_id.in_(ids))).delete(synchronize_session=False)
    db.query(Report).filter(or_(Report.reporter_id.in_(ids),
                                Report.reported_id.in_(ids))).delete(synchronize_session=False)

    if review_user and not include_review:
        db.query(UserPhoto).filter(
            UserPhoto.user_id == review_user.id,
            UserPhoto.s3_url.like(f"%{DEMO_PHOTO_MARKER}%")).delete(synchronize_session=False)

    kill_ids = list(demo_ids)
    if include_review and review_user:
        kill_ids.append(review_user.id)

    if kill_ids:
        db.query(UserPhoto).filter(UserPhoto.user_id.in_(kill_ids)).delete(
            synchronize_session=False)
        db.query(PointHistory).filter(PointHistory.user_id.in_(kill_ids)).delete(
            synchronize_session=False)
        db.query(Point).filter(Point.user_id.in_(kill_ids)).delete(
            synchronize_session=False)
        db.query(MannerHistory).filter(MannerHistory.user_id.in_(kill_ids)).delete(
            synchronize_session=False)
        db.query(UserProfile).filter(UserProfile.user_id.in_(kill_ids)).delete(
            synchronize_session=False)
        db.query(User).filter(User.id.in_(kill_ids)).delete(synchronize_session=False)

    db.commit()
    print("\n✅ 롤백 완료 (커밋)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="심사용 데모 데이터 시드/롤백")
    p.add_argument("--apply", action="store_true",
                   help="실제로 DB에 반영한다. 없으면 dry-run.")
    p.add_argument("--rollback", action="store_true",
                   help="생성 대신 되돌린다.")
    p.add_argument("--include-review-account", action="store_true",
                   help="롤백 시 심사 계정 User 행까지 삭제한다.")
    args = p.parse_args()

    db = SessionLocal()
    try:
        if args.rollback:
            return do_rollback(db, args.apply, args.include_review_account)
        return do_seed(db, args.apply)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
