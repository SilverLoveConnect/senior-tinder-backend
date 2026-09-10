# 시나브로 백엔드 — Google Play 출시 전 QA 리포트

- **대상 저장소**: `SilverLoveConnect/senior-tinder-backend`
- **기준 커밋**: `425a23b` (사진 검수 상태 노출 + 채팅방 나가기 API, #55)
- **QA 브랜치**: `claude/google-play-store-qa-g4b29h`
- **작성일**: 2026-09-10
- **QA 방식**: 문서 리뷰가 아니라 **실제 구동 검증**. PostgreSQL 16을 띄우고 `alembic upgrade head`로
  스키마를 만든 뒤, `uvicorn`으로 실서버를 올려 HTTP로 62개 시나리오를 직접 호출했습니다.
  결과는 아래 각 항목의 "재현 로그"에 실제 응답 그대로 붙였습니다.

## 0. 요약

| 결과 | 건수 |
|---|---|
| PASS | 32 |
| FAIL | 15 |
| WARN | 4 |
| INFO | 5 |

**결론: 현재 상태로 프로덕션 업로드 시 P0 5건이 걸립니다.**
그중 2건(`H-01`, `G-07`)은 Google Play **데이터 보안(Data safety) 신고 내용과 실제 동작이 다른 경우**로,
심사 반려를 넘어 게시 후 앱 정지까지 이어질 수 있는 유형입니다.
1건(`B-00`)은 심사관은 겪지 않고 **실사용자 전원이 겪는** 온보딩 차단이라 심사는 통과해도 출시 직후 리뷰가 무너집니다.

### 심각도별 목록

| 등급 | ID | 내용 | 영역 |
|---|---|---|---|
| **P0** | B-00 | 회원가입 완료 직후 로그인이 불가능(1분 대기 강제) | 온보딩 |
| **P0** | F-01/F-02 | `INTERNAL_TOKEN` 미설정 시 관리자 API가 무인증 통과 | 보안 |
| **P0** | H-01 | 채팅 원문을 외부 AI 서버로 전송 — 처리방침은 "외부 전송 없음"이라 명시 | Play 정책 |
| **P0** | D-02 | 차단 목록 응답이 닉네임 자리에 **실명**을 반환 | 개인정보 |
| **P0** | G-07 | 탈퇴·사진삭제 시 S3 원본이 남음 — 처리방침은 "30일 내 파기" | Play 계정삭제 정책 |
| P1 | B-04/B-05 | `/auth/register` 인증코드 무차별 대입에 시도 제한 없음 | 보안 |
| P1 | D-10/D-11 | 프로필 텍스트 모더레이션·콘텐츠 단위 신고 부재 | Play UGC 정책 |
| P1 | K-02 | 마케팅 수신동의 철회 API 없음 | 개인정보 |
| P1 | L-01 | FCM 토큰 중복 — 남의 메시지 알림이 이전 사용자 기기로 발송 | 개인정보 |
| P1 | C-06 | 읽음 처리 코드가 없어 안읽음 배지가 영구 잔존 | 기능 |
| P1 | J-01 | 가입 시 `points` 레코드 미생성 → 포인트 사용 항상 실패 | 기능 |
| P1 | I-01 | 포인트 차감 동시성 — 100P로 200P 사용 성공 | 정합성 |
| P1 | G-04 | 탈퇴·정지 계정도 refresh 토큰으로 액세스 토큰 재발급 | 보안 |
| P1 | L-03 | 탈퇴한 상대와의 채팅방이 활성으로 남음 | 기능 |
| P2 | D-09 | 신고 3회 자동정지 어뷰징 + 앱 내 이의제기 경로 없음 | 운영 |
| P2 | H-03 | `/docs`·`/openapi.json` 전체 공개(`/internal` 경로 포함) | 보안 |
| P2 | K-06 | `CORS_ALLOWED_ORIGINS` 미설정 시 `*` + `allow_credentials=True` | 보안 |
| P2 | I-04 | 차단 상태에서는 채팅방 나가기가 403 | 기능 |

---

## 1. QA 환경 구성

```bash
service postgresql start
su postgres -c "createdb sinabro"
su postgres -c "psql -d sinabro -c 'CREATE EXTENSION IF NOT EXISTS pgcrypto;'"

# .env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sinabro
SECRET_KEY=qa-local-secret-key-for-testing-only
REVIEW_TEST_PHONE=01099998888
REVIEW_TEST_CODE=112233

uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

먼저 통과한 기본 항목:

- `alembic upgrade head` — 11개 리비전 전부 정상 적용, 에러 없음
- `alembic check` — **"No new upgrade operations detected"**. 모델과 마이그레이션 간 드리프트 없음
- `GET /health` → `{"status":"ok"}`

> 참고(경미): `users.is_active`, `chat_rooms.is_active`, `user_photos.is_approved` 등은
> Python 측 `default=`만 있고 DB `server_default`가 없습니다. ORM 경유 INSERT만 쓰는 지금은 문제없지만,
> 시드 스크립트나 운영 쿼리에서 raw SQL로 INSERT하면 NOT NULL 위반이 납니다.

---

## 2. P0 — 출시 차단

### P0-1 (B-00) 회원가입 완료 직후 로그인이 불가능하다

**재현 로그 (실제 응답)**

```
[FAIL] B-00 가입 완료 직후 로그인 가능 여부
  register 응답에 토큰 없음
  방금 인증한 코드로 login=400 ("인증번호를 먼저 요청해주세요")
  인증번호 재요청=429 ("잠시 후 다시 시도해주세요. (1분에 1회만 요청할 수 있습니다)")
```

**무엇이 벌어지나**

1. `POST /auth/sms/verify`가 `SmsVerification.is_used = True`로 코드를 **소비**한다 (`app/services/auth.py:139`)
2. `POST /auth/register`는 토큰을 주지 않는다 — 응답은 `{id, phone, name}`뿐 (`app/schemas/auth.py` `RegisterResponse`)
3. 앱은 이어서 `POST /auth/login`을 불러야 하는데, `login_user()`가 `verify_sms_code()`를 다시 호출한다 (`app/services/auth.py:211`).
   미사용 코드가 없으므로 400
4. 그래서 `POST /auth/sms/send`를 다시 불러야 하는데 — 1분 rate limit에 걸려 **429** (`app/services/auth.py:16,64`)

즉 **가입 직후 최소 1분간 로그인 경로가 완전히 막힙니다.** 50~60대 이용자가 가입 마지막 화면에서
"인증번호를 먼저 요청해주세요"와 "1분에 1회만 요청할 수 있습니다"를 연달아 보게 됩니다.

**심사관은 왜 못 잡나**: `_is_review_phone()`이 rate limit 자체를 건너뛰기 때문입니다 (`app/services/auth.py:46-56`).
심사용 번호는 재요청이 즉시 성공합니다. 그래서 **심사는 통과하고 실사용자만 막히는** 형태입니다.

**수정안 A (권장) — register가 토큰을 함께 반환**

```python
# app/services/auth.py
def register_user(db: Session, data: RegisterRequest) -> dict:
    ...
    db.commit()
    db.refresh(user)
    return {
        "user": user,
        "access_token": create_access_token(subject=str(user.id)),
        "refresh_token": create_refresh_token(subject=str(user.id)),
    }
```

```python
# app/schemas/auth.py
class RegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    phone: str
    name: str
    access_token: str          # 추가
    refresh_token: str         # 추가
    token_type: str = "bearer" # 추가
```

- 장점: 방금 SMS 인증을 마친 사용자이므로 신뢰 근거가 이미 충분합니다. 왕복 1회가 줄어 가입 이탈이 낮아지고,
  로그인 화면으로 되돌아가는 동선 자체가 사라집니다. 업계 표준 동작이기도 합니다.
- 단점: **앱 수정이 필요합니다.** 프론트가 register 응답에서 토큰을 저장하고 바로 홈으로 진입하도록 바꿔야 합니다.
- **팀 조율**: 응답에 필드를 *추가*만 하므로 기존 앱 버전은 깨지지 않습니다(무시하면 지금 동작 그대로).
  백엔드 먼저 배포 → 앱이 따라오는 순서가 가능합니다. **백엔드가 앱에 맞추는 게 아니라 앱이 백엔드에 맞추는 쪽**을 권합니다.

**수정안 B — 로그인 시 "최근 소비된 코드"도 허용**

```python
# app/services/auth.py
def login_user(db: Session, phone: str, code: str) -> dict:
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(400, "존재하지 않는 회원입니다.")
    try:
        verify_sms_code(db, phone, code)
    except HTTPException:
        # register가 방금 소비한 코드는 짧은 유예시간 안에서 재사용 허용
        _ensure_sms_verified_for_register(db, phone, code)
    ...
```

- 장점: **앱 수정이 전혀 필요 없습니다.** 백엔드만 배포하면 끝납니다. 급하게 막아야 할 때 유효한 카드입니다.
- 단점: 한 번 쓴 코드가 15분간 재사용 가능해집니다. 코드 유출 시 창이 넓어지고, `_ensure_sms_verified_for_register`가
  register 전용이라는 원래 의도에서 벗어나 의미가 흐려집니다.
- **팀 조율**: 앱 릴리스 일정이 잡혀 있다면 B로 막고, 다음 앱 버전에서 A로 정리하는 2단계도 합리적입니다.

**추가 확인 필요**: 앱이 register 후 실제로 어떤 화면으로 가는지(자동 로그인 시도인지, 로그인 화면 복귀인지)를
프론트에서 확인해야 최종 판단이 됩니다. 만약 앱이 register 후 사용자에게 "로그인해주세요"만 띄운다면
사용자는 영문도 모른 채 1분을 기다려야 합니다.

---

### P0-2 (F-01/F-02) `INTERNAL_TOKEN` 미설정 시 관리자 API가 무인증으로 열린다

**재현 로그**

```
[FAIL] F-01  토큰 헤더 없이 GET /internal/photos/pending = 200
             (전 사용자 검수대기 사진 URL과 user_id가 그대로 반환)
[FAIL] F-02  POST /internal/users/{uid}/ban = 200
             {"user_id":"660ec0b9-...","is_banned":true,"message":"계정을 정지했습니다."}
[FAIL] L-06  무인증 조회 반환 건수=1,
             샘플=[{'id': '0e1e...', 'user_id': 'e943...', 's3_url': 'https://bucket.s3...'}]
```

**원인** — `app/core/dependencies.py:76-81`

```python
def verify_internal_token(x_internal_token: str = Header(default="")):
    if not settings.INTERNAL_TOKEN:
        # 환경변수 미설정 시 개발 환경으로 간주, 통과
        return
```

환경변수가 비어 있으면 **통과**합니다(fail-open). Railway에 `INTERNAL_TOKEN`을 넣는 것을 한 번 잊으면
인터넷의 누구나 전 사용자 사진 URL과 user_id를 긁어가고, 임의 계정을 정지시킬 수 있습니다.
`/openapi.json`이 공개돼 있어 경로를 찾는 데 탐색조차 필요 없습니다(H-03 참조).

**수정안 (권장) — fail-closed 로 뒤집기**

```python
# app/core/dependencies.py
def verify_internal_token(x_internal_token: str = Header(default="")):
    """AI 서버 등 내부 서비스 콜백 인증.

    미설정 시 통과시키면 배포 환경변수를 한 번 빠뜨리는 것만으로 관리자 API가
    인터넷에 열린다. 설정을 잊었을 때 기능이 죽는 쪽이, 조용히 열리는 쪽보다 안전하다.
    """
    if not settings.INTERNAL_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="내부 서비스 인증이 구성되지 않았습니다.",
        )
    if not secrets.compare_digest(x_internal_token, settings.INTERNAL_TOKEN):
        raise HTTPException(status_code=401, detail="내부 서비스 인증 실패")
```

- `secrets.compare_digest`는 타이밍 공격 방지용입니다. `!=` 비교는 앞자리부터 다른 시점에 리턴합니다.
- 단점: 로컬 개발 시 `.env`에 `INTERNAL_TOKEN`을 반드시 넣어야 합니다 → `.env.example`에 항목 추가로 해결.
- **팀 조율**: AI 서버(Modal) 쪽이 `X-Internal-Token` 헤더를 실제로 보내고 있는지 **먼저 확인**해야 합니다.
  안 보내고 있는데 fail-closed로 바꾸면 사진 검수 콜백이 전부 401로 죽습니다.
  → 순서: ① Modal 쪽 헤더 전송 확인/추가 → ② Railway에 `INTERNAL_TOKEN` 설정 → ③ 이 코드 배포.

**즉시 조치(코드 배포 전에라도)**: Railway 환경변수에 `INTERNAL_TOKEN`이 설정돼 있는지 지금 확인하세요.
비어 있다면 그 자체가 현재 열려 있는 상태입니다.

---

### P0-3 (H-01) 채팅 원문이 외부 AI 서버로 나가는데, 처리방침은 "외부 전송 없음"이라고 적혀 있다

**코드** — `app/routers/chat.py:85-95`

```python
res = httpx.post(
    f"{settings.AI_API_URL}/api/v1/nlp/scam",
    json={..., "content": body.content, "room_id": room_id},
    timeout=2,
)
```

메시지 **원문**이 `AI_API_URL`로 나갑니다.

**처리방침 제8조 2항 (docs/legal/privacy.html) 원문**

> 이 검사는 **회사의 서버 안에서만 이루어지며 메시지 내용이 외부 사업자에게 전송되지 않습니다.**

또한 **제6조 위탁 목록**에 채팅 메시지를 처리하는 수탁자가 없고(Modal은 "프로필 사진의 AI 검수 연산"으로만 기재),
**제7조 국외이전** 표에도 채팅 메시지 항목이 없습니다.
Modal이 미국 리전이라면 국외이전 미고지에 해당합니다.

**왜 P0인가**: Google Play **데이터 보안 양식**은 "제3자와 공유" 여부를 신고하게 되어 있고,
신고 내용과 앱의 실제 동작이 다르면 Play 개발자 정책 위반(허위 신고)으로 **게시 후에도 앱이 정지**됩니다.
심사 반려보다 무거운 유형입니다. 처리방침에 "전송하지 않는다"고 못 박아 둔 상태라 해석의 여지도 없습니다.

**선택지는 둘 중 하나입니다.**

**방안 A — 문서를 사실에 맞춘다 (권장, 코드 변경 없음)**

`docs/legal/privacy.html` 세 곳을 수정:

1. 제6조 위탁 표에 행 추가

| 수탁자 | 위탁 업무 | 처리 국가 |
|---|---|---|
| Modal Labs, Inc. | 채팅 메시지의 사기·스캠 패턴 탐지 연산 | 미국 |

2. 제7조 국외이전 표에 행 추가 — 이전 항목: **채팅 메시지 내용**, 이전 시점: 메시지 전송 시점,
   보유 기간: **분석 완료 즉시 파기(수탁자 별도 보관 없음)**
3. 제8조 2항의 "회사의 서버 안에서만 이루어지며 … 전송되지 않습니다" 문장을
   "수탁자의 분석 서버로 전송되어 검사되며, 분석 후 즉시 파기되고 별도로 보관되지 않습니다"로 교체

- 장점: 코드 변경 0, 기능 유지. 스캠 탐지는 시니어 대상 서비스에서 **실제 이용자 보호에 직결**되므로 끄는 건 손해입니다.
- 단점: 국외이전 고지가 늘어나 가입 화면 고지 문구 검토가 필요할 수 있습니다.
  Modal이 메시지를 실제로 저장하지 않는다는 점은 **위탁계약서로 확인**해야 합니다(문서에 "즉시 파기"라고 쓰는 이상 근거가 필요).

**방안 B — 코드를 문서에 맞춘다**

스캠 탐지를 서버 내부 규칙 기반으로 옮깁니다(정규식/키워드 매칭). 처리방침 제8조 2항이
"규칙 기반으로 검사합니다"라고 이미 적혀 있어 문서와 정확히 일치하게 됩니다.

- 장점: 개인정보 전송 자체가 사라져 가장 깨끗합니다. 문서 수정이 필요 없습니다.
- 단점: 탐지 정확도가 떨어지고, 이미 붙여둔 AI 서버 연동이 사장됩니다.

**팀 조율**: 이건 백엔드 단독 결정이 아닙니다. AI 서버 담당(스캠 모델이 실제로 규칙 기반인지 모델 기반인지)과
법무/문서 담당(=한지수 대표)이 함께 결정해야 합니다. **제 판단은 A입니다** — 기능을 죽이지 않으면서
문서 3곳 수정으로 정합성을 맞출 수 있고, 스캠 탐지는 이 서비스의 타깃 사용자에게 특히 중요한 보호 장치입니다.

---

### P0-4 (D-02) 차단 목록이 닉네임 자리에 실명을 반환한다

**재현 로그**

```
[FAIL] D-02 차단 목록 응답의 개인정보 노출
  nickname 필드값='이영희' / DB 실명='이영희' / DB 닉네임='영희'
```

**원인** — `app/schemas/block.py:15`

```python
class BlockUserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nickname: str = Field(validation_alias="name")   # ← User.name(실명)을 nickname으로 매핑
```

`User` 모델에는 `nickname` 컬럼이 **따로 존재**하는데(`app/models/user.py:47`), 스키마가 굳이 `name`을 끌어옵니다.
`nickname`이 nullable이던 시절의 잔재로 보입니다. 지금은 `RegisterRequest.nickname`이 필수라 실질적으로 항상 값이 있습니다.

**왜 P0인가**: 처리방침 제5조가 **"실명과 휴대전화번호는 다른 회원에게 공개되지 않습니다"**라고 명시합니다.
차단 목록은 상대 회원의 정보를 보여주는 화면이므로 정면 위반입니다.
매칭 피드(`C-02`)와 대화 목록은 정상적으로 닉네임만 내려주고 있어서, **차단 목록만 유일하게 새는 구멍**입니다.

**수정안**

```python
# app/schemas/block.py
class BlockUserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nickname: str
    age: int
    region: str | None = None
```

```python
# app/services/block.py — nickname이 비어 있는 과거 계정 대비
def get_blocks(db: Session, current_user: User) -> dict:
    blocks = db.query(Block).filter(Block.blocker_id == current_user.id).all()
    return {
        "blocks": [
            {
                "id": b.blocked.id,
                "nickname": b.blocked.nickname or "알 수 없음",
                "age": b.blocked.age,
                "region": b.blocked.region,
            }
            for b in blocks
        ]
    }
```

- `nickname or user.name` 으로 폴백하면 **같은 유출이 그대로 남습니다.** 다른 화면들과 달리 여기서는
  `"알 수 없음"`으로 떨어뜨려야 합니다. (매칭 피드의 `nickname or name` 폴백도 같은 이유로 점검 대상입니다 —
  `app/services/matching.py:105,278` 및 `app/services/users.py:13`. 다만 그쪽은 nickname이 필수가 된 뒤
  가입한 계정만 존재한다면 실제 노출은 없습니다. **DB에서 `select count(*) from users where nickname is null` 확인 권장.**)
- 응답 구조는 그대로라 **앱 수정 불필요**. 값만 실명 → 닉네임으로 바뀝니다.

---

### P0-5 (G-07) 탈퇴·사진삭제 시 S3 원본이 남는다

**코드** — `app/services/users.py:92`

```python
db.query(UserPhoto).filter(UserPhoto.user_id == user.id).delete()   # DB 행만 삭제
```

`app/routers/users.py:181`의 `delete_photo()`도 동일하게 `db.delete(photo)`만 합니다.
**S3 객체를 지우는 코드가 저장소 어디에도 없습니다.**

**문서와의 불일치**

- 처리방침 제4조: "프로필 사진 — … **저장소에 남은 원본 파일은 30일 이내 파기**"
- 계정 삭제 안내 페이지: "즉시 삭제·익명화 — 프로필 사진: **삭제**"

**왜 P0인가**: Google Play는 계정 삭제 정책에서 **앱 내 삭제 경로 + 웹 삭제 요청 URL**과 함께
"삭제 요청 시 데이터가 실제로 삭제될 것"을 요구합니다. 데이터 보안 양식에도 "삭제 요청 가능" 항목이 있습니다.
S3 URL이 퍼블릭 버킷이라면 URL을 아는 사람은 탈퇴 후에도 얼굴 사진을 계속 볼 수 있습니다.

**먼저 확인할 것**: S3 버킷이 퍼블릭인지 프리사인드인지. `app/routers/users.py:138`에서
`https://{bucket}.s3.{region}.amazonaws.com/{key}` 형태의 **직링크**를 그대로 저장·반환하고 있어
퍼블릭 리드일 가능성이 높습니다. 퍼블릭이면 심각도가 한 단계 더 올라갑니다.

**수정안 A (권장) — 삭제 시점에 S3에서도 지운다**

```python
# app/services/s3.py (신규)
import logging
import boto3
from urllib.parse import urlparse
from app.core.config import settings

logger = logging.getLogger(__name__)

def _client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

def delete_photo_objects(s3_urls: list[str]) -> None:
    """S3 원본 삭제. 실패해도 탈퇴 자체는 막지 않는다(사용자 권리 행사가 우선)."""
    keys = [{"Key": urlparse(u).path.lstrip("/")} for u in s3_urls if u]
    if not keys:
        return
    try:
        _client().delete_objects(
            Bucket=settings.AWS_S3_BUCKET, Delete={"Objects": keys}
        )
    except Exception:
        logger.exception("S3 원본 삭제 실패 — 수동 파기 대상: %s", keys)
```

```python
# app/services/users.py
def delete_account(db: Session, user: User) -> None:
    ...
    photos = db.query(UserPhoto).filter(UserPhoto.user_id == user.id).all()
    urls = [p.s3_url for p in photos]
    db.query(UserPhoto).filter(UserPhoto.user_id == user.id).delete()
    db.commit()
    delete_photo_objects(urls)   # 커밋 후 — S3 실패가 탈퇴를 롤백시키면 안 된다
```

- 장점: 문서의 "즉시 삭제"와 코드가 일치합니다. 별도 인프라가 필요 없습니다.
- 단점: S3 호출이 탈퇴 응답 시간에 포함됩니다(수 백 ms). 실패 시 로그만 남고 조용히 유실될 수 있어
  **실패 로그를 Sentry로 잡아 수동 파기하는 운영 절차**가 함께 필요합니다.
- 트레이드오프: 완전 무결하게 하려면 삭제 큐 테이블 + 재시도 워커가 정석이지만, 현재 규모(MVP)에는 과합니다.
  대신 문서의 "30일 이내 파기"라는 표현이 **재시도 여유를 이미 허용**하고 있으므로 A로 충분합니다.

**수정안 B — S3 수명주기 규칙**: `photos/` 프리픽스에 30일 만료 규칙을 걸어 두는 방식.
코드 변경이 없지만 **탈퇴하지 않은 사용자의 사진까지 30일 뒤 사라지므로 그대로는 쓸 수 없습니다.**
탈퇴분만 `deleted/` 프리픽스로 옮기고 거기에 규칙을 거는 조합이면 가능합니다 — A보다 복잡합니다.

**팀 조율**: 인프라(S3 버킷 정책·IAM에 `s3:DeleteObject` 권한이 있는지) 확인이 선행돼야 합니다.
현재 IAM 키에 업로드 권한만 있으면 삭제가 전부 실패합니다.

---

## 3. P1 — 출시 전 처리 권장

### P1-1 (B-04/B-05) `/auth/register`에 인증코드 시도 제한이 없다

**재현 로그**

```
[FAIL] B-04 틀린 코드 60회 연속 시도 — 차단/지연 없음(모두 400)
[FAIL] B-05 정답 코드 register=200
             → 15분 창 안에서 6자리 전수조사 시 타인 번호 계정 생성 가능
```

**공격 시나리오**: 피해자가 SMS 인증만 마치고 가입을 완료하지 않은 15분(`REGISTER_SMS_VERIFY_WINDOW`) 동안,
공격자가 그 번호로 `/auth/register`에 6자리 코드를 무차별 대입하면 **타인 명의로 계정이 생성**됩니다.
`verify_sms_code()`에는 5회 제한이 있지만(`MAX_VERIFY_ATTEMPTS`), `_ensure_sms_verified_for_register()`는
단순 SELECT라 **시도 횟수를 세지도, 늘리지도 않습니다** (`app/services/auth.py:144-171`).

**수정안**

```python
# app/services/auth.py
def _ensure_sms_verified_for_register(db: Session, phone: str, code: str) -> None:
    latest = (
        db.query(SmsVerification)
        .filter(SmsVerification.phone == phone)
        .order_by(SmsVerification.created_at.desc())
        .first()
    )
    if latest is None:
        raise HTTPException(400, "SMS 인증을 먼저 완료해주세요.")

    # 틀린 코드로 오면 시도 횟수를 올리고, 한도를 넘으면 인증 자체를 폐기한다.
    if latest.code != code or not latest.is_used:
        latest.attempt_count += 1
        if latest.attempt_count >= MAX_VERIFY_ATTEMPTS:
            db.delete(latest)
        db.commit()
        raise HTTPException(400, "SMS 인증을 먼저 완료해주세요.")

    if latest.created_at < datetime.now(timezone.utc) - REGISTER_SMS_VERIFY_WINDOW:
        raise HTTPException(400, "SMS 인증을 먼저 완료해주세요.")
```

- 응답 메시지를 모든 실패에 대해 동일하게 유지한 것은 의도적입니다. "코드가 틀림"과 "인증 안 함"을 구분해 주면
  공격자에게 진행 상황을 알려주게 됩니다.
- 앱 수정 불필요. 정상 흐름(verify 직후 같은 코드로 register)은 그대로 통과합니다.
- 대안으로 IP 기반 rate limit(slowapi 등)도 가능하지만 의존성이 늘고, 위 방식이 근본 원인에 더 정확히 대응합니다.

### P1-2 (D-10/D-11) Play UGC 정책 — 콘텐츠 단위 신고와 텍스트 모더레이션이 없다

| 항목 | 현재 | Play 요구 |
|---|---|---|
| 사용자 신고 | `POST /reports` ✅ | 필요 |
| 사용자 차단 | `POST /blocks/{id}` ✅ | 필요 |
| 사진 검수 | AI + 관리자 검수 ✅ | 필요 |
| **메시지/사진 단위 신고** | ❌ 없음 | 필요 |
| **닉네임·자기소개 모더레이션** | ❌ 없음 | 필요 |
| **신고된 콘텐츠 개별 삭제** | ❌ 계정 정지만 가능 | 필요 |

`bio`, `life_story`, `nickname`은 어떤 필터도 거치지 않고 즉시 다른 회원에게 노출됩니다.
신고가 들어와도 **텍스트만 내리는 수단이 없어** 계정 정지 아니면 방치, 둘 중 하나입니다.

Play는 데이팅 카테고리에 특히 엄격합니다. 최소한 다음 두 개는 출시 전 확보를 권합니다.

```python
# app/schemas/report.py — 신고 대상을 확장
class ReportTargetEnum(str, enum.Enum):
    user = "user"
    message = "message"
    photo = "photo"
    profile_text = "profile_text"

class ReportRequest(BaseModel):
    reported_id: uuid.UUID
    target_type: ReportTargetEnum = ReportTargetEnum.user   # 기본값 = 기존 동작
    target_id: uuid.UUID | None = None                       # 메시지/사진 id
    reason: str = Field(min_length=5, max_length=500)
```

```python
# app/routers/internal.py — 콘텐츠 단위 내리기
@router.post("/messages/{message_id}/hide", dependencies=[Depends(verify_internal_token)])
def hide_message(message_id: uuid.UUID, db: Session = Depends(get_db)):
    ...
```

- `target_type` 기본값을 `user`로 두면 **기존 앱이 그대로 동작**합니다(하위 호환).
- 단점: 관리자 화면이 없어 실제 처리가 수동입니다. 정식 어드민 UI는 별도 스코프로 이미 분리돼 있습니다
  (`app/routers/internal.py:40` 주석). 출시 시점에는 `/internal` API + 담당자 수동 대응으로 갈음하되,
  **Play Console에 "신고 접수 후 24시간 내 검토" 같은 모더레이션 정책을 명시**해야 합니다.
- **팀 조율**: 앱에 "이 메시지 신고" / "이 사진 신고" 메뉴가 필요합니다. 백엔드 스키마를 먼저 넓혀 두면
  앱은 준비되는 대로 붙일 수 있습니다.

### P1-3 (K-02) 마케팅 수신동의를 철회할 API가 없다

```
[FAIL] K-02  settings 스키마는 chat_push_enabled만 받음(응답={'chat_push_enabled': False})
             프로필 수정도 marketing_consent 미지원
```

가입 시 `marketing_consent`를 받지만(`app/schemas/auth.py` `RegisterRequest`),
`UpdateSettingsRequest`에도 `UpdateProfileRequest`에도 해당 필드가 없습니다.
처리방침 제1조 3항 **"동의는 언제든지 철회할 수 있습니다"**와 불일치합니다.

```python
# app/schemas/users.py
class UpdateSettingsRequest(BaseModel):
    chat_push_enabled: bool | None = None
    marketing_consent: bool | None = None      # 추가

class UpdateSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    chat_push_enabled: bool
    marketing_consent: bool                     # 추가
```

```python
# app/services/users.py
def update_settings(db: Session, user: User, data: UpdateSettingsRequest) -> User:
    if data.chat_push_enabled is not None:
        user.chat_push_enabled = data.chat_push_enabled
    if data.marketing_consent is not None:
        user.marketing_consent = data.marketing_consent
    db.commit()
    db.refresh(user)
    return user
```

- `bool` → `bool | None`으로 바꾸는 건 **완화**라 기존 앱 요청이 그대로 통과합니다.
- 앱에 설정 화면 토글 1개 추가가 필요합니다(앱 작업).

### P1-4 (L-01) FCM 토큰이 계정 간 중복된다 — 남의 알림이 이전 사용자에게 간다

```
[FAIL] L-01 동일 토큰을 보유한 계정 수=2
```

`POST /users/me/fcm-token`은 그냥 덮어쓰기만 합니다(`app/routers/users.py:79`).
같은 기기에서 A가 로그아웃하고 B가 로그인하면 **두 계정이 같은 토큰**을 갖게 되고,
A에게 오는 매칭·메시지 알림이 B의 기기로 발송됩니다. 알림 본문에는 **메시지 앞 50자가 그대로 실립니다**
(`app/services/fcm.py:165`). 대화 내용이 제3자에게 노출되는 경로입니다.

```python
# app/routers/users.py
@router.post("/me/fcm-token")
def update_fcm_token(body: FcmTokenRequest, current_user=..., db=...):
    # 같은 기기 토큰을 들고 있는 다른 계정에서 회수한다.
    # 회수하지 않으면 기기를 넘겨받은 사람에게 이전 사용자의 알림이 계속 간다.
    db.query(User).filter(
        User.fcm_token == body.fcm_token, User.id != current_user.id
    ).update({"fcm_token": None}, synchronize_session=False)
    current_user.fcm_token = body.fcm_token
    db.commit()
    return {"message": "저장 완료"}
```

앱 수정 불필요. 인덱스가 없어 풀스캔이 나므로 `users.fcm_token`에 인덱스를 추가하는 마이그레이션을 함께 권합니다.

### P1-5 (C-06) 읽음 처리 코드가 없어 안읽음 배지가 사라지지 않는다

```
[PASS] C-05 unread_count=1
[FAIL] C-06 이력 조회 후에도 unread_count=1
```

`ChatMessage.is_read` 컬럼과 집계 쿼리(`app/services/matching.py:256`)는 있는데,
**`is_read`를 `True`로 바꾸는 코드가 저장소 전체에 없습니다.** 배지가 영원히 남습니다.

```python
# app/routers/chat.py — get_messages 안, 조회 직후
db.query(ChatMessage).filter(
    ChatMessage.room_id == room.id,
    ChatMessage.sender_id != current_user.id,
    ChatMessage.is_read == False,
).update({"is_read": True}, synchronize_session=False)
db.commit()
```

- 조회 = 읽음으로 처리하는 방식입니다. 별도 `POST /read` 엔드포인트를 두는 게 더 정확하지만
  앱 작업이 늘고, 이 앱의 채팅 화면은 진입 시 이력을 항상 부르므로 실질 차이가 없습니다.
- 응답에 실린 `is_read` 값은 갱신 전 값이라 살짝 어긋납니다. 신경 쓰인다면 `update` 후 재조회하거나
  응답 직렬화 시 `True`로 고정하면 됩니다.

### P1-6 (J-01) 가입 시 `points` 레코드가 생성되지 않는다

```
[FAIL] J-01 가입 직후 points 행 수=0
```

`register_user()`(`app/services/auth.py:174-199`)가 `User`와 `UserProfile`만 만듭니다.
PR #18 설명에는 "register_user 시 Point 레코드 자동 생성"이 적혀 있었으나 **현재 코드에는 없습니다**
(중간 머지에서 유실된 것으로 보입니다). 결과적으로 `POST /points/use`는 항상 "포인트가 부족합니다"로 실패합니다.
`GET /points`는 `point.balance if point else 0`으로 방어돼 있어 조회만 정상으로 보입니다.

```python
# app/services/auth.py — register_user 안
profile = UserProfile(user_id=user.id)
db.add(profile)
db.add(Point(user_id=user.id, balance=0))   # 추가
db.commit()
```

기존 가입자용 백필도 필요합니다:

```sql
INSERT INTO points (user_id, balance, created_at, updated_at)
SELECT u.id, 0, now(), now() FROM users u
LEFT JOIN points p ON p.user_id = u.id WHERE p.id IS NULL;
```

### P1-7 (I-01) 포인트 차감에 잠금이 없어 이중 차감된다

```
[FAIL] I-01 100P 잔액에 100P 사용 8회 동시 요청 → 성공 2건, 최종 잔액=0
```

`use_points()`가 SELECT → 검사 → UPDATE를 잠금 없이 수행합니다(`app/services/point.py:24-30`).
동시 요청이 같은 잔액을 읽고 각자 차감해 **100P로 200P를 소비**했습니다.

```python
# app/services/point.py
point = (
    db.query(Point)
    .filter(Point.user_id == current_user.id)
    .with_for_update()          # 행 잠금 — 같은 유저의 동시 차감을 직렬화
    .first()
)
```

- `with_for_update()`는 PostgreSQL의 `SELECT ... FOR UPDATE`입니다. 한 줄로 해결됩니다.
- 지금은 포인트를 충전할 경로가 없어(결제 비활성) 실피해가 없지만, **결제를 켜는 순간 금전 손실**이 됩니다.
  결제 재개 전에는 반드시 들어가야 합니다.

### P1-8 (G-04) 탈퇴·정지 계정도 refresh 토큰으로 액세스 토큰을 계속 받는다

```
[FAIL] G-04 status=200
```

`refresh_access_token()`이 유저 존재만 확인하고 `is_active`/`is_banned`를 보지 않습니다
(`app/services/auth.py:238-244`). 발급된 액세스 토큰은 `get_current_user`에서 막히므로(G-03 PASS)
실제 데이터 접근은 없지만, 탈퇴·정지 계정이 무기한 토큰을 받아가는 상태 자체가 깔끔하지 않습니다.

```python
# app/services/auth.py
user = db.query(User).filter(User.id == subject).first()
if not user or not user.is_active or user.is_banned:
    raise HTTPException(401, "등록된 회원이 아닙니다.")
```

- 앱 입장에서 401을 받으면 로그인 화면으로 보내면 되므로 오히려 동작이 명확해집니다.

### P1-9 (L-03) 탈퇴한 상대와의 채팅방이 활성으로 남는다

```
[INFO] L-02 남은 대화 1건, 표시 이름='탈퇴한 사용자'
[FAIL] L-03 탈퇴한 상대에게 메시지 전송 status=200
```

`delete_account()`가 `ChatRoom.is_active`를 내리지 않아, 남은 쪽은 응답이 절대 오지 않는 방에
계속 말을 걸 수 있습니다. `leave_room()`은 같은 상황에서 방을 비활성화하는데(`app/routers/chat.py:154`),
탈퇴는 그러지 않아 두 경로의 동작이 어긋납니다.

```python
# app/services/users.py — delete_account 안
room_ids = (
    db.query(ChatRoom.id)
    .join(Match, ChatRoom.match_id == Match.id)
    .filter(or_(Match.user1_id == user.id, Match.user2_id == user.id))
    .subquery()
)
db.query(ChatRoom).filter(ChatRoom.id.in_(select(room_ids))).update(
    {"is_active": False}, synchronize_session=False
)
```

---

## 4. P2 — 기록해 두고 이후 처리

| ID | 내용 | 비고 |
|---|---|---|
| D-09 | 서로 다른 계정 3개면 임의 사용자를 즉시 정지시킬 수 있음(`app/services/report.py:285`). 해제 경로가 `/internal`뿐이라 앱 내 이의제기 수단이 없음 | 자동 정지 기준을 "고유 신고자 3명 + 관리자 확인" 2단계로 나누거나, 정지 화면에 문의 메일 링크 노출 |
| H-03 | `/openapi.json`이 인증 없이 200. `/internal` 관리자 경로까지 전부 공개 | 프로덕션에서 `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)` 또는 환경변수 분기 |
| K-06 | `CORS_ALLOWED_ORIGINS` 미설정 시 `["*"]` + `allow_credentials=True`. 프리플라이트에서 임의 Origin이 그대로 반영됨 | 모바일 앱은 CORS 영향이 없지만, Railway 환경변수 설정 여부를 확인 |
| I-04 | 차단 관계면 `_get_room_or_403`이 먼저 403을 내서 채팅방 나가기가 불가(`app/routers/chat.py:60`) | 목록에서는 이미 숨겨져 실피해 없음. `leave_room`만 차단 검사를 건너뛰면 해결 |
| E-03/E-04 | `PAYMENTS_ENABLED=false`여도 `GET /payments`(200), `DELETE /payments/subscriptions`(400)는 열려 있음 | 기존 결제자를 위한 의도된 설계(`app/routers/payment.py:24` 주석). 유지 무방 |
| — | `pyproject.toml`에 `google-cloud-vision==3.7.0`이 있으나 코드에서 미사용 | 처리방침 위탁 목록에도 없음. 의존성 정리 권장 |
| — | 처리방침 제6조에 "OpenAI — 자기소개 문구 자동 생성"이 기재돼 있으나 백엔드에 해당 코드 없음 | 앱/AI 서버에서 직접 호출하는지 확인 필요. 어느 쪽도 아니면 문서에서 삭제 |
| — | `app/schemas/auth.py:9` `# TODO: 배포 전 examples 제거` | `/docs`를 닫으면 자동 해소 |
| — | `app/core/dependencies.py:26` `from app.models.user import User` 중복 임포트 | 정리 |

---

## 5. 정상 동작 확인 항목 (PASS 32건)

Play 심사에서 실제로 확인하는 흐름은 대부분 통과했습니다.

**심사관 로그인 경로 (Play Console '앱 액세스 권한')**

```
[PASS] A-01 REVIEW_TEST_PHONE 고정코드 가입 — sms/send=200 verify=200 register=200
[PASS] A-02 고정코드 반복 로그인 — 횟수 제한 없이 재사용 가능
```

해외 번호라 SMS를 못 받는 심사관을 위한 우회 경로가 정상 동작합니다. rate limit도 우회하므로
심사관은 P0-1(가입 직후 로그인 불가)에 걸리지 않습니다.

**UGC 안전장치**

```
[PASS] C-02 추천 카드에 실명/전화번호 미노출
[PASS] C-07 제3자의 타인 채팅방 접근 차단 (403)
[PASS] D-01 사용자 차단 API
[PASS] D-03 차단 후 대화 목록에서 제거 (남은 대화 0건)
[PASS] D-04 차단당한 쪽의 메시지 전송 차단 (403)
[PASS] D-05 차단 관계 양방향 피드 제외
[PASS] D-06/D-07 신고 접수 / 중복 신고 방지
[PASS] D-08 신고 3회 누적 → 자동 정지, 정지 계정 API 접근 403
[PASS] L-05 미승인 사진의 타인 노출 차단 (상대 카드 photos=[])
```

차단이 **양방향**으로 동작하는 점(피드·좋아요·채팅·대화목록 전부)이 특히 잘 되어 있습니다.
Play UGC 정책에서 가장 자주 지적받는 부분입니다.

**계정 삭제 (Play 필수 요건)**

```
[PASS] G-01 앱 내 회원 탈퇴 (204)
[PASS] G-02 users row = deleted:c1fc...|탈퇴한 사용자|탈퇴한 사용자|NULL|false
[PASS] G-03 탈퇴 후 기존 액세스 토큰 무효화 (403)
[PASS] G-05 탈퇴한 번호로 재로그인 불가 (400)
[PASS] G-06 동일 번호 재가입 가능 (200, 신규 계정)
```

익명화·FCM 토큰 제거·재가입 허용이 계정 삭제 안내 페이지 문구와 정확히 일치합니다.
**S3 원본(G-07)만 예외**입니다.

**결제 차단 (Play 결제 정책)**

```
[PASS] E-01 포인트 충전 404
[PASS] E-02 구독 결제 404
```

`PAYMENTS_ENABLED=false`가 서버 측에서도 확실히 닫습니다. 403이 아니라 404를 주는 것도 좋은 선택입니다.

**업로드 검증 / 프로필 무결성**

```
[PASS] K-01 프로필 수정으로 나이·성별 변조 불가 (요청 후에도 62/male 유지)
[PASS] K-03 채팅 푸시 수신 거부 설정 반영
[PASS] K-04 확장자·Content-Type 위조 파일 차단 (매직바이트 검사)
[PASS] K-05 비이미지 Content-Type 차단
[PASS] L-04 검수 대기·거부 사진의 본인 노출 (pending=1)
```

`UpdateProfileRequest`에 `age`/`gender`가 없어 나이 변조가 원천 차단됩니다.
만 50세 이상 제한(`B-03`, 422)과 함께 데이팅 앱 연령 정책에 부합합니다.

---

## 6. Google Play Console 제출 체크리스트

백엔드 저장소 밖(앱·콘솔) 담당자가 확인해야 하는 항목입니다.

### 6-1. 데이터 보안(Data safety) 양식 — 코드에서 도출한 실제 수집 항목

| Play 분류 | 세부 항목 | 근거 | 수집 | 공유 | 필수 | 목적 |
|---|---|---|---|---|---|---|
| 개인 정보 | 이름 | `users.name` | O | X | 필수 | 앱 기능, 계정 관리 |
| 개인 정보 | 전화번호 | `users.phone` | O | X | 필수 | 계정 관리, 사기 방지 |
| 개인 정보 | 기타(나이·성별·지역) | `users.age/gender/region` | O | X | 필수 | 앱 기능 |
| 개인 정보 | 기타(자기소개·인생이야기·직업·키·관심사) | `user_profiles` | O | X | 선택 | 앱 기능 |
| 사진 및 동영상 | 사진 | `user_photos.s3_url` | O | X | 선택 | 앱 기능 |
| 메시지 | 앱 내 메시지 | `chat_messages.content` | O | **O ※** | 필수 | 앱 기능, 사기 방지 |
| 앱 활동 | 앱 내 검색·상호작용 | `likes/matches/blocks/reports/point_history` | O | X | 필수 | 앱 기능 |
| 앱 정보 및 성능 | 비정상 종료 로그 | Sentry | O | O | 필수 | 분석 |
| 기기 또는 기타 ID | 기기 ID | `users.fcm_token` | O | O(Google FCM) | 필수 | 앱 기능 |

**※ 메시지의 "공유" 표기는 P0-3(H-01)의 결론에 따라 확정됩니다.**
방안 A(외부 AI 유지)를 택하면 공유 = O로 신고하고 처리방침도 수정해야 합니다.
방안 B(서버 내부 처리)를 택하면 공유 = X입니다. **여기서 잘못 신고하면 앱 정지 사유입니다.**

- 전송 중 암호화: **예** (Railway HTTPS)
- 데이터 삭제 요청 가능: **예** — 단, G-07(S3 원본) 처리 후에 신고해야 사실과 일치합니다
- 위치 정보: **수집 안 함** (`region`은 이용자가 직접 고른 시·도 텍스트, GPS 아님)
- 광고 ID: **수집 안 함** — 앱 매니페스트에 `com.google.android.gms.permission.AD_ID`가
  선언돼 있지 않은지 확인 필요(라이브러리가 자동 추가하는 경우가 있음)

### 6-2. 앱 콘텐츠 / 정책 선언

- [ ] **개인정보처리방침 URL** — `docs/legal/privacy.html` (GitHub Pages 게시 확인)
- [ ] **계정 삭제 URL** — `docs/legal/account-deletion.html` 등록 (앱 내 삭제 + 웹 요청 경로 양쪽 필요, 둘 다 확보됨)
- [ ] **앱 액세스 권한** — `REVIEW_TEST_PHONE` / `REVIEW_TEST_CODE` 값을 기재.
      "인증번호 요청 버튼을 누른 뒤 고정 코드 입력"이라는 절차 설명을 함께 적어야 합니다(A-03 참고)
- [ ] **콘텐츠 등급 설문** — 사용자 간 상호작용 O, 사용자 콘텐츠 공유 O, 위치 공유 X, 성인용 데이팅
- [ ] **데이팅 앱 카테고리** — 별도 선언 필요
- [ ] **타깃 API 레벨** — 신규 앱은 Android 15(API 35) 이상 필수
- [ ] **권한** — `READ_MEDIA_IMAGES`(사진 선택), `POST_NOTIFICATIONS`(알림).
      처리방침 제12조가 "카메라·마이크는 라이브러리가 선언한 것"이라 설명하고 있으므로,
      가능하면 매니페스트에서 실제로 제거하는 편이 심사 마찰이 적습니다
- [ ] **결제** — 현재 유료 기능 없음. **재개 시 반드시 Google Play 결제 라이브러리 사용**.
      외부 PG(포트원)로 디지털 재화를 판매하면 Play 결제 정책 위반입니다.
      약관 제10조 2항이 *"결제는 회사가 지정한 전자지급결제대행사를 통해 처리되며"*로 되어 있어
      **유료 재개 시 약관 문구도 함께 고쳐야 합니다**(제11조 5항에 마켓 인앱결제 언급은 이미 있음)
- [ ] **UGC 모더레이션 정책** — 신고 접수 후 검토 기한을 명시 (D-10/D-11 대응과 연동)

### 6-3. 배포 환경변수 (Railway) — 출시 전 필수 확인

| 변수 | 확인 사항 | 미설정 시 결과 |
|---|---|---|
| `INTERNAL_TOKEN` | **반드시 설정** | 관리자 API 무인증 개방 (P0-2) |
| `PAYMENTS_ENABLED` | `false` 유지 | true면 외부 PG 결제가 열려 Play 결제 정책 위반 |
| `CORS_ALLOWED_ORIGINS` | 설정 권장 | `*` + credentials 조합 |
| `REVIEW_TEST_PHONE` / `REVIEW_TEST_CODE` | **둘 다** 설정 | 하나만 넣으면 기능이 통째로 꺼져 심사관 로그인 불가 (`_is_review_phone` 가드) |
| `SECRET_KEY` | 로컬/개발과 다른 값 | — |
| `FIREBASE_CREDENTIALS_JSON` | Base64 인코딩 값 | 푸시 알림 전부 미발송 (초기화 스킵 후 로그 경고만) |
| `AI_API_URL` / `AI_IMAGE_API_URL` | 설정 | 스캠 탐지·사진 검수 무동작(예외를 삼키므로 조용히 실패) |
| `SENTRY_DSN` | 설정 권장 | S3 삭제 실패 등을 잡을 수단이 사라짐 (P0-5 운영 절차와 연결) |

---

## 7. 권장 처리 순서

1. **환경변수 점검** (코드 배포 없이 지금 가능) — `INTERNAL_TOKEN`, `PAYMENTS_ENABLED`, `REVIEW_TEST_*`
2. **P0-3 결정 회의** — 채팅 메시지 외부 전송을 유지할지(문서 수정) 걷어낼지(코드 수정).
   데이터 보안 양식이 이 결정에 걸려 있어 **가장 먼저 정해져야** 합니다
3. **앱 수정이 필요 없는 P0/P1 일괄 처리** — D-02, G-07, B-04/B-05, L-01, C-06, J-01, I-01, G-04, L-03, F-01
4. **앱 수정이 필요한 항목** — B-00(수정안 A), K-02, D-10/D-11
5. **P2 정리 후 Play Console 제출**

---

## 부록 A. 재현 방법

```bash
# 1. QA 환경 기동 (1장 참고)
# 2. 전체 시나리오 실행
uv run python scripts/qa_play_store.py       # 본 리포트의 A~K 항목
uv run python scripts/qa_play_store_extra.py # L 항목 (FCM/탈퇴/사진)
```

각 스크립트는 실행 시작 시 테이블을 TRUNCATE하므로 **반복 실행해도 같은 결과**가 나옵니다.
운영 DB에는 절대 연결하지 마세요.

## 부록 B. 검증하지 못한 영역

- **S3 실제 업로드·삭제** — AWS 자격증명이 없어 `boto3` 호출 직전까지만 검증했습니다.
  버킷 퍼블릭 여부, IAM `s3:DeleteObject` 권한은 인프라에서 확인이 필요합니다
- **FCM 실제 발송** — Firebase 자격증명이 없어 초기화 스킵 경로만 확인했습니다.
  토큰 중복(L-01)은 DB 상태로 검증했으며, 실제 발송 대상 오류는 논리적 귀결입니다
- **AI 서버 연동** — `AI_API_URL` 미설정이라 스캠 탐지·사진 검수 콜백은 예외 처리 경로만 탔습니다.
  두 곳 모두 `except Exception: pass`라 실패해도 기능이 계속 진행됩니다(의도된 설계)
- **포트원 결제** — `PAYMENTS_ENABLED=false`로 엔드포인트가 닫혀 있어 결제 검증 로직 자체는 미실행.
  결제 재개 시 별도 QA가 필요합니다(특히 I-01 포인트 동시성)
- **안드로이드 앱** — 이 저장소는 백엔드 전용입니다. 타깃 API 레벨, 권한 선언, 광고 ID,
  인앱결제 라이브러리는 앱 저장소에서 확인해야 합니다
