"""사전 신청 API — SQLite 메모리 DB로 라우터·검증·upsert·집계를 확인한다."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ["INTERNAL_TOKEN"] = "test-internal"

from datetime import datetime  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.dependencies import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.pre_registration import PreRegistration  # noqa: E402
from app.services import pre_registration as svc  # noqa: E402

settings.INTERNAL_TOKEN = "test-internal"
YEAR = datetime.now(svc.KST).year


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    # gen_random_uuid()는 Postgres 전용 — SQLite에서는 파이썬 쪽 uuid4 기본값만 쓴다
    id_col = PreRegistration.__table__.c.id
    saved_default, id_col.server_default = id_col.server_default, None
    try:
        PreRegistration.__table__.create(engine)
    finally:
        id_col.server_default = saved_default
    Session = sessionmaker(bind=engine, autoflush=False)

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    svc._phone_last.clear()
    svc._ip_hits.clear()
    with TestClient(app) as c:
        c.Session = Session
        yield c
    app.dependency_overrides.clear()


def body(**kw):
    base = {
        "name": "김영희",
        "phone": "010-1234-5678",
        "gender": "female",
        "birth_year": YEAR - 60,
        "region": "경기 수원시",
        "source": "band",
        "privacy_consent": True,
        "marketing_consent": True,
    }
    base.update(kw)
    return base


def test_create_ok_and_normalizes_phone(client):
    r = client.post("/pre-registrations", json=body())
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    assert "phone" not in r.json()  # 신청자 정보를 되돌려주지 않는다
    with client.Session() as db:
        row = db.query(PreRegistration).one()
        assert row.phone == "01012345678"
        assert row.source == "band"
        assert row.marketing_consent is True


def test_reapply_updates_same_row_and_keeps_first_source(client):
    client.post("/pre-registrations", json=body())
    svc._phone_last.clear()  # 1분 제한은 별도 테스트
    r = client.post(
        "/pre-registrations",
        json=body(phone="01012345678", region="서울", source="daangn", marketing_consent=False),
    )
    assert r.status_code == 200, r.text
    with client.Session() as db:
        rows = db.query(PreRegistration).all()
        assert len(rows) == 1
        assert rows[0].region == "서울"
        assert rows[0].source == "band"
        assert rows[0].marketing_consent is False


@pytest.mark.parametrize(
    "override, msg",
    [
        ({"privacy_consent": False}, "동의"),
        ({"phone": "02-123-4567"}, "휴대폰"),
        ({"birth_year": YEAR - 49}, "만 50세"),
        ({"birth_year": YEAR - 101}, "출생연도"),
        ({"region": "부산"}, "지역"),
        ({"name": "   "}, "이름"),
        ({"name": "조건만남"}, "이름"),
    ],
)
def test_rejects_invalid(client, override, msg):
    r = client.post("/pre-registrations", json=body(**override))
    assert r.status_code == 400, r.text
    assert msg in r.json()["detail"]


def test_age_boundary_50_ok(client):
    r = client.post("/pre-registrations", json=body(birth_year=YEAR - 50))
    assert r.status_code == 200, r.text


def test_weird_source_is_bucketed(client):
    client.post("/pre-registrations", json=body(source="<script>"))
    with client.Session() as db:
        assert db.query(PreRegistration).one().source == "etc"


def test_same_phone_within_a_minute_is_limited(client):
    assert client.post("/pre-registrations", json=body()).status_code == 200
    assert client.post("/pre-registrations", json=body()).status_code == 429


def test_ip_limit(client):
    for i in range(svc.IP_MAX_REQUESTS):
        r = client.post(
            "/pre-registrations",
            json=body(phone=f"0101000{i:04d}"),
            headers={"x-forwarded-for": "1.2.3.4"},
        )
        assert r.status_code == 200, r.text
    r = client.post(
        "/pre-registrations",
        json=body(phone="01099998888"),
        headers={"x-forwarded-for": "1.2.3.4, 10.0.0.1"},
    )
    assert r.status_code == 429


def test_summary_requires_internal_token_and_has_no_pii(client):
    client.post("/pre-registrations", json=body())
    client.post(
        "/pre-registrations",
        json=body(phone="01022223333", gender="male", region="서울", source=None, marketing_consent=False),
    )
    assert client.get("/internal/pre-registrations/summary").status_code == 401
    r = client.get(
        "/internal/pre-registrations/summary", headers={"x-internal-token": "test-internal"}
    )
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["total"] == 2
    assert s["marketing_consent"] == 1
    assert s["by_gender"] == {"female": 1, "male": 1}
    assert s["by_region_gender"]["경기 수원시"] == {"female": 1}
    assert s["by_source"] == {"band": 1, "direct": 1}
    assert "0101234" not in r.text and "김영희" not in r.text
