# 사전 신청 비즈니스 로직
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.pre_registration import PreRegistration
from app.schemas.pre_registration import (
    PreRegistrationRequest,
    PreRegistrationResponse,
    PreRegistrationSummary,
)
from app.services.content_filter import check_profile_text

KST = timezone(timedelta(hours=9))
MIN_AGE = 50  # 앱 가입 조건(schemas/auth.py age ge=50)과 같은 기준

GYEONGGI = (
    "수원시", "성남시", "의정부시", "안양시", "부천시", "광명시", "평택시", "동두천시",
    "안산시", "고양시", "과천시", "구리시", "남양주시", "오산시", "시흥시", "군포시",
    "의왕시", "하남시", "용인시", "파주시", "이천시", "안성시", "김포시", "화성시",
    "광주시", "양주시", "포천시", "여주시", "연천군", "가평군", "양평군",
)
ALLOWED_REGIONS = {"서울", "기타"} | {f"경기 {c}" for c in GYEONGGI}

PHONE_RE = re.compile(r"^01[016789]\d{7,8}$")
SOURCE_RE = re.compile(r"^[a-z0-9_-]{1,30}$")

# ── 도배 방지 (프로세스 메모리 기반) ─────────────────────────────────────────
# Railway 단일 인스턴스라 메모리로 충분하다. 재시작되면 초기화되지만, 막으려는 건
# 짧은 시간의 반복 제출이라 문제없다.
PHONE_INTERVAL_SEC = 60
IP_WINDOW_SEC = 600
IP_MAX_REQUESTS = 20

_lock = threading.Lock()
_phone_last: dict[str, float] = {}
_ip_hits: dict[str, deque] = defaultdict(deque)


def _rate_limit(phone: str, ip: str | None) -> None:
    now = time.monotonic()
    with _lock:
        last = _phone_last.get(phone)
        if last is not None and now - last < PHONE_INTERVAL_SEC:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="잠시 후 다시 시도해 주세요.",
            )
        if ip:
            hits = _ip_hits[ip]
            while hits and now - hits[0] > IP_WINDOW_SEC:
                hits.popleft()
            if len(hits) >= IP_MAX_REQUESTS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
                )
            hits.append(now)
        _phone_last[phone] = now


def _bad_request(msg: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


def register(
    db: Session, data: PreRegistrationRequest, client_ip: str | None = None
) -> PreRegistrationResponse:
    if not data.privacy_consent:
        raise _bad_request("개인정보 수집·이용에 동의해 주셔야 신청할 수 있어요.")

    phone = re.sub(r"\D", "", data.phone)
    if not PHONE_RE.match(phone):
        raise _bad_request("휴대폰 번호를 다시 확인해 주세요.")

    name = data.name.strip()
    if not name:
        raise _bad_request("이름을 입력해 주세요.")
    check_profile_text("이름", name)

    age = datetime.now(KST).year - data.birth_year
    if age < MIN_AGE:
        raise _bad_request("시나브로는 만 50세 이상만 이용할 수 있어요.")
    if age > 100:
        raise _bad_request("출생연도를 다시 확인해 주세요.")

    region = data.region.strip()
    if region not in ALLOWED_REGIONS:
        raise _bad_request("지역을 목록에서 선택해 주세요.")

    source = (data.source or "").strip().lower() or None
    if source and not SOURCE_RE.match(source):
        source = "etc"

    _rate_limit(phone, client_ip)

    row = db.query(PreRegistration).filter(PreRegistration.phone == phone).first()
    if row is None:
        row = PreRegistration(phone=phone)
        db.add(row)
    row.name = name
    row.gender = data.gender
    row.birth_year = data.birth_year
    row.region = region
    # 처음 들어온 경로를 지킨다 — 재신청 링크가 달라도 최초 유입 채널로 집계
    row.source = row.source or source
    row.privacy_consent = True
    row.marketing_consent = data.marketing_consent
    db.commit()

    return PreRegistrationResponse(
        ok=True, message="신청이 완료됐어요. 출시되면 문자로 알려드릴게요."
    )


def summary(db: Session) -> PreRegistrationSummary:
    rows = db.query(
        PreRegistration.gender,
        PreRegistration.region,
        PreRegistration.source,
        PreRegistration.marketing_consent,
    ).all()

    by_gender: dict[str, int] = defaultdict(int)
    by_region: dict[str, int] = defaultdict(int)
    by_region_gender: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_source: dict[str, int] = defaultdict(int)
    marketing = 0
    for gender, region, source, mkt in rows:
        g = gender.value if hasattr(gender, "value") else str(gender)
        by_gender[g] += 1
        by_region[region] += 1
        by_region_gender[region][g] += 1
        by_source[source or "direct"] += 1
        marketing += 1 if mkt else 0

    return PreRegistrationSummary(
        total=len(rows),
        marketing_consent=marketing,
        by_gender=dict(by_gender),
        by_region=dict(by_region),
        by_region_gender={k: dict(v) for k, v in by_region_gender.items()},
        by_source=dict(by_source),
    )
