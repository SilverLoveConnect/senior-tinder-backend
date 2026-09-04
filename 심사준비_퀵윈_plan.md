# 심사 퀵윈 구현 계획 (오늘 손댈 것)

- 작성일: 2026-09-03
- 선행 문서: `심사준비_점검_research.md`
- 브랜치: `claude/review-progress-check-159zhd`
- 원칙: **코드 리스크가 0에 가까운 것부터.** 문서 2건 → 설정 1건 순서. 판단이 필요한 건(시드 사진)은 오늘 손대지 않고 이유를 남긴다.

| 항목 | 종류 | 파일 | 코드 리스크 | 상태 |
|---|---|---|---|---|
| A. 계정 삭제 안내 페이지 | 신규 문서 | `docs/legal/account-deletion.html` | 없음 (기존 코드 미접촉) | ✅ 적용 완료 (2026-09-03) |
| B. 약관 무관용·24시간 문구 | 문서 수정 | `docs/legal/terms.html` | 없음 | ✅ 적용 완료 (2026-09-03) — 제7조 4·5항 추가 |
| C. `INTERNAL_TOKEN` 미설정 통과 제거 | 설정/보안 | `app/core/config.py`, `app/core/dependencies.py`, `.env.example` | 낮음 (단, **팀원 로컬 기동에 영향**) | ⏸ 보류 — Railway 현재 설정 + AI 서버 헤더 사용 여부 확인 후 진행 |
| D. 시드 더미 사진 | 코드+정책 | `scripts/seed.py` | 중 | **오늘 보류** (§4 사유) |

---

## A. 계정 삭제 안내 페이지 (`docs/legal/account-deletion.html`)

### 왜 필요한가
Google Play는 사용자 계정을 만드는 앱에 대해 **"앱을 설치하지 않고도 계정·데이터 삭제를 요청할 수 있는 웹 URL"** 을 Play Console 데이터 안전 섹션에 입력하도록 요구한다. 우리는 앱 내 탈퇴(`DELETE /users/me`)만 있고 이 URL이 없다. 실제 반려 사유 상위권이고, 코드를 한 줄도 안 건드리고 막을 수 있다.

### 어떻게
`docs/`는 이미 GitHub Pages로 서빙되고 있으므로(`docs/.nojekyll` + 기존 privacy/terms 게시) **HTML 파일 한 장을 같은 폴더에 추가하면 URL이 생긴다.** 새 인프라·새 라우트·새 배포 없음.

- 파일 경로: `docs/legal/account-deletion.html`
- 예상 URL: `https://silverloveconnect.github.io/senior-tinder-backend/legal/account-deletion.html`
  - ⚠️ 이 세션에서는 사내 네트워크 정책으로 외부 접속이 막혀 **URL 실동작을 확인하지 못했다.** 푸시 후 브라우저로 직접 열어보고, 안 열리면 GitHub → Settings → Pages → Source가 `main` / `/docs` 인지 확인할 것.
- 문서 내용은 **전부 기존 문서에서 그대로 가져온다**(새로 지어낸 사실 없음): 회사 정보·연락처는 `privacy.html`, 보관 기간은 `privacy.html` 제5항, 탈퇴 경로는 `terms.html` 제11조.
- 스타일은 privacy/terms와 동일한 인라인 CSS를 복사해 세 문서가 같은 톤으로 보이게 한다.

### 전체 내용 (핵심 부분)

```html
<h1>계정 및 데이터 삭제 안내</h1>

<h2>방법 1. 앱에서 직접 삭제 (권장)</h2>
<ol>
  <li>시나브로 앱 실행 후 로그인</li>
  <li>하단 <strong>내 정보</strong> 탭 이동</li>
  <li><strong>회원 탈퇴</strong> 선택 → 안내 확인 후 탈퇴 완료</li>
</ol>

<h2>방법 2. 이메일로 삭제 요청 (앱을 삭제하셨거나 로그인이 어려운 경우)</h2>
<p><a href="mailto:e53788989@gmail.com">e53788989@gmail.com</a> 으로 아래 내용을 보내주세요.</p>
<ul>
  <li>제목: <code>[시나브로] 계정 삭제 요청</code></li>
  <li>가입에 사용한 휴대전화번호</li>
</ul>
<p>본인 확인 후 <strong>영업일 기준 7일 이내</strong> 처리하고 결과를 회신합니다.</p>

<h2>삭제되는 데이터</h2>
<ul>
  <li>이름·닉네임 등 프로필 정보 (즉시 익명화)</li>
  <li>휴대전화번호 (즉시 익명 처리 — 동일 번호로 재가입 가능)</li>
  <li>등록한 프로필 사진 전부</li>
  <li>푸시 알림 토큰</li>
  <li>매칭·좋아요 등 서비스 이용 기록</li>
</ul>

<h2>법령에 따라 일정 기간 보관되는 데이터</h2>
<table>
  <tr><th>항목</th><th>보관 기간</th><th>근거</th></tr>
  <tr><td>계약·청약철회 등 기록</td><td>5년</td><td>전자상거래법</td></tr>
  <tr><td>대금결제·재화 공급 기록</td><td>5년</td><td>전자상거래법</td></tr>
  <tr><td>소비자 불만·분쟁처리 기록</td><td>3년</td><td>전자상거래법</td></tr>
  <tr><td>접속(로그) 기록</td><td>3개월</td><td>통신비밀보호법</td></tr>
</table>
<p>또한 부정 이용 방지 및 신고 처리를 위해 탈퇴 후 <strong>30일간</strong> 일부 식별정보를 분리 보관한 뒤 파기할 수 있습니다.</p>
```

### 다른 방법과 비교

| 방법 | 채택? | 이유 |
|---|---|---|
| **GitHub Pages에 HTML 추가** | ✅ 채택 | 이미 privacy/terms가 같은 방식으로 서빙 중. 새 개념 0, 배포 0, 비용 0 |
| FastAPI에 `GET /legal/account-deletion` 라우트 추가 | ❌ | API 서버에 HTML 렌더링 책임을 새로 얹는 것 — 기존 레이어 구조(라우터=JSON API)를 깨뜨린다. 서버가 죽으면 법적 고지 페이지도 같이 죽는다 |
| Notion·구글 폼 등 외부 링크 | ❌ | 도메인이 회사 소유가 아니고 나중에 링크가 끊긴다. Play 심사에서 "임시 페이지"로 보일 위험 |

### 장단점
- 장점: 코드 미접촉이라 회귀 위험 0. Play 데이터 안전 섹션 입력란을 오늘 바로 채울 수 있다.
- 단점: **"영업일 7일 이내 처리"는 사람이 지켜야 하는 약속이다.** 이메일 요청이 오면 실제로 `POST /internal/users/{id}/ban` 이 아니라 탈퇴 처리를 해줘야 하는데, 지금 그 수단이 DB 직접 조작뿐이다 → 별도 항목(리서치 B-1)과 함께 풀어야 함.

### 팀 영향
- **팀원이 고칠 것: 없음.** 백엔드 코드 변경 0.
- **지수님이 하실 것 2가지**: ① 푸시 후 URL이 열리는지 확인 ② Play Console → 앱 콘텐츠 → 데이터 안전 → "계정 삭제 요청 URL"에 이 주소 입력.
- 프론트 담당자에게 공유하면 좋은 것: 앱 내 '내 정보' 화면에서 이 페이지로 링크를 걸어두면 심사관이 찾기 쉬워진다(필수는 아님).

---

## B. 약관에 무관용·24시간 조치 문구 추가 (`docs/legal/terms.html`)

### 왜 필요한가
Apple Guideline 1.2(사용자 생성 콘텐츠)는 UGC 앱에 다음을 **명시적으로** 요구한다.
> "a method for filtering objectionable material, a mechanism to report offensive content **and timely responses to concerns**, the ability to block abusive users, **and published contact information**"

그리고 심사관은 EULA에 **"objectionable content에 대한 무관용(zero tolerance)"** 문구가 있는지를 키워드로 찾는다. 현재 제7조에는 금지행위와 제재는 있지만 이 두 표현이 없다.

### 어떻게
제7조에 항목 2개를 **추가만** 한다. 기존 3개 항의 문장은 손대지 않는다(법무 검토를 이미 거칠 문서이므로 기존 문장 변경은 최소화).

```html
<h2>제7조 (게시물의 관리, 신고·차단 및 제재)</h2>
<ol>
  <li>회사는 회원이 등록한 콘텐츠가 제6조를 위반한다고 판단될 경우 사전 통지 없이 삭제·비공개 처리할 수 있습니다.</li>
  <li>회원은 부적절한 상대를 신고 및 차단할 수 있으며, 회사는 신고 누적 등을 근거로 신뢰점수 하향, 이용 정지, 계정 영구 정지 등의 조치를 취할 수 있습니다.</li>
  <li>회사는 AI를 통해 부적절한 사진·사기성 메시지를 자동 탐지하여 경고·차단할 수 있습니다.</li>
+ <li><strong>회사는 음란물·폭력적 표현·혐오 표현·불법 촬영물 등 부적절한 콘텐츠와, 다른 회원을 괴롭히거나 기만하는 행위에 대해 무관용 원칙(zero tolerance)을 적용합니다.</strong> 해당 콘텐츠는 즉시 삭제되며, 게시한 회원은 사전 통지 없이 서비스에서 배제될 수 있습니다.</li>
+ <li><strong>회사는 접수된 신고를 24시간 이내에 검토하고, 위반이 확인된 콘텐츠는 삭제하며 해당 회원의 이용을 정지합니다.</strong> 회원은 조치 결과에 대해 제9조의 문의처를 통해 이의를 제기할 수 있습니다.</li>
</ol>
```

### 다른 방법과 비교
- **별도 "커뮤니티 가이드라인" 문서 신설**: 나중에 필요하지만 오늘은 아님. 문서가 하나 늘면 앱 내 링크·심사 제출 URL·법무 검토 대상이 다 같이 늘어난다. 약관 2줄로 요건을 만족할 수 있는데 문서를 늘릴 이유가 없다.
- **앱 내 문구로만 처리**: ❌ 심사관이 보는 건 EULA다. 앱 화면 문구는 근거로 안 잡힌다.

### 장단점
- 장점: 30분. Apple 1.2의 서면 요건이 채워진다.
- **단점(중요): 이건 회사가 지겠다고 선언하는 의무다.** "24시간 이내 검토"라고 써놓고 신고 목록을 볼 API조차 없는 게 지금 상태다. 문구를 넣는 순간 리서치 B-1(신고 처리 창구)은 **선택이 아니라 필수**가 된다.
  - 그래도 넣는 게 맞다고 보는 이유: 문구가 없으면 심사에서 바로 걸리고, 있으면 최소한 심사는 통과한 뒤 창구를 만들 수 있다. 다만 **B-1을 이번 주 안에 끝낸다는 전제**로만 유효하다.
  - 24시간이 부담스러우면 "영업일 1일 이내"로 낮출 수 있으나, Apple이 찾는 표현은 24시간이라 그대로 가는 걸 권한다.

### 팀 영향
- 팀원이 고칠 코드: 없음.
- 대신 **운영 약속이 생긴다** — 신고가 들어오면 24시간 내에 누군가 본다는 뜻. 담당자와 확인 주기를 정해두는 게 좋다.
- ⚠️ 두 문서 모두 상단에 "법무 검토 필요 (초안)" 배너가 그대로 있다. 정식 출시 전에는 이 배너를 떼는 게 맞고, 떼려면 실제 법무 검토가 선행돼야 한다. 이번 변경으로 그 필요가 커졌다.

---

## C. `INTERNAL_TOKEN` 미설정 시 인증 통과 제거

### 지금 상태
```python
# app/core/dependencies.py:76-86
def verify_internal_token(x_internal_token: str = Header(default="")):
    """AI 서버 등 내부 서비스 콜백 인증"""
    if not settings.INTERNAL_TOKEN:
        # 환경변수 미설정 시 개발 환경으로 간주, 통과   ← 여기
        return
    if x_internal_token != settings.INTERNAL_TOKEN:
        raise HTTPException(401, "내부 서비스 인증 실패")
```

프로덕션에서 `INTERNAL_TOKEN` 환경변수를 한 번 빠뜨리면 아래가 **인터넷에 무인증으로 열린다.**

| 엔드포인트 | 열렸을 때 피해 |
|---|---|
| `GET /internal/photos/pending` | 검수 대기 사진의 **S3 URL + user_id 전량 유출** |
| `POST /internal/photos/{id}/review` | 부적절 사진 임의 승인 |
| `POST /internal/users/{id}/ban` | **임의 계정 정지** — 서비스 전체 사용자 차단 가능 |
| `POST /internal/ai/photo-result` | 신뢰점수 임의 조작 |

"설정하면 안전한데 안 하면 조용히 뚫린다"가 가장 나쁜 형태다. 배포 사고 한 번이면 개인정보 유출이 된다.

### 선택지 (여기서 **결정이 필요**합니다)

**옵션 1 — `DATABASE_URL`·`SECRET_KEY`와 똑같이 필수화 (권장)**
```python
# app/core/config.py
-    INTERNAL_TOKEN: str = ""
+    # 내부 서비스(AI 서버 등) 콜백 인증 토큰 (필수 — 비어있으면 기동 실패)
+    # 빈 값 통과를 허용하면 환경변수 누락 한 번으로 /internal/* 전체가
+    # 무인증 공개된다(계정 정지·사진 승인·사진 URL 유출).
+    INTERNAL_TOKEN: str = Field(min_length=1)
```
```python
# app/core/dependencies.py
 def verify_internal_token(x_internal_token: str = Header(default="")):
     """AI 서버 등 내부 서비스 콜백 인증"""
-    if not settings.INTERNAL_TOKEN:
-        # 환경변수 미설정 시 개발 환경으로 간주, 통과
-        return
     if x_internal_token != settings.INTERNAL_TOKEN:
         raise HTTPException(401, "내부 서비스 인증 실패")
```
```diff
# .env.example
-INTERNAL_TOKEN=
+# 내부 서비스(AI 서버) 콜백 인증 토큰 — 필수. 로컬은 아무 문자열이나 넣으면 됨
+INTERNAL_TOKEN=local-dev-internal-token
```
- 장점: **이 저장소에 이미 있는 관례를 그대로 따른다.** `DATABASE_URL`·`SECRET_KEY`가 정확히 이 방식(`Field(min_length=1)`)이라 팀원이 새로 배울 개념이 0이다. 빠뜨리면 배포가 아예 안 뜨므로 "조용히 뚫리는" 경우가 사라진다.
- 단점: **팀원이 `git pull` 후 서버가 안 뜬다.** `.env`에 `INTERNAL_TOKEN`을 추가해야 함. (에러 메시지는 pydantic이 필드명을 그대로 찍어주므로 원인은 바로 보인다.)

**옵션 2 — `ENV`/`DEBUG` 플래그를 새로 만들어 로컬에서만 통과**
- 장점: 팀원 로컬 흐름이 안 바뀐다.
- 단점: **이 프로젝트에 없는 새 설정 개념을 도입**하게 된다. 앞으로 "이건 DEBUG 때만?" 판단이 계속 붙고, 프로덕션에 `DEBUG=true`가 실수로 들어가면 원래 문제로 되돌아간다. 지금 막으려는 사고를 다른 이름으로 남겨두는 셈.

**옵션 3 — 기동은 그대로 두고, 토큰이 비어 있으면 401로 거부**
- 장점: 서버는 뜬다. 배포 리스크 최소.
- 단점: 프로덕션 환경변수를 빠뜨렸을 때 **AI 콜백이 전부 401로 죽는데 아무도 모른다** → 사진이 영구 미승인(리서치 B-3)으로 이어진다. 실패가 조용하다는 점은 그대로.

**권장: 옵션 1.** 이유는 하나 — 이 저장소가 이미 그 방식을 쓰고 있어서, 내가 팀 코드에 맞추는 쪽이지 팀이 내 코드에 맞추는 쪽이 아니다.

### 팀 영향 (옵션 1 기준)
- **팀원이 해야 할 일**: 각자 로컬 `.env`에 `INTERNAL_TOKEN=아무값` 한 줄 추가. (`.env.example`에 값까지 채워둘 예정이라 복붙이면 끝.)
- **배포 담당(지수님)이 해야 할 일**: Railway 환경변수에 `INTERNAL_TOKEN` 추가 — **이 변경을 배포하기 전에 먼저.** 순서를 바꾸면 배포가 기동 실패한다.
- **AI 서버 담당자에게 공유**: 콜백 호출 시 `X-Internal-Token` 헤더에 같은 값을 넣어야 한다. 지금 프로덕션에 토큰이 이미 설정돼 있다면 동작은 그대로고, 안 되어 있었다면 **이 변경으로 AI 콜백이 401로 막힌다.** → 배포 전에 현재 Railway에 `INTERNAL_TOKEN`이 있는지, AI 서버가 헤더를 보내고 있는지 먼저 확인 필요.

### 검증 방법
```bash
# 1) 토큰 없이 기동 → 즉시 실패해야 정상
INTERNAL_TOKEN= uv run uvicorn app.main:app   # ValidationError 확인

# 2) 토큰 넣고 기동 후, 헤더 없이 호출 → 401
curl -i localhost:8000/internal/photos/pending
# 3) 올바른 헤더로 호출 → 200
curl -i -H "X-Internal-Token: local-dev-internal-token" localhost:8000/internal/photos/pending
```

---

## D. 시드 더미 사진 — 오늘 보류하는 이유

`scripts/seed.py`는 `UserPhoto`를 하나도 만들지 않아 매칭 피드가 사진 없는 카드 20장이 된다(리서치 B-3). 심사 관점에선 가장 급하지만, **"바로 만들 수 있는 것"이 아니다.** 두 가지 결정이 선행돼야 한다.

1. **어떤 이미지를 쓸 것인가** — 실존 인물 사진을 무단으로 쓰면 초상권 문제고, 무료 스톡도 "인물 사진을 데이팅 프로필로 사용"은 라이선스가 금지하는 경우가 많다. AI 생성 이미지 또는 명시적으로 허용된 소스가 필요하고, S3에 올려야 URL이 생긴다.
2. **이 더미를 프로덕션 DB에 넣을 것인가** — 심사관에게만 보이게 할 방법이 없다. 프로덕션에 넣으면 **실제 가입자도 이 가짜 프로필을 보고 좋아요를 보낸다.** 매칭이 안 되니 "아무도 답이 없는 앱"이 되고, 표시 없이 운영하면 기만행위 소지도 있다.

→ 다음 단계에서 별도 `plan.md`로 다룰 것. 후보 방향: 스테이징 DB + 심사관 전용 계정, 또는 시드 프로필에 "체험용 계정" 배지 표시, 또는 출시 직후 시드 삭제 스크립트 동반.

---

## 실행 순서 및 롤백

1. A, B 적용 → 커밋 (문서만, 코드 무영향)
2. **Railway에 `INTERNAL_TOKEN` 설정 확인** → 그 다음 C 적용 → 커밋
3. 푸시 후 Pages URL 육안 확인
4. 롤백: 전부 독립 커밋이라 `git revert <sha>` 하나로 각각 되돌아간다. A·B는 되돌려도 코드 영향 0.
