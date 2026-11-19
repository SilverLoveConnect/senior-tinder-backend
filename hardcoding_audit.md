# 하드코딩 점검 보고서

> 점검일: 2026-11-19 · 기준: `main` (PR #63 머지 직후, `c7bcc6c`)
> 범위: `app/`, `scripts/`, `alembic/env.py`, `alembic.ini`, `railway.json`, `.env.example`, `docs/`, git 이력 전체
> 상태: **점검만 했다. 코드는 고치지 않았다.** 아래 "제안" 항목은 확인을 받은 뒤 반영한다.

---

## 0. 판정 기준 — "하드코딩"을 다 나쁘다고 보지 않았다

| 종류 | 판단 |
|---|---|
| 비밀 값(API 키, 비밀번호, 토큰)이 코드에 박힘 | **반드시 고친다** |
| 환경마다 다른 값(URL, 버킷, 도메인)이 코드에 박힘 | 고친다 |
| 같은 규칙 숫자가 여러 파일에 흩어져 있음 | 한 곳으로 모은다 (값을 바꿀 때 빠뜨리는 버그 예방) |
| 바뀔 일이 거의 없는 규칙(정규식, 금칙어, 지역 목록, 외부 API 공식 주소) | **코드에 두는 게 맞다** — 환경변수로 빼면 오히려 실수할 곳만 늘어난다 |

---

## 1. 비밀 값 — ✅ 문제 없음

- 코드에 박힌 API 키·비밀번호·토큰 **없음**. 전부 `settings.*`(`app/core/config.py`)로 읽는다.
  - 예: `app/services/sms.py:19-20` `settings.SOLAPI_API_KEY/SECRET`, `app/core/ai.py` `settings.AI_API_KEY`
- `.env`는 `.gitignore:17`로 제외됨.
- **git 이력 전체**에서 `.env`, 서비스 계정 JSON, `.pem`, `.p8` 등이 한 번이라도 커밋된 적 **없음** (`git log --all --diff-filter=A`로 확인).
- `DATABASE_URL`, `SECRET_KEY`는 비어 있으면 기동 실패하도록 `Field(min_length=1)` — 좋은 패턴.
- `alembic.ini:64` `sqlalchemy.url =` 빈 값, `alembic/env.py`에서 환경변수로 주입 — 문제 없음.

---

## 2. 환경별 값 — ✅ 대부분 문제 없음

| 위치 | 값 | 판단 |
|---|---|---|
| `app/routers/users.py:147` | `https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}` | 버킷·리전은 settings에서 읽음. ✅ |
| `app/services/fcm.py:33` | `EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"` | Expo 공식 고정 주소. 코드에 두는 게 맞음 ✅ |
| `app/services/payment.py:32` | `PORTONE_BASE_URL = "https://api.iamport.kr"` | 포트원 V1 공식 고정 주소 ✅ |
| `app/routers/users.py:202`, `chat.py:87` | `f"{settings.AI_API_URL}/api/v1/nlp/..."` | 호스트는 settings, 경로는 AI 서버 API 계약. ✅ |
| `scripts/review_photos.json` | `https://sinabro-photos.s3.ap-northeast-2.amazonaws.com/photos/review-demo/...` | 심사용 데모 사진 목록. 코드에서 참조하지 않는 수동 작업용 파일. 공개 URL일 뿐 비밀 아님 ✅ (버킷을 바꾸면 같이 바꿔야 한다는 것만 기억) |

---

## 3. 고칠 만한 것 (중요도 순)

### 3-1. [중] `.env.example`에 설정값 10개가 빠져 있음
`config.py`에는 있는데 `.env.example`에는 없는 항목:

```
REFRESH_TOKEN_EXPIRE_DAYS, FIREBASE_CREDENTIALS_JSON, AI_API_URL, AI_IMAGE_API_URL,
AI_API_KEY, PORTONE_IMP_KEY, PORTONE_IMP_SECRET, PAYMENTS_ENABLED,
SUPABASE_SERVICE_ROLE_KEY, INTERNAL_TOKEN
```
- **왜 문제인가:** 하드코딩은 아니지만, 팀원이 `.env.example`만 보고 `.env`를 만들면 **AI 서버 연동·내부 콜백 인증(`INTERNAL_TOKEN`)이 조용히 꺼진 채로** 돌아간다. 에러가 안 나서 원인 찾기가 어렵다.
- **제안:** `.env.example`에 빈 값 + 한 줄 설명으로 추가. 코드 변경 없음, 위험 없음.

### 3-2. [중] 신뢰점수(trust_score) 숫자가 5개 파일에 흩어져 있음
| 값 | 위치 |
|---|---|
| 기본값 50 | `models/user.py:144`, `services/matching.py:99`, `services/matching.py:110`, `services/users.py:26` |
| 점수 범위 0~100 | `services/manner.py:19` |
| 등급 경계 90 / 70 | `services/manner.py:36, 38` |
| 가감점 +10 (프로필 완성) | `services/users.py:82` |
| 가감점 +15 (사진 승인) | `services/internal.py:49, 107` (같은 값 2번) |
| 가감점 -10 (신고) | `services/report.py:45` |

- **왜 문제인가:** 기본값을 60으로 바꾸려면 4곳을 다 고쳐야 한다. 하나라도 빠지면 프로필 없는 회원의 점수가 화면마다 다르게 보인다. 사진 승인 +15도 2곳이라 한쪽만 바뀔 수 있다.
- **제안:** `app/services/manner.py`(이미 점수 계산을 담당하는 레이어) 위쪽에 상수로 모은다.
  ```python
  # app/services/manner.py
  DEFAULT_TRUST_SCORE = 50
  TRUST_SCORE_MIN, TRUST_SCORE_MAX = 0, 100
  GRADE_GOLD_MIN, GRADE_SILVER_MIN = 90, 70
  DELTA_PROFILE_COMPLETE = 10
  DELTA_PHOTO_APPROVED = 15
  DELTA_REPORTED = -10
  ```
  다른 파일은 `from app.services.manner import DEFAULT_TRUST_SCORE`처럼 가져다 쓴다.
- **다른 방법:** `config.py` 환경변수로 빼기 → **비추천.** 운영 중에 환경변수만 바꾸면 이미 쌓인 점수와 기준이 어긋난다. 점수 규칙은 코드 리뷰를 거쳐 바꾸는 게 맞다.
- **주의:** `models/user.py:144`의 `default=50`은 DB 기본값이라 상수를 써도 되지만, `server_default`가 아니어서 **마이그레이션은 필요 없다.** (값을 바꾸는 순간에도 기존 행은 그대로.)
- **팀원 영향:** 동작 변경 없음. 점수 관련 코드를 만지는 팀원이 앞으로 상수를 쓰면 된다.

### 3-3. [하] 휴대폰 번호 규칙이 3곳에서 다름
| 위치 | 규칙 |
|---|---|
| `schemas/auth.py:12, 58` (회원가입·로그인) | `^010[0-9]{8}$` — **010만** |
| `services/pre_registration.py:30` (사전 신청) | `^01[016789]\d{7,8}$` — 011/016/017/018/019도 허용 |
| `services/content_filter.py:34` (금칙 필터) | 01X + 하이픈·점·공백 허용 — 필터 목적이라 넓은 게 맞음 ✅ |

- **결과:** 011 번호로 사전 신청은 되는데 앱 가입은 안 된다. 창립 회원 혜택 대상 확인도 실패한다.
- **실제 영향은 작다:** 01X 번호는 2021년 6월에 서비스가 종료돼 지금은 대부분 010으로 바뀌었다. 다만 중장년층이 대상이라 0은 아닐 수 있다.
- **제안:** 사전 신청도 `^010\d{8}$`로 좁힌다. **앱에서 못 쓰는 번호를 미리 받지 않는 게** 사용자에게도 정직하다. (반대로 앱 가입을 01X까지 넓히는 건 SMS 인증·심사 계정 로직까지 건드려서 비추천.)
- 사전 신청은 이미 받은 데이터가 있으므로, 바꾸기 전에 `SELECT count(*) FROM pre_registrations WHERE phone NOT LIKE '010%'`로 해당 신청자가 있는지 먼저 확인.

### 3-4. [하] 최소 나이 50이 2곳
- `schemas/auth.py:38` `Field(ge=50, ...)`, `services/pre_registration.py:20` `MIN_AGE = 50` (+ 88행 에러 문구 "만 50세").
- 이미 주석으로 서로를 가리키고 있다. 3-2를 할 때 같이 `MIN_AGE`를 schemas에서도 가져다 쓰게 하면 된다. 단독으로는 급하지 않음.

### 3-5. [하] `scripts/seed.py:67` 더미 회원 번호 형식
- `phone = f"010-9000-{index:04d}"` — 하이픈 포함. 실제 가입은 숫자만 저장(`^010[0-9]{8}$`).
- 개발용 스크립트라 운영 영향은 없다. 다만 **프로덕션 DB에서 실행하면** 로그인 불가능한 더미 회원 20명이 매칭 목록에 뜬다. 스크립트 맨 위에 "프로덕션 실행 금지" 가드를 두는 것을 권장.

---

## 4. 하드코딩이지만 그대로 두는 게 맞는 것

| 위치 | 이유 |
|---|---|
| `services/payment.py:20-30` 포인트 패키지·구독 가격 | 결제가 닫혀 있다(`PAYMENTS_ENABLED=False`). Play 결제를 붙이면 **상품·가격은 Play Console에서 관리**하게 되므로 그때 이 표 자체가 바뀐다. 지금 옮기는 건 헛수고 |
| `services/auth.py:17-23` 인증 시도 5회·1분·일 10회·15분 | 보안 정책. 환경변수로 빼면 운영 중 실수로 풀릴 수 있다 |
| `services/pre_registration.py:36-38` 도배 방지 수치 | 위와 같음 |
| `services/pre_registration.py:22-28` 경기도 시·군 목록 | 행정구역은 거의 안 바뀜. 코드 리뷰로 관리하는 게 맞음 |
| `services/content_filter.py` 금칙어·정규식 | 마찬가지. 다만 단어가 많이 늘면 별도 파일(예: `app/data/banned_words.txt`)로 빼는 걸 고려 |
| `routers/users.py:29-30` 사진 6장·10MB | 프론트 UI와 맞춘 제품 규칙 |
| 외부 API 타임아웃 2~30초 (`chat.py:96`, `users.py:160,229,239`, `fcm.py:48`, `payment.py:42,58`) | 호출마다 성격이 달라 개별 값이 맞다(채팅 스캠 탐지 2초 = 메시지 전송을 막지 않으려고 짧게) |
| `main.py:22` Sentry `traces_sample_rate=0.1` | 무료 한도 관리용. 바꿀 일이 생기면 그때 설정으로 |
| `main.py:28` `title="Sinabro API"` | 서비스 이름. 문제 없음 |

---

## 5. 하드코딩은 아니지만 출시 전에 확인할 설정

- **CORS (`main.py:31-37`, `config.py`)**: `CORS_ALLOWED_ORIGINS`가 비어 있으면 `*` + `allow_credentials=True`. 인증이 쿠키가 아니라 Bearer 토큰이라 당장 위험은 낮지만, **Railway 프로덕션에 org 사이트 도메인(사전 신청 페이지)만 넣어 두었는지** 확인 필요. 앱(React Native)은 CORS 영향을 받지 않는다.
- **`REVIEW_TEST_PHONE/CODE`**: Play 심사 전에 프로덕션에 둘 다 설정됐는지(기존 계획서 5장과 동일).

---

## 6. 정리 — 제안 작업 순서

| 순서 | 작업 | 위험 | 코드 동작 변화 |
|---|---|---|---|
| 1 | `.env.example`에 빠진 10개 추가 (3-1) | 없음 | 없음 |
| 2 | 신뢰점수 상수 모으기 (3-2) + MIN_AGE 공유 (3-4) | 낮음 | 없음 |
| 3 | 사전 신청 번호 규칙 010으로 통일 (3-3) | 낮음 — 기존 데이터 먼저 조회 | 011 등 신청이 거절됨 |
| 4 | seed.py 프로덕션 가드 (3-5) | 없음 | 없음 |

1번은 출시 전에 하는 걸 추천, 2~4번은 출시 후 정리해도 된다.
