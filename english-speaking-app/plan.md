# plan.md — 영어회화 앱 (청화식 · 개인용) 1단계 상세 계획

- 작성일: 2026-10-21
- 근거: `research.md` (2026-10-21) + 사용자 답변
- 상태: **계획 작성 완료 → 사용자 승인 대기** (승인 전에는 코드 파일을 만들지 않는다)

### 사용자 결정 반영표

| 질문 | 사용자 답 | 이 계획에서 바뀐 것 |
|---|---|---|
| Q1 마이크 인식 | **Azure 사용** | STT는 Azure Speech SDK 하나만 쓴다. 내장 `webkitSpeechRecognition`는 **코드에 넣지 않는다**(설정값으로도 남기지 않음 → 죽은 코드 방지). |
| Q2 학습 시간 | **10 / 20 / … 학습자가 선택** | "하루 표현 5개 고정"을 **"학습 시간 → 그날 표현 개수 N과 연습 강도 계산"** 으로 바꾼다(§1-3, `studyBudget.ts`). 퀴즈는 `3 × N`문항. 콘텐츠 파일 단위를 `day-001`에서 `pack-001`(표현 5개 묶음)로 바꾼다(§3-1). |
| Q3 발음 평가 | **같은 요청 안에서 반환** | 모든 말하기 인식 요청에 발음 평가 설정을 붙인다. "발음 채점" 버튼은 **이미 받은 점수를 보여주기만** 한다(추가 Azure 호출 0). |
| Q4~Q8 | (답 없음) | research.md 13장 **추천안을 기본값으로 적용**. 아래 표에 표시했고, 모두 설정값이라 나중에 바꾸기 쉽다. |

| 미답변 항목 | 적용한 기본값 | 바꾸는 곳 |
|---|---|---|
| Q4 저녁에 아침 학습을 안 했을 때 | "오늘 아침 학습을 아직 안 했어요" 리마인더 발송 (설정에서 끌 수 있음) | `settings.evening_reminder_if_no_morning` |
| Q5 퀴즈 중복 회피 | 그 표현에서 **이미 나온 쌍 전부** 제외, 다 나왔으면 가장 오래전 것 | `quizSelection.ts`의 `pickPair()` |
| Q6 콘텐츠 생성 범위 | 레벨 테스트 후 **현재 레벨 + 다음 레벨**만 30팩씩 | 콘텐츠 생성 요청 시 지정 |
| Q7 "나" 음성 | `en-US-AndrewNeural`(남). 상대방 `en-US-AvaNeural`(여) | `src/config/voices.ts` (바꾸면 "나" 문장만 다시 생성) |
| Q8 승급 보완 규칙 | 보완 규칙 포함 (§4-5) | `src/config/defaults.ts`의 `promotion` |

---

## 0. 먼저 정할 것: 프로젝트를 어디에 만들지

지금 작업 중인 저장소는 `senior-tinder-backend`(시니어 매칭 앱 백엔드, Python/FastAPI)다. research.md와 plan.md는 임시로 그 안의 `english-speaking-app/` 폴더에 두었다.

| 방법 | 장점 | 단점 |
|---|---|---|
| **A. 새 GitHub 저장소** (예: `english-speaking-app`) **← 추천** | Vercel 연결이 깔끔함(저장소 1개 = Vercel 프로젝트 1개). 백엔드 저장소의 CI(`.github/`)·Python 설정과 섞이지 않음 | 저장소 생성 권한이 필요함(내가 만들 수 있는지 시도해 보고, 안 되면 사용자가 만들어 줘야 함) |
| B. 이 저장소의 하위 폴더 | 지금 바로 가능 | Vercel "Root Directory" 설정 필요, 백엔드 PR/CI에 영어앱 변경이 섞임, 팀원 저장소라면 팀원에게 혼란 |

→ **구현 0단계에서 A로 진행**하고, research.md / plan.md도 새 저장소로 옮긴다. (승인 시 함께 확인 부탁)

---

## 1. 접근 방식

### 1-1. 전체 구조

```
┌──────────────── iPhone (홈 화면 웹앱, standalone) ─────────────────┐
│  React SPA (Vite)                                                  │
│   화면(screens) → 훅(hooks) → 서비스(services) → 저장소(repositories) │
│                                 │            │                     │
│                     순수 도메인 함수(domain)   │ supabase-js / IndexedDB │
│  Service Worker (push 수신 · 음성 mp3 캐시)                         │
└────────┬───────────────────┬──────────────────────┬────────────────┘
         │ Azure Speech SDK  │ /api/speech-token     │ Supabase (DB/Auth/Storage)
         ▼ (WebSocket)       ▼                       ▼
   Azure AI Speech F0   Vercel Functions ◀── pg_net ── pg_cron (매분)
   (STT+발음평가)        ├ speech-token    (Supabase 안)
                        ├ push/dispatch ──▶ Apple Web Push (web.push.apple.com)
                        └ keepalive ◀── Vercel Cron (하루 1회)
```

| 구성 | 선택 | 이유 (research.md 근거) |
|---|---|---|
| 프런트 | **Vite + React + TypeScript SPA** | 서버 렌더링이 필요 없는 1인 앱. 화면 전환 시 페이지 새로고침이 없어야 마이크 권한 재요청을 줄인다(research 2-2). |
| 라우팅 | **react-router `BrowserRouter`(history API)**, hash 라우팅 금지 | WebKit 버그 215884: standalone에서 hash가 바뀌면 권한을 다시 물음. |
| 서버 | **Vercel Functions(`/api/*`, Node)** 3개만 | 키를 숨겨야 하는 일(토큰 발급, 푸시 발송)만 서버에서. 나머지 읽기/쓰기는 supabase-js + RLS로 직접. → **같은 일을 하는 API 엔드포인트를 만들지 않는다.** |
| DB/Auth/파일 | **Supabase 무료** | RLS로 "나만" 접근, pg_cron으로 정시 실행, Storage 1GB에 음성 파일. |
| STT·발음 평가 | **Azure Speech SDK (브라우저) — 사용자 확정** | 홈 화면 웹앱에서 내장 STT 미지원(research 2-1). |
| TTS | **Azure REST, 로컬 스크립트로 1회 생성** | 앱 실행 중 TTS 호출 0. 해시 캐시. |
| 정시 알림 | **pg_cron(매분) → pg_net → Vercel `push/dispatch`** | research 4-2. Vercel Cron은 하루 1회·±59분이라 부적합. |
| 일시정지 방지 | **Vercel Cron 하루 1회 → `/api/keepalive`** | research 4-3. 이 용도엔 Vercel Cron의 부정확함이 문제 안 됨. |

### 1-2. 계층 규칙 (가장 비싼 실패 ① 방지)

```
screens/  ──▶ hooks/ ──▶ services/ ──▶ repositories/ ──▶ supabase-js / IndexedDB / fetch
                 │            │
                 └────────────┴──▶ domain/ (순수 함수, 입출력·시간·랜덤 없음 → 단위 테스트 대상)
api/ (Vercel 함수) ──▶ services/ ──▶ repositories/   ← 서버도 같은 계층을 쓴다
```

| 계층 | 할 수 있는 것 | 하면 안 되는 것 |
|---|---|---|
| `screens/`, `components/` | 화면 그리기, 훅 호출 | `supabase`, `fetch`, Azure SDK 직접 import |
| `hooks/` | 화면 상태, 서비스 호출 조합 | DB 쿼리 직접 작성 |
| `services/` | 업무 흐름(녹음→인식→채점→저장), 도메인 함수 호출 | UI 코드 |
| `repositories/` | 테이블 단위 읽기/쓰기. **`SupabaseClient`를 인자로 받는다** (브라우저=로그인 세션, 서버=service role → 같은 코드 재사용) | 업무 규칙 판단 |
| `domain/` | 학습일 계산, 퀴즈 출제, 정규화, diff, 레벨 판정, 승급 규칙, 학습량 계산 | 네트워크, `Date.now()`, `Math.random()` (시각과 난수는 인자로 받는다) |

- 강제 방법: ESLint `no-restricted-imports` 규칙으로 `screens/**`에서 `@supabase/*`, `microsoft-cognitiveservices-speech-sdk`, `src/repositories/**` import를 에러로 만든다(§2 `eslint.config.js`).
- 새 함수를 만들기 전에 `src/domain/index.ts`, `src/services/index.ts`의 export 목록을 먼저 확인한다(중복 생성 방지 ②).

### 1-3. 학습 시간 → 그날 학습량 (Q2 반영, 새 설계)

사용자가 설정에서 **하루 학습 시간**을 고른다: `10 / 15 / 20 / 30 / 40분` (기본 20분, 목록은 설정값).
그날 아침에 다룰 **표현 개수 N**과 **연습 강도**를 순수 함수 `planStudyDay()`가 계산한다.

research.md 10장의 단위 시간을 그대로 쓴다:

| 상수 (초) | 초급 | 중급 | 고급 |
|---|---|---|---|
| 표현 1개 아침(가벼운 흐름: build-up은 실패 시만, 대화 B역만) | 118 | 150 | 190 |
| 표현 1개가 만드는 퀴즈 부담 (1·3·7학습일 후 3번 출제 × 문항당) | 3×19=57 | 3×23=69 | 3×27=81 |
| **표현 1개 총비용** | **175** | **219** | **271** |
| 역할 교대 대화 1개 | 30 | 45 | 60 |
| build-up 항상 하기(표현당 추가) | 25 | 30 | 35 |
| 시작/마무리 고정 | 90 | 90 | 90 |

계산 순서:
1. `예산 = 분 × 60 − 고정 90초 − 역할 교대 1개`
2. `N = clamp(floor(예산 / 표현 총비용), 1, 5)` (하루 최대 5개는 원래 요구사항 유지, 설정값)
3. 남은 시간이 있으면 **연습 강도를 올린다**: ① build-up 항상 → ② 역할 교대 대화 추가(최대 N개)

아래 표는 `planStudyDay()` 스케치(§4-4)를 실제로 돌린 결과다 (N / build-up / 역할 교대 대화 수):

| 선택 | 초급 | 중급 | 고급 |
|---|---|---|---|
| 10분 | N=2 · 항상 · 교대 2 | N=2 · 실패 시 · 교대 1 | N=1 · 항상 · 교대 1 |
| 15분 | N=4 · 실패 시 · 교대 3 | N=3 · 항상 · 교대 1 | N=2 · 항상 · 교대 2 |
| 20분 | **N=5** · 항상 · 교대 3 | N=4 · 항상 · 교대 2 | N=3 · 항상 · 교대 3 |
| 30분 | N=5 · 항상 · 교대 5 | N=5 · 항상 · 교대 5 | N=5 · 항상 · 교대 3 |
| 40분 | N=5 · 항상 · 교대 5 | N=5 · 항상 · 교대 5 | N=5 · 항상 · 교대 5 |

- 초급 15분처럼 "N은 늘었는데 build-up은 실패 시"가 되는 칸이 있다. 표현 개수를 연습 강도보다 우선하는 규칙이라서다. 반대(강도 우선)를 원하면 §4-4의 계산 순서만 바꾸면 된다.

- 저녁 퀴즈 = 1·3·7학습일 전의 표현마다 1쌍 → 최대 `3 × N`문항(그날들의 N이 다르면 합이 달라질 수 있어 **상한 = 3 × 오늘 N**, 섹션별 순환 배분).
- 학습 시간을 바꾸면 **다음 학습일부터** 적용(오늘 진행 중인 세션은 그대로).
- 실제 소요 시간은 세션 시작/끝 시각을 기록해 설정 화면에 "최근 7일 평균 실제 소요"로 보여준다 → 상수 보정 근거.

**버린 대안**

| 대안 | 버린 이유 |
|---|---|
| N은 5 고정, 시간에 따라 연습 단계만 빼기 | 10분에 5개를 넣으면 대화·파생을 거의 다 빼야 함 → 청화식 핵심(대화 암기)이 사라짐 |
| 사용자가 N을 직접 고름 | 사용자는 "몇 분"을 생각하지 "몇 개"를 생각하지 않음. 원하면 확장 아이디어로 "직접 지정" 추가 가능 |

---

## 2. 폴더 구조와 파일 경로 전체

> ★ = 이번 계획에서 새로 만드는 파일 전부 (기존 파일 없음, 새 저장소 기준)

```
english-speaking-app/
├─ package.json                         ★ 스크립트: dev, build, test, lint, typecheck, content:*, tts:*
├─ tsconfig.json                        ★
├─ vite.config.ts                       ★
├─ vitest.config.ts                     ★
├─ eslint.config.js                     ★ 계층 import 규칙 포함
├─ vercel.json                          ★ SPA rewrite + keepalive cron
├─ index.html                           ★
├─ .env.example                         ★ 환경변수 목록(값 없음)
├─ docs/
│  ├─ research.md                       (이동)
│  ├─ plan.md                           (이동)
│  └─ device-spike-results.md           ★ 실기기 테스트 결과 기록
├─ public/
│  ├─ manifest.webmanifest              ★ display: standalone
│  ├─ sw.js                             ★ push / notificationclick / 음성 캐시
│  ├─ icons/icon-192.png, icon-512.png, apple-touch-icon.png ★
│  ├─ worklets/pcm-capture.js           ★ AudioWorklet (마이크 PCM 수집)
│  └─ content/                          ★ 콘텐츠 JSON(정적 파일로 배포)
│     ├─ beginner/pack-001.json …
│     ├─ intermediate/pack-001.json …
│     ├─ advanced/pack-001.json …
│     ├─ level-test/set-a.json, set-b.json
│     └─ index.json                     ★ 레벨별 팩 개수 (스크립트가 생성)
├─ api/                                 ★ Vercel Functions (얇게: 인증 확인 → 서비스 호출)
│  ├─ speech-token.ts
│  ├─ push/dispatch.ts
│  └─ keepalive.ts
├─ src/
│  ├─ main.tsx, App.tsx, routes.tsx     ★
│  ├─ config/
│  │  ├─ defaults.ts                    ★ 모든 [기본값] 한곳에
│  │  ├─ voices.ts                      ★ 역할별 음성 이름
│  │  └─ env.ts                         ★ 클라이언트에 공개해도 되는 값만 (VITE_*)
│  ├─ domain/                           ★ 순수 함수 (단위 테스트 대상)
│  │  ├─ types.ts                       Level, LearningDay, QuizItem …
│  │  ├─ learningDay.ts                 서비스 날짜·학습일·퀴즈 상태·저녁 알림 판단
│  │  ├─ studyBudget.ts                 학습 시간 → N, 연습 강도
│  │  ├─ quizSelection.ts               1·3·7학습일 출제
│  │  ├─ normalize.ts                   텍스트 정규화
│  │  ├─ wordDiff.ts                    단어 diff + 통과 판정
│  │  ├─ levelTest.ts                   2단계 분기 + 판정
│  │  ├─ promotion.ts                   자동 승급 / 하향 권유
│  │  ├─ usageBudget.ts                 Azure 사용량 단계(정상/절약/퀴즈만/정지)
│  │  ├─ rng.ts                         시드 난수(mulberry32)
│  │  ├─ index.ts                       export 목록 (중복 생성 전 확인용)
│  │  └─ __tests__/*.test.ts            ★ 도메인 함수마다 1개
│  ├─ content/
│  │  ├─ schema.ts                      ★ zod 스키마 (앱·스크립트 공용)
│  │  └─ contentIndex.ts                ★ 표현 커서 → 팩/표현 찾기, 퀴즈 후보 쌍 만들기
│  ├─ repositories/                     ★ supabase/IndexedDB 접근 (client를 인자로)
│  │  ├─ supabaseClient.ts              브라우저용 클라이언트 생성
│  │  ├─ settingsRepo.ts
│  │  ├─ morningSessionRepo.ts          (= 학습일 기록)
│  │  ├─ quizRepo.ts
│  │  ├─ attemptRepo.ts
│  │  ├─ levelTestRepo.ts
│  │  ├─ levelChangeRepo.ts
│  │  ├─ pushSubscriptionRepo.ts
│  │  ├─ pushLogRepo.ts
│  │  ├─ usageRepo.ts
│  │  ├─ contentRepo.ts                 /content/*.json fetch + 메모리 캐시
│  │  └─ outbox.ts                      IndexedDB 전송 대기열
│  ├─ services/                         ★
│  │  ├─ audio/
│  │  │  ├─ micStream.ts                getUserMedia 세션당 1회
│  │  │  ├─ pcmRecorder.ts              AudioWorklet → 16kHz Int16 + VAD
│  │  │  ├─ wav.ts                      PCM → WAV Blob
│  │  │  └─ player.ts                   단일 플레이어, 속도, A/B 비교
│  │  ├─ speech/
│  │  │  ├─ tokenClient.ts              /api/speech-token 호출 + 9분 갱신
│  │  │  └─ azureRecognizer.ts          STT + 발음 평가(같은 요청)
│  │  ├─ attemptService.ts              녹음→인식→정규화·diff→저장→사용량
│  │  ├─ morningService.ts              오늘 학습 계획·진행·완료(학습일 확정)
│  │  ├─ quizService.ts                 퀴즈 생성·진행·미응시 처리
│  │  ├─ levelTestService.ts
│  │  ├─ levelService.ts                현재 레벨 계산·승급 평가·레벨 변경 기록
│  │  ├─ pushService.ts                 구독·재구독 / (서버) 발송
│  │  ├─ usageService.ts
│  │  └─ index.ts
│  ├─ hooks/                            ★ useMorningSession, useQuiz, useLevelTest,
│  │                                       useSpeechAttempt, useAudioPlayer, useSettings,
│  │                                       usePushSubscription, useUsage, useAuth
│  ├─ screens/                          ★ (§5 화면 목록과 1:1)
│  └─ components/                       ★ WordDiffView, AbCompare, RecordButton, ScoreCard …
├─ scripts/                             ★ 로컬에서 Node로 실행 (tsx)
│  ├─ content/validate.ts               zod 스키마 + 품질 규칙 검사
│  ├─ content/check-duplicates.ts       전체 콘텐츠(+레벨 테스트) 표현 중복 검사
│  ├─ content/build-index.ts            public/content/index.json 생성
│  └─ tts/generate-audio.ts             해시 캐시 TTS 일괄 생성 → Supabase Storage
└─ supabase/
   ├─ config.toml                       ★ (supabase init)
   └─ migrations/
      ├─ 20261022000100_init_schema.sql      ★ 테이블 + RLS + GRANT
      ├─ 20261022000200_usage_rpc.sql        ★ 사용량 증가 RPC
      └─ 20261022000300_push_scheduler.sql   ★ pg_cron + pg_net + dispatch 함수
```

**라이브러리 버전** (npm 레지스트리에서 2026-10-21 확인. 원칙: 출시 2주 이상 지난 버전으로 고정, `^` 없이 정확한 버전)

| 패키지 | 버전 | 출시일 | 비고 |
|---|---|---|---|
| react / react-dom | 19.3.0 | 2026-09-09 | 19.3.1은 10-14 출시(1주) → 보류 |
| vite | 8.3.3 | 2026-10-06 | 8.3.5는 오늘 출시 → 보류 |
| @vitejs/plugin-react | 6.1.1 | 2026-08-28 | vite ^8 요구 |
| typescript | 6.0.3 | 2026-04-16 | 7.x(Go 컴파일러)는 7월 출시. 생태계 호환을 위해 6.x로 시작 |
| vitest | 5.0.3 | 2026-09-30 | vite 6.4~8 지원 |
| @supabase/supabase-js | 2.117.2 | 2026-09-25 | |
| supabase (CLI) | 2.120.0 | 2026-10-06 | 마이그레이션용 dev 의존성 |
| microsoft-cognitiveservices-speech-sdk | 1.52.0 | 2026-09-28 | 발음 평가 prosody는 1.34+ |
| web-push | 3.6.7 | 2024-01-16 | 오래됐지만 표준 구현, Node ≥16 |
| zod | 4.6.5 | 2026-09-13 | |
| idb | 8.0.3 | 2025-05-07 | 8.0.4는 10-06 출시(2주 직전) |
| react-router-dom | 7.18.4 | 2026-09-15 | |
| tsx | 4.23.15 | 2026-09-20 | 스크립트 실행 |

- `vite-plugin-pwa`는 **쓰지 않는다** (§6-3 대안 비교).
- Node: 로컬 22.x (현재 환경 22.22.0 확인).

---

## 3. 데이터 모델

### 3-1. 콘텐츠 JSON — `public/content/{level}/pack-001.json`

**프롬프트 초안 대비 변경점과 이유**

| 변경 | 이유 |
|---|---|
| 파일 단위 `day-001` → **`pack-001`**(표현 5개 묶음) | Q2로 하루 표현 수 N이 1~5로 바뀜. "day"로 부르면 하루=파일이 아니게 되어 헷갈림. 진도는 **레벨별 "소비한 표현 수"(커서)** 로 관리하고, 학습일 기록에 그날 배운 표현 id 목록을 저장한다. |
| `dialogue` 각 줄에 `id` 추가 | 퀴즈 출제·중복 회피·결과 기록을 줄 단위로 하려면 고유 id가 필요 |
| `build_up` 추가 | backward build-up 덩어리를 콘텐츠 작성 단계에서 정함(자동 분할은 품질이 낮음). 덩어리도 따로 TTS(research 11-1 주의 ②) |
| `me.focus` 선택 필드 | 통과 판정 때 "반드시 맞아야 하는 핵심 구간". 대치 연습처럼 표현이 바뀌는 문장 때문에 `expression`을 그대로 쓸 수 없음 |
| `audio` 필드 | TTS 스크립트가 채움(파일명 = 해시) |
| `topic`을 `daily / business / interview` 3값으로 | "비즈니스·면접 50%" 안에서 면접 비중도 보이게. 검사 스크립트는 `daily` vs 나머지 50:50 확인 |
| `schema_version: 1` | 아직 만든 데이터가 없으므로 확정본을 1로 시작. 이후 바꾸면 2로 올리고 `scripts/content/migrate-v1-to-v2.ts`를 만든다(③ 마이그레이션 없이 덮어쓰기 금지) |

```json
{
  "schema_version": 1,
  "level": "beginner",
  "pack": 1,
  "expressions": [
    {
      "id": "beg-p001-1",
      "expression": "I'm running a bit late",
      "meaning_ko": "나 좀 늦을 것 같아",
      "when_to_use": "약속 시간에 늦을 것 같을 때 미리 알리는 말",
      "topic": "daily",
      "source_check": ["https://...", "https://..."],
      "audio": "3f9a1c0d5e7b2a44.mp3",
      "build_up": {
        "target_line_id": "beg-p001-1-l2",
        "chunks": [
          { "en": "a bit late", "audio": "…" },
          { "en": "running a bit late", "audio": "…" },
          { "en": "Sorry, I'm running a bit late.", "audio": "…" }
        ]
      },
      "derived": [
        {
          "id": "beg-p001-1-d1", "type": "substitution",
          "cue": { "en": "Where are you? The movie starts soon.", "ko": "어디야? 영화 곧 시작해.", "audio": "…" },
          "me":  { "en": "I'm running ten minutes late.", "ko": "10분쯤 늦을 것 같아.", "focus": "running ten minutes late", "audio": "…" }
        }
      ],
      "dialogue": [
        { "id": "beg-p001-1-l1", "speaker": "partner", "en": "Hey, are you almost here?", "ko": "야, 거의 다 왔어?", "audio": "…" },
        { "id": "beg-p001-1-l2", "speaker": "me", "en": "Sorry, I'm running a bit late. Traffic's crazy.", "ko": "미안, 좀 늦을 것 같아. 차가 엄청 막혀.", "focus": "running a bit late", "audio": "…" }
      ]
    }
  ]
}
```

zod 스키마(`src/content/schema.ts`, 앱과 스크립트가 같이 씀):
```ts
import { z } from 'zod';

export const LevelSchema = z.enum(['beginner', 'intermediate', 'advanced']);
const Line = z.object({
  en: z.string().min(1),
  ko: z.string().min(1),
  audio: z.string().regex(/^[0-9a-f]{16}\.mp3$/).optional(), // 생성 전엔 없음
});
const MeLine = Line.extend({ focus: z.string().min(1).optional() });

export const ExpressionSchema = z.object({
  id: z.string().regex(/^(beg|int|adv)-p\d{3}-\d$/),
  expression: z.string().min(1),
  meaning_ko: z.string().min(1),
  when_to_use: z.string().min(1),
  topic: z.enum(['daily', 'business', 'interview']),
  source_check: z.array(z.string().url()).min(1),
  audio: z.string().optional(),
  build_up: z.object({
    target_line_id: z.string(),
    chunks: z.array(z.object({ en: z.string(), audio: z.string().optional() })).min(2),
  }),
  derived: z.array(z.object({
    id: z.string(),
    type: z.enum(['substitution', 'transformation']),
    cue: Line,
    me: MeLine,
  })).min(2).max(3),
  dialogue: z.array(z.object({
    id: z.string(),
    speaker: z.enum(['partner', 'me']),
  }).merge(MeLine)).min(4).max(8),
});

export const PackSchema = z.object({
  schema_version: z.literal(1),
  level: LevelSchema,
  pack: z.number().int().positive(),
  expressions: z.array(ExpressionSchema).length(5),
});
```
추가 검사(`scripts/content/validate.ts`, zod로 표현이 어려운 규칙):
- 파생에 `substitution` ≥1, `transformation` ≥1
- 레벨별 문장 길이(초급 4–8, 중급 7–12, 고급 10–18단어)와 대화 턴 수(4 / 6 / 6–8)
- `build_up.chunks`의 마지막 = `target_line_id` 줄의 문장(구두점 차이 무시), 각 덩어리는 문장 **끝부분**(backward)
- `build_up.target_line_id`의 줄은 `speaker: "me"`
- 팩 단위 `daily` : 나머지 = 3:2 또는 2:3, **레벨 전체 50% ± 5%**
- `focus`가 있으면 그 문장 안에 실제로 들어 있는지(정규화 후)

### 3-2. 레벨 테스트 JSON — `public/content/level-test/set-a.json`

```json
{
  "schema_version": 1,
  "set_id": "set-a",
  "stage1_intermediate": [
    { "id": "lt-a-s1-01", "type": "repeat", "en": "I'd rather grab something quick before the meeting.", "audio": "…" },
    {
      "id": "lt-a-s1-02", "type": "situation_speak",
      "situation_ko": "동료가 회의를 오후로 옮겨도 되는지 묻는다. 3시 이후면 괜찮다고 말하기",
      "cue": { "en": "Can we push the meeting to this afternoon?", "audio": "…" },
      "accepted": ["Sure, anytime after three works for me.", "Yeah, after three is fine."]
    },
    {
      "id": "lt-a-s1-03", "type": "choose_response",
      "cue": { "en": "Do you mind if I sit here?", "audio": "…" },
      "options": [
        { "en": "Not at all, go ahead.", "audio": "…" },
        { "en": "Yes, sit down please.", "audio": "…" },
        { "en": "I don't mind to sit.", "audio": "…" }
      ],
      "answer_index": 0,
      "why_ko": "Do you mind ~? 에는 '괜찮다'가 Not at all"
    }
  ],
  "stage2_beginner": [ "… 9문항" ],
  "stage2_advanced": [ "… 9문항" ]
}
```
- 프롬프트 초안 대비 변경: `cue_en` → `cue: {en, audio}`, `options`를 `{en, audio}` 객체로(선택지 음성 듣기 요구사항). 
- 각 블록 유형 비율: repeat 3 / choose 3 / situation 3 (stage1은 2/2/2).
- repeat 문항은 블록 안에서 **짧은 것 → 긴 것** 순서(검사 스크립트가 단어 수 오름차순 확인).
- 세트 2개(`set-a`, `set-b`). 응시할 세트 = 가장 최근에 안 쓴 세트.

### 3-3. Supabase 테이블

| 테이블 | 용도 | 핵심 컬럼 |
|---|---|---|
| `settings` | 1행(내 설정) | 알림 시각 2개, 학습 시간(분), 시간대, 하루 경계, 저녁 리마인더 on/off |
| `morning_sessions` | 아침 학습 진행 + **완료되면 학습일** | `day_index`(완료 시 부여, unique), `service_date`(unique), `level`, `expression_ids[]`, `plan`(jsonb), `progress`(jsonb) |
| `quiz_sessions` | 학습일별 저녁 퀴즈 | `day_index`(unique), `status`, `items`(jsonb: 출제 목록 고정) |
| `quiz_answers` | 퀴즈 문항 결과(승급 계산용 요약) | `pair_id`, `expression_id`, `offset`(1/3/7), `level`, `first_try_passed`, `final_passed`, `revealed` |
| `attempts` | 모든 말하기 원시 기록 | `context`, `item_id`, `reference_text`, `recognized_text`, `word_accuracy`, `passed`, `pron`(jsonb), `audio_seconds` |
| `level_test_results` | 레벨 테스트 결과 | `set_id`, `route`, `stage1_score`, `stage2_score`, `type_scores`, `judged_level`, `items` |
| `level_changes` | 레벨 변경 이력 = **현재 레벨의 유일한 근거** | `from_level`, `to_level`, `reason`, `effective_from_day_index` |
| `push_subscriptions` | 웹 푸시 구독 | `endpoint`(unique), `p256dh`, `auth`, `status`, `last_success_at` |
| `push_log` | 발송 기록 + 중복 발송 방지 | unique(`user_id`,`kind`,`service_date`) |
| `usage_monthly` | 이번 달 Azure 사용량 | `month`, `tts_chars`, `stt_seconds` |

**중복 방지 설계 결정**
- "현재 레벨"을 `settings`에 따로 저장하지 않는다 → `level_changes`의 마지막 행에서 계산. (두 곳에 두면 언젠가 어긋남)
- "레벨별 진도"를 따로 저장하지 않는다 → `morning_sessions`(완료)에서 레벨별 `expression_ids` 개수 합으로 계산(`levelService.progressOf(level)`).
- 학습일 테이블을 따로 만들지 않는다 → `morning_sessions.status = 'completed'`인 행이 곧 학습일.

마이그레이션 `supabase/migrations/20261022000100_init_schema.sql` (발췌, 패턴 동일하게 전 테이블 적용):
```sql
-- 레벨 enum
create type public.level as enum ('beginner', 'intermediate', 'advanced');

create table public.settings (
  user_id uuid primary key references auth.users (id) on delete cascade,
  time_zone text not null default 'Asia/Seoul',
  day_start_hour smallint not null default 4 check (day_start_hour between 0 and 12),
  morning_push_time time not null default '07:00',
  evening_push_time time not null default '20:00',
  study_minutes smallint not null default 20 check (study_minutes in (10, 15, 20, 30, 40)),
  evening_reminder_if_no_morning boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  -- 푸시 시각은 05:00~23:00 (매분 체크 창이 자정을 넘지 않게)
  check (morning_push_time between '05:00' and '23:00'),
  check (evening_push_time between '05:00' and '23:00')
);

create table public.morning_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  status text not null default 'in_progress' check (status in ('in_progress', 'completed', 'abandoned')),
  level public.level not null,
  expression_ids text[] not null,
  plan jsonb not null,                 -- planStudyDay() 결과 스냅숏
  progress jsonb not null default '{}',
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  service_date date,                   -- 완료 시 서버 시각으로 계산
  day_index integer,                   -- 완료 시 부여 (Day N)
  unique (user_id, day_index),
  unique (user_id, service_date),
  check ((status = 'completed') = (day_index is not null and service_date is not null and completed_at is not null))
);

-- (quiz_sessions, quiz_answers, attempts, level_test_results, level_changes,
--  push_subscriptions, push_log, usage_monthly 도 같은 패턴)

-- RLS: 모든 테이블 "내 행만"
alter table public.settings enable row level security;
create policy "own rows" on public.settings
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
-- ... 각 테이블 반복

-- ★ research 4-5: 2026-05-30 이후 새 프로젝트는 GRANT가 없으면 Data API에서 안 보임
grant select, insert, update, delete on public.settings to authenticated;
-- ... 각 테이블 반복. anon 에게는 아무 권한도 주지 않는다.
```
- **Auth 설정**: Supabase 대시보드에서 "Allow new users to sign up" **끄기** → 내 계정 1개만 존재. 로그인은 **이메일 + 비밀번호**.
  - 이유: 매직 링크는 메일 앱 → **Safari**로 열린다. 홈 화면 앱은 Safari와 저장소가 분리되어 있어(research 2-4) 로그인 세션이 앱으로 넘어오지 않는다.
- 학습일 확정은 **DB 함수**로 원자적으로 처리(동시에 두 번 눌러도 Day가 2개 생기지 않게):

```sql
-- 학습일 확정: 서비스 날짜 계산은 TS(domain/learningDay.ts)가 "규칙의 원본"이고,
-- 여기서는 같은 규칙을 서버 시각으로 한 번 더 적용해 기록만 한다. (테스트로 두 구현 일치 확인 §7)
create function public.complete_morning_session(p_session_id uuid)
returns table (day_index integer, service_date date)
language plpgsql security invoker set search_path = '' as $$
declare
  v_tz text; v_start smallint; v_date date; v_next integer;
begin
  select s.time_zone, s.day_start_hour into v_tz, v_start
    from public.settings s where s.user_id = (select auth.uid());
  v_date := ((now() at time zone v_tz) - make_interval(hours => v_start))::date;
  select coalesce(max(m.day_index), 0) + 1 into v_next
    from public.morning_sessions m where m.user_id = (select auth.uid());
  update public.morning_sessions m
     set status = 'completed', completed_at = now(), service_date = v_date, day_index = v_next
   where m.id = p_session_id and m.user_id = (select auth.uid()) and m.status = 'in_progress';
  if not found then raise exception 'session not in progress'; end if;
  return query select v_next, v_date;
end $$;
grant execute on function public.complete_morning_session(uuid) to authenticated;
```
같은 서비스 날짜에 이미 완료된 세션이 있으면 `unique (user_id, service_date)` 위반 → 클라이언트는 "오늘은 이미 완료" 처리.

**트레이드오프**: 서비스 날짜 규칙이 TS와 SQL 두 곳에 존재. 대안(완료 시각을 클라이언트가 계산해 보냄)은 기기 시계가 틀리면 학습일이 틀어짐(research 9-1 #12). → SQL 쪽은 "기록용 1줄"로 최소화하고, **TS 단위 테스트와 같은 입력값으로 SQL 결과를 비교하는 테스트**를 둔다.

---

## 4. 코드 스니펫

### 4-1. 학습일 계산 + 퀴즈 출제 (1·3·7학습일 전)

`src/domain/learningDay.ts`
```ts
import type { Level } from './types';

export type ServiceDate = string; // 'YYYY-MM-DD'
export interface DayBoundary { timeZone: string; dayStartHour: number }

export interface LearningDay {
  dayIndex: number;          // Day N (1부터)
  serviceDate: ServiceDate;
  level: Level;
  expressionIds: string[];
  completedAt: string;       // ISO
}

/** 새벽 dayStartHour 시를 하루 경계로 하는 "서비스 날짜". 01:30 KST → 전날. */
export function serviceDateOf(instant: Date, b: DayBoundary): ServiceDate {
  const shifted = new Date(instant.getTime() - b.dayStartHour * 3_600_000);
  // en-CA 로케일은 YYYY-MM-DD 형식
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: b.timeZone, year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(shifted);
}

export function latestDay(days: readonly LearningDay[]): LearningDay | undefined {
  return days.reduce<LearningDay | undefined>((a, d) => (!a || d.dayIndex > a.dayIndex ? d : a), undefined);
}

export function isLearningDayDone(days: readonly LearningDay[], today: ServiceDate): boolean {
  return days.some((d) => d.serviceDate === today);
}

export const QUIZ_OFFSETS = [1, 3, 7] as const;

/** 학습일 n의 퀴즈 출처: n-1, n-3, n-7. 없으면 null(= "아직 없음") */
export function quizSourceDays(
  days: readonly LearningDay[],
  forDayIndex: number,
  offsets: readonly number[] = QUIZ_OFFSETS,
): { offset: number; day: LearningDay | null }[] {
  const byIndex = new Map(days.map((d) => [d.dayIndex, d]));
  return offsets.map((offset) => ({ offset, day: byIndex.get(forDayIndex - offset) ?? null }));
}

export type QuizStatus = 'in_progress' | 'completed' | 'missed';

export interface QuizAvailabilityInput {
  latest: LearningDay | undefined;
  latestQuizStatus: QuizStatus | undefined;     // 최근 학습일 퀴즈의 상태 (없으면 미시작)
  morningStartedAfterLatest: boolean;           // 다음 아침 학습을 시작했는가
  quizHasItems: boolean;                        // Day1처럼 출제 대상이 0개면 false
}

/** 지금 풀 수 있는 퀴즈의 학습일 번호. 없으면 null. (research 9-1 #1·#2·#3) */
export function pendingQuizDayIndex(i: QuizAvailabilityInput): number | null {
  if (!i.latest || !i.quizHasItems) return null;
  if (i.latestQuizStatus === 'completed' || i.latestQuizStatus === 'missed') return null;
  if (i.morningStartedAfterLatest) return null; // 다음 아침 시작 → 미응시 처리 대상
  return i.latest.dayIndex;
}

export type EveningPush = 'quiz' | 'remind_morning' | 'none';

/** 20:00 알림 내용 결정 (Q4 기본값: 리마인더 발송) */
export function decideEveningPush(p: {
  pendingQuiz: number | null;
  todayDone: boolean;
  remindIfNoMorning: boolean;
}): EveningPush {
  if (p.pendingQuiz !== null) return 'quiz';
  if (!p.todayDone && p.remindIfNoMorning) return 'remind_morning';
  return 'none';
}
```

`src/domain/quizSelection.ts`
```ts
import { mulberry32 } from './rng';
import type { LearningDay } from './learningDay';
import { quizSourceDays } from './learningDay';
import type { Level } from './types';

export interface QuizPair {
  pairId: string;          // derived id 또는 dialogue 'me' 줄 id
  expressionId: string;
  level: Level;
  cue: { en: string; audio?: string };
  me: { en: string; audio?: string; focus?: string };
}

export interface AskedHistory { pairId: string; dayIndex: number }

export interface QuizItem extends QuizPair { offset: number; sourceDayIndex: number }

/**
 * Q5 기본값: 그 표현에서 이미 나온 쌍은 제외. 전부 나왔으면 가장 오래전에 나온 쌍.
 * 같은 학습일이면 항상 같은 결과(시드 = 학습일 번호).
 */
export function pickPair(
  candidates: readonly QuizPair[],
  asked: readonly AskedHistory[],
  rand: () => number,
): QuizPair | null {
  if (candidates.length === 0) return null;
  const lastAsked = new Map<string, number>();
  for (const a of asked) lastAsked.set(a.pairId, Math.max(a.dayIndex, lastAsked.get(a.pairId) ?? -1));
  const fresh = candidates.filter((c) => !lastAsked.has(c.pairId));
  if (fresh.length > 0) return fresh[Math.floor(rand() * fresh.length)];
  return [...candidates].sort((a, b) => lastAsked.get(a.pairId)! - lastAsked.get(b.pairId)!)[0];
}

export function selectQuiz(input: {
  forDayIndex: number;
  days: readonly LearningDay[];
  candidatesOf: (expressionId: string) => readonly QuizPair[]; // content/contentIndex.ts 제공
  askedOf: (expressionId: string) => readonly AskedHistory[];  // quiz_answers 에서
  cap: number;                                                 // 3 × 오늘 N
}): { items: QuizItem[]; emptySections: number[] } {
  const rand = mulberry32(input.forDayIndex);
  const sections = quizSourceDays(input.days, input.forDayIndex);
  const emptySections = sections.filter((s) => !s.day).map((s) => s.offset);

  // 섹션별 후보 목록
  const perSection: QuizItem[][] = sections.map(({ offset, day }) =>
    (day?.expressionIds ?? []).flatMap((exprId) => {
      const pair = pickPair(input.candidatesOf(exprId), input.askedOf(exprId), rand);
      return pair ? [{ ...pair, offset, sourceDayIndex: day!.dayIndex }] : [];
    }),
  );

  // 상한을 넘으면 섹션을 돌아가며 1개씩 뽑는다(1일 전 → 3일 전 → 7일 전 → …)
  const items: QuizItem[] = [];
  for (let round = 0; items.length < input.cap; round++) {
    let added = false;
    for (const list of perSection) {
      if (round < list.length && items.length < input.cap) { items.push(list[round]); added = true; }
    }
    if (!added) break;
  }
  return { items, emptySections };
}
```
퀴즈 후보 쌍 만들기(`src/content/contentIndex.ts`): 파생 3개 + 대화에서 **바로 앞 줄이 partner인 me 줄**(앞 줄이 없으면 제외).

**대안 코드 — 퀴즈를 학습일 완료 시점에 미리 뽑아 저장**
```ts
// morningService.complete() 안에서
const quiz = selectQuiz({...});
await quizRepo.createPending(client, { dayIndex, items: quiz.items });
```
| | 채택안(퀴즈 열 때 생성 + 생성 후 `quiz_sessions.items`에 고정) | 대안(아침 완료 시 미리 생성) |
|---|---|---|
| 장점 | 학습 시간 설정 변경·콘텐츠 수정이 저녁 전까지 반영 | 저녁 알림 함수가 문항 수를 바로 알 수 있음 |
| 단점 | 처음 열 때 약간의 계산(수 ms) | 아침 완료 로직이 퀴즈까지 알게 되어 결합도 증가 |
| 결과 일관성 | 시드 고정 + 생성 후 저장이라 다시 열어도 같음 | 같음 |

### 4-2. 텍스트 정규화 + 단어 단위 비교

`src/domain/normalize.ts`
```ts
const WHOLE: Record<string, string> = {
  "i'm": 'i am', "let's": 'let us', "won't": 'will not', "can't": 'can not',
  cannot: 'can not', "shan't": 'shall not', "ain't": 'is not', "y'all": 'you all',
};
const SUFFIX: readonly [RegExp, string][] = [
  [/n't$/, ' not'], [/'re$/, ' are'], [/'ll$/, ' will'], [/'ve$/, ' have'], [/'m$/, ' am'],
  [/'s$/, " 's"],  // is / has / 소유격 → 비교 단계에서 동치 처리
  [/'d$/, " 'd"],  // would / had
];
/** 비교할 때 같은 단어로 볼 토큰 (양방향) */
export const EQUIVALENT: Readonly<Record<string, readonly string[]>> = {
  "'s": ['is', 'has'], "'d": ['would', 'had'],
  ok: ['okay'], okay: ['ok'], alright: ['all right'],
};
const FILLERS = new Set(['um', 'uh', 'er', 'erm', 'hmm', 'mm']);
const UNITS: Record<string, number> = {
  zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9,
  ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16,
  seventeen: 17, eighteen: 18, nineteen: 19,
};
const TENS: Record<string, number> = {
  twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90,
};

export function normalizeTokens(text: string): string[] {
  let s = text.normalize('NFKC').toLowerCase()
    .replace(/[’‘ʼ`]/g, "'")
    .replace(/(\d{1,2}):(\d{2})/g, (_, h: string, m: string) => (m === '00' ? h : `${h} ${m}`))
    .replace(/\bo'clock\b/g, ' ')
    .replace(/-/g, ' ')
    .replace(/[^a-z0-9'\s]/g, ' ');

  const tokens: string[] = [];
  for (const raw of s.split(/\s+/)) {
    const w = raw.replace(/^'+|'+$/g, '');
    if (!w || FILLERS.has(w)) continue;
    const expanded = WHOLE[w] ?? SUFFIX.reduce((acc, [re, rep]) => acc.replace(re, rep), w);
    tokens.push(...expanded.split(' ').filter(Boolean));
  }
  return numbersToDigits(tokens);
}

function numbersToDigits(tokens: string[]): string[] {
  const out: string[] = [];
  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    const next = tokens[i + 1];
    if (t in TENS && next !== undefined && next in UNITS && UNITS[next] > 0 && UNITS[next] < 10) {
      out.push(String(TENS[t] + UNITS[next])); i++;
    } else if (t in TENS) out.push(String(TENS[t]));
    else if (t in UNITS) out.push(String(UNITS[t]));
    else out.push(t);
  }
  return out;
}
```

`src/domain/wordDiff.ts`
```ts
import { EQUIVALENT } from './normalize';

export type DiffOp =
  | { kind: 'match'; ref: string; hyp: string; refIndex: number }
  | { kind: 'sub'; ref: string; hyp: string; refIndex: number }
  | { kind: 'del'; ref: string; refIndex: number }   // 말하지 않은 단어
  | { kind: 'ins'; hyp: string };                    // 정답에 없는 단어

export const same = (a: string, b: string) => a === b || (EQUIVALENT[a]?.includes(b) ?? false);

/** 단어 단위 Levenshtein + 역추적. 최대 18단어라 O(N·M)로 충분 */
export function wordDiff(ref: readonly string[], hyp: readonly string[]): DiffOp[] {
  const n = ref.length, m = hyp.length;
  const d = Array.from({ length: n + 1 }, (_, i) => Array.from({ length: m + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0)));
  for (let i = 1; i <= n; i++)
    for (let j = 1; j <= m; j++)
      d[i][j] = Math.min(
        d[i - 1][j - 1] + (same(ref[i - 1], hyp[j - 1]) ? 0 : 1),
        d[i - 1][j] + 1,
        d[i][j - 1] + 1,
      );

  const ops: DiffOp[] = [];
  let i = n, j = m;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && d[i][j] === d[i - 1][j - 1] + (same(ref[i - 1], hyp[j - 1]) ? 0 : 1)) {
      const kind = same(ref[i - 1], hyp[j - 1]) ? 'match' : 'sub';
      ops.push({ kind, ref: ref[i - 1], hyp: hyp[j - 1], refIndex: i - 1 }); i--; j--;
    } else if (i > 0 && d[i][j] === d[i - 1][j] + 1) {
      ops.push({ kind: 'del', ref: ref[i - 1], refIndex: i - 1 }); i--;
    } else {
      ops.push({ kind: 'ins', hyp: hyp[j - 1] }); j--;
    }
  }
  return ops.reverse();
}

export interface PassRule { errorRatio: number; minAllowedErrors: number } // 기본 0.2, 1

export function judge(ops: readonly DiffOp[], refLen: number, focus: readonly string[], rule: PassRule) {
  const errors = ops.filter((o) => o.kind !== 'match').length;
  const matched = new Set(ops.flatMap((o) => (o.kind === 'match' ? [o.refIndex] : [])));
  const allowed = Math.max(rule.minAllowedErrors, Math.round(rule.errorRatio * refLen));
  const focusOk = focusMatched(ops, focus, matched);
  return {
    wordAccuracy: refLen === 0 ? 0 : matched.size / refLen,
    wer: refLen === 0 ? 1 : errors / refLen,
    errors, allowed, focusOk,
    passed: errors <= allowed && focusOk,
  };
}

function focusMatched(ops: readonly DiffOp[], focus: readonly string[], matched: Set<number>): boolean {
  if (focus.length === 0) return true;
  const ref = ops.flatMap((o) => ('refIndex' in o ? [{ i: o.refIndex, w: o.ref }] : []));
  for (let s = 0; s + focus.length <= ref.length; s++) {
    if (focus.every((f, k) => same(ref[s + k].w, f))) return focus.every((_, k) => matched.has(ref[s + k].i));
  }
  return false; // 콘텐츠 검사 스크립트가 focus 포함 여부를 미리 보장
}
```
**대안**: `diff` npm 패키지의 `diffWords()`(LCS). 대치를 "삭제+삽입" 두 개로 보여줘 하이라이트가 덜 직관적이고, 축약 동치(`'s`↔`is`)를 끼워 넣기 어렵다 → 직접 구현(위 60줄) 채택. 나중에 바꾸려면 `wordDiff()`만 교체하면 되고 `judge()`와 화면은 `DiffOp` 형식만 지키면 그대로.

### 4-3. 레벨 테스트 2단계 분기 + 점수 → 레벨 판정

`src/domain/levelTest.ts`
```ts
import type { Level } from './types';

export interface LevelTestConfig {
  stage1ToAdvancedMin: number;   // 0.60
  advancedKeepMin: number;       // 0.65
  beginnerToIntermediateMin: number; // 0.75
  repeatWeights: { words: number; pron: number }; // 0.7 / 0.3
  repeatDelayMs: number;         // 1500 (research 7-1: 응답 전 pause 설계가 타당도↑)
}

export type ItemResult =
  | { type: 'repeat'; wordAccuracy: number; pronAccuracy: number | null }   // pron 0~100
  | { type: 'choose_response'; correct: boolean }
  | { type: 'situation_speak'; bestWordAccuracy: number };                   // 허용 답안 중 최고

export function itemScore(r: ItemResult, cfg: LevelTestConfig): number {
  switch (r.type) {
    case 'repeat':
      return r.pronAccuracy === null
        ? r.wordAccuracy
        : cfg.repeatWeights.words * r.wordAccuracy + cfg.repeatWeights.pron * (r.pronAccuracy / 100);
    case 'choose_response': return r.correct ? 1 : 0;
    case 'situation_speak': return r.bestWordAccuracy;
  }
}

export const mean = (xs: readonly number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);

export type Route = 'beginner' | 'advanced';

export function routeAfterStage1(stage1Score: number, cfg: LevelTestConfig): Route {
  return stage1Score >= cfg.stage1ToAdvancedMin ? 'advanced' : 'beginner';
}

export function judgeLevel(route: Route, stage2Score: number, cfg: LevelTestConfig): Level {
  if (route === 'advanced') return stage2Score >= cfg.advancedKeepMin ? 'advanced' : 'intermediate';
  return stage2Score >= cfg.beginnerToIntermediateMin ? 'intermediate' : 'beginner';
}

export function typeScores(results: readonly ItemResult[], cfg: LevelTestConfig) {
  const by = (t: ItemResult['type']) => mean(results.filter((r) => r.type === t).map((r) => itemScore(r, cfg)));
  return { repeat: by('repeat'), choose_response: by('choose_response'), situation_speak: by('situation_speak') };
}
```

**기준값 제안과 근거**
| 값 | 기본 | 근거 |
|---|---|---|
| 1단계 → 고급 블록 | **0.60** | 1단계는 **중급(B1)** 문항. 일반적 숙달 판정 관행 "그 레벨 문항의 60~75%를 해내면 그 레벨"(research 7-3)의 하한. 중급을 겨우 넘는 사람도 고급 블록에서 한 번 더 확인받게 일부러 낮게. misrouting 영향은 작다는 ETS 시뮬레이션(research 7-2)이 낮은 라우팅 기준을 뒷받침 |
| 고급 블록 → 고급 유지 | **0.65** | B2–C1 문항을 2/3 해내면 고급. 실패 시 중급으로 내려오므로 한쪽으로 치우친 오판 위험 낮음 |
| 초급 블록 → 중급 | **0.75** | 초급 블록은 쉬운 문항이라 "거의 다(75%)" 해내야 중급으로. 1단계(중급) 60% 미만인 사람이므로 확실할 때만 올림 |
| repeat 가중치 | 단어 0.7 / 발음 0.3 | EI 연구의 핵심 지표는 "얼마나 정확히 재생했나"(단어). 발음은 보조 |
| 응답 전 지연 | 1.5초 + 삐 소리 | 메타분석: pause 있는 설계 r=.76 vs 즉시 r=.63 |

- 결과 화면: 판정 레벨, 유형별 점수(`typeScores`), 틀린 문장 다시 듣기, **이전 테스트와 비교**(`level_test_results` 직전 행).
- 보정: 판정 후 첫 10학습일 퀴즈 첫 시도 통과율이 50% 미만 또는 95% 이상이면 설정 화면에 "레벨 테스트 기준이 맞지 않을 수 있어요" 표시(자동 변경은 안 함).

### 4-4. (Q2) 학습 시간 → 학습량

`src/domain/studyBudget.ts`
```ts
import type { Level } from './types';

export interface StudyCostTable {
  morningPerExpr: Record<Level, number>;   // 118 / 150 / 190
  quizPerItem: Record<Level, number>;      // 19 / 23 / 27
  roleSwap: Record<Level, number>;         // 30 / 45 / 60
  buildUpAlwaysExtra: Record<Level, number>; // 25 / 30 / 35
  fixedOverhead: number;                   // 90
  maxExpressions: number;                  // 5
  quizOffsets: number;                     // 3 (1·3·7)
}

export interface DayPlan {
  expressions: number;              // N
  buildUp: 'on_fail' | 'always';
  roleSwapDialogues: number;        // 역할 교대할 대화 수 (≥1)
  quizCap: number;                  // 3 × N
  estimatedSeconds: number;
}

export function planStudyDay(minutes: number, level: Level, c: StudyCostTable): DayPlan {
  const perExpr = c.morningPerExpr[level] + c.quizOffsets * c.quizPerItem[level];
  let budget = minutes * 60 - c.fixedOverhead - c.roleSwap[level];
  const n = Math.min(c.maxExpressions, Math.max(1, Math.floor(budget / perExpr)));
  budget -= n * perExpr;

  let buildUp: DayPlan['buildUp'] = 'on_fail';
  const buildUpCost = n * c.buildUpAlwaysExtra[level];
  if (budget >= buildUpCost) { buildUp = 'always'; budget -= buildUpCost; }

  let roleSwapDialogues = 1;
  while (roleSwapDialogues < n && budget >= c.roleSwap[level]) { roleSwapDialogues++; budget -= c.roleSwap[level]; }

  return {
    expressions: n, buildUp, roleSwapDialogues,
    quizCap: c.quizOffsets * n,
    estimatedSeconds: minutes * 60 - Math.max(0, budget),
  };
}
```
- 10분인데 고급 표현 1개(=271초+고정)가 예산보다 커도 **최소 1개**는 한다(`max(1, …)`) → 그날은 10분을 약간 넘을 수 있음. 화면에 "예상 약 7분/12분"처럼 `estimatedSeconds` 표시.

### 4-5. 자동 승급 / 하향 권유 규칙

`src/domain/promotion.ts`
```ts
import type { Level } from './types';

export interface PromotionConfig {
  minDays: number;           // 10 (최근 10학습일)
  maxLookbackDays: number;   // 30
  minQuizDayRatio: number;   // 0.8 (10일 중 8일 이상 응시)
  minGradedItems: number;    // 40
  promoteAt: number;         // 0.85
  suggestRetestBelow: number;// 0.50
  suggestCooldownDays: number; // 7
}

/** 학습일 하나의 "현재 레벨 문항만" 집계 (research 8-2 ③) */
export interface DayQuizStat { dayIndex: number; quizTaken: boolean; graded: number; firstTryPassed: number }

export type PromotionDecision =
  | { kind: 'promote'; to: Level; rate: number }
  | { kind: 'suggest_retest'; rate: number }
  | { kind: 'none'; reason: 'not_enough_days' | 'not_enough_quiz_days' | 'not_enough_items' | 'in_range' | 'top_level' | 'cooldown'; rate?: number };

const NEXT: Record<Level, Level | null> = { beginner: 'intermediate', intermediate: 'advanced', advanced: null };

export function evaluatePromotion(input: {
  currentLevel: Level;
  levelSinceDayIndex: number;            // 현재 레벨이 적용된 첫 학습일 (승급 후 창 리셋: 8-2 ⑤)
  stats: readonly DayQuizStat[];         // 학습일 오름차순
  lastSuggestDayIndex: number | null;
  cfg: PromotionConfig;
}): PromotionDecision {
  const { cfg } = input;
  const eligible = input.stats.filter((s) => s.dayIndex >= input.levelSinceDayIndex);

  // 최근부터 거꾸로: 최소 minDays일 AND 채점 문항 minGradedItems개가 모일 때까지 (최대 maxLookbackDays)
  const window: DayQuizStat[] = [];
  let graded = 0;
  for (let i = eligible.length - 1; i >= 0 && window.length < cfg.maxLookbackDays; i--) {
    window.push(eligible[i]); graded += eligible[i].graded;
    if (window.length >= cfg.minDays && graded >= cfg.minGradedItems) break;
  }
  if (window.length < cfg.minDays) return { kind: 'none', reason: 'not_enough_days' };
  if (window.filter((d) => d.quizTaken).length < Math.ceil(window.length * cfg.minQuizDayRatio))
    return { kind: 'none', reason: 'not_enough_quiz_days' };
  if (graded < cfg.minGradedItems) return { kind: 'none', reason: 'not_enough_items' };

  const rate = window.reduce((a, d) => a + d.firstTryPassed, 0) / graded; // 첫 시도 통과율 (8-2 ①)
  const next = NEXT[input.currentLevel];
  if (rate >= cfg.promoteAt) return next ? { kind: 'promote', to: next, rate } : { kind: 'none', reason: 'top_level', rate };
  if (rate < cfg.suggestRetestBelow) {
    const latest = eligible[eligible.length - 1].dayIndex;
    const cooling = input.lastSuggestDayIndex !== null && latest - input.lastSuggestDayIndex < cfg.suggestCooldownDays;
    return cooling ? { kind: 'none', reason: 'cooldown', rate } : { kind: 'suggest_retest', rate };
  }
  return { kind: 'none', reason: 'in_range', rate };
}
```
- **왜 "최소 10일 AND 40문항"인가** (Q2의 영향): 학습 시간 10분·고급이면 하루 퀴즈가 3문항뿐 → 10일에 30문항이라 원래 규칙(10일)만 쓰면 3문항×10일 표본으로 승급이 결정된다. 문항 수 조건을 추가하고 부족하면 창을 최대 30일까지 넓힌다.
- 평가 시점: 저녁 퀴즈 완료 직후 `levelService.afterQuizCompleted()`에서 1번. 승급이면 `level_changes`에 `effective_from_day_index = 다음 학습일` 기록 + 푸시(`kind: 'promotion'`).

### 4-6. TTS 일괄 생성 스크립트 (해시 캐시)

`scripts/tts/generate-audio.ts` — 로컬에서 `npm run tts:generate -- --level beginner` 로 실행. 키는 로컬 `.env.local`에만.
```ts
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { createClient } from '@supabase/supabase-js';
import { glob } from 'node:fs/promises';
import { PackSchema } from '../../src/content/schema';
import { VOICES } from '../../src/config/voices';
import { DEFAULTS } from '../../src/config/defaults';

const OUTPUT_FORMAT = 'audio-24khz-48kbitrate-mono-mp3';
const { AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OWNER_USER_ID } = process.env;
const BUCKET = 'audio';

/** 파일명 = sha256(음성 이름 + 출력 형식 + 문장)의 앞 16자리 → 같은 문장·같은 음성은 다시 만들지 않음 */
export const audioKey = (voice: string, text: string) =>
  createHash('sha256').update(`${voice}\n${OUTPUT_FORMAT}\n${text}`).digest('hex').slice(0, 16) + '.mp3';

const escapeXml = (s: string) => s.replace(/[<>&'"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' })[c]!);

async function synthesize(voice: string, text: string): Promise<Buffer> {
  // <speak>/<voice> 태그는 과금 글자에서 제외 (research 5-1) → 다른 SSML 태그는 쓰지 않는다
  const ssml = `<speak version="1.0" xml:lang="en-US"><voice name="${voice}">${escapeXml(text)}</voice></speak>`;
  const res = await fetch(`https://${AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1`, {
    method: 'POST',
    headers: {
      'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY!,
      'Content-Type': 'application/ssml+xml',
      'X-Microsoft-OutputFormat': OUTPUT_FORMAT,
      'User-Agent': 'english-speaking-app-tts',
    },
    body: ssml,
  });
  if (res.status === 429) throw new RetryableError('rate limited');
  if (!res.ok) throw new Error(`TTS ${res.status}: ${await res.text()}`);
  return Buffer.from(await res.arrayBuffer());
}

class RetryableError extends Error {}
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const level = process.argv[process.argv.indexOf('--level') + 1];
  const supabase = createClient(SUPABASE_URL!, SUPABASE_SERVICE_ROLE_KEY!);
  const existing = await listAll(supabase);               // 버킷에 이미 있는 파일명 Set
  const minInterval = 60_000 / DEFAULTS.tts.requestsPerMinute; // F0 가정 20/분 → 3초
  let chars = 0;

  for await (const file of glob(`public/content/${level}/pack-*.json`)) {
    const pack = PackSchema.parse(JSON.parse(await readFile(file, 'utf8')));
    let changed = false;
    for (const job of collectJobs(pack)) {                // {voice, text, assign(key)}
      const key = audioKey(job.voice, job.text);
      job.assign(key); changed = true;
      if (existing.has(key)) continue;                    // ★ 캐시 적중: 생성·과금 없음
      const mp3 = await withRetry(() => synthesize(job.voice, job.text));
      await supabase.storage.from(BUCKET).upload(key, mp3, { contentType: 'audio/mpeg', upsert: false });
      existing.add(key);
      chars += job.text.length;
      await sleep(minInterval);
    }
    if (changed) await writeFile(file, JSON.stringify(pack, null, 2) + '\n');
  }
  // 사용량 카운터 (앱 설정 화면 표시용)
  await supabase.rpc('increment_usage_for', { p_user_id: OWNER_USER_ID, p_tts_chars: chars, p_stt_seconds: 0 });
  console.log(`generated chars: ${chars}`);
}
```
- `collectJobs()`: 표현·build-up 덩어리·파생 `me`·대화 `me` 줄 → `VOICES.me` / 파생 `cue`·대화 `partner` 줄 → `VOICES.partner`.
- 중단 후 다시 실행해도 버킷 목록으로 건너뛰므로 **이어하기**가 자연히 된다.
- `--dry-run`: 생성 없이 "새로 만들 글자 수 / 이번 달 남은 한도"만 출력 → **한도 초과 전에 멈춤**(남은 한도보다 크면 실행 거부).

**대안 — 음성 파일을 저장소 `public/audio/`에 커밋**
```ts
await writeFile(`public/audio/${key}`, mp3);   // Vercel 정적 파일로 배포
```
| | 채택: Supabase Storage(public 버킷) | 대안: `public/audio` 커밋 |
|---|---|---|
| 장점 | git 저장소가 가벼움(약 100MB 바이너리 제외), 콘텐츠 수정 시 재배포 불필요 | 외부 의존 없음, Vercel CDN, 오프라인 캐시 쉬움 |
| 단점 | Storage 1GB / egress 5GB 한도(사용량 약 10% / 매우 적음) | 저장소가 계속 커짐, 문장 수정마다 바이너리 커밋 |
| 고치는 곳 | `BUCKET` 상수와 `contentRepo.audioUrl()` 한 곳 | 같은 두 곳 |

### 4-7. Azure 토큰 발급 서버리스 함수

`api/speech-token.ts`
```ts
import type { VercelRequest, VercelResponse } from '@vercel/node';
import { createClient } from '@supabase/supabase-js';

const { AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, SUPABASE_URL, SUPABASE_ANON_KEY, OWNER_USER_ID } = process.env;

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') return res.status(405).end();

  // research 5-4: 비밀값 헤더는 클라이언트 번들에 노출되므로 쓰지 않는다 → 로그인 세션으로 확인
  const jwt = req.headers.authorization?.replace(/^Bearer /, '');
  if (!jwt) return res.status(401).json({ error: 'no session' });
  const supabase = createClient(SUPABASE_URL!, SUPABASE_ANON_KEY!);
  const { data, error } = await supabase.auth.getUser(jwt);
  if (error || data.user?.id !== OWNER_USER_ID) return res.status(401).json({ error: 'unauthorized' });

  const r = await fetch(`https://${AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken`, {
    method: 'POST',
    headers: { 'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY!, 'Content-Length': '0' },
  });
  if (!r.ok) return res.status(502).json({ error: `issueToken ${r.status}` });

  res.setHeader('Cache-Control', 'no-store');
  return res.json({ token: await r.text(), region: AZURE_SPEECH_REGION, expiresInSec: 540 }); // 10분 유효, 9분에 갱신
}
```

**대안 코드 — 비밀값 헤더 방식** (프롬프트 v2 원안)
```ts
if (req.headers['x-app-secret'] !== process.env.APP_SECRET) return res.status(401).end();
// 클라이언트: fetch('/api/speech-token', { headers: { 'x-app-secret': import.meta.env.VITE_APP_SECRET } })
```
| | 채택: 세션 JWT 확인 | 대안: 비밀값 헤더 |
|---|---|---|
| 보호 효과 | 로그인한 나만 통과 | `VITE_` 값은 번들에 그대로 들어감 → 누구나 꺼내 쓸 수 있음 = **보호 없음** |
| 비용 | 토큰 요청마다 Supabase `getUser` 1회(9분에 1번) | 없음 |
| 고치는 곳 | `api/speech-token.ts` 인증 블록 | — |

### 4-8. 말하기 1회 = 녹음 → STT + 발음 평가(같은 요청, Q3) → 채점

`src/services/speech/azureRecognizer.ts`
```ts
import * as sdk from 'microsoft-cognitiveservices-speech-sdk';
import { getToken } from './tokenClient';

export interface RecognizeResult {
  text: string;
  pron: null | {
    accuracy: number; fluency: number; completeness: number; prosody: number | null; overall: number;
    words: { word: string; accuracy: number; errorType: string }[];
  };
  audioSeconds: number;
}

/** 이미 녹음된 16kHz Int16 PCM을 보내 텍스트와 발음 점수를 "한 요청"으로 받는다 */
export async function recognizeWithAssessment(pcm: Int16Array, referenceText: string | null): Promise<RecognizeResult> {
  const { token, region } = await getToken();
  const speechConfig = sdk.SpeechConfig.fromAuthorizationToken(token, region);
  speechConfig.speechRecognitionLanguage = 'en-US';

  const push = sdk.AudioInputStream.createPushStream(sdk.AudioStreamFormat.getWaveFormatPCM(16000, 16, 1));
  push.write(pcm.buffer.slice(pcm.byteOffset, pcm.byteOffset + pcm.byteLength) as ArrayBuffer);
  push.close();

  const recognizer = new sdk.SpeechRecognizer(speechConfig, sdk.AudioConfig.fromStreamInput(push));
  if (referenceText) {
    const pa = new sdk.PronunciationAssessmentConfig(
      referenceText,
      sdk.PronunciationAssessmentGradingSystem.HundredMark,
      sdk.PronunciationAssessmentGranularity.Word,
      true, // enableMiscue: 빠뜨린/덧붙인 단어 표시
    );
    pa.enableProsodyAssessment = true; // research 5-2: SDK 1.52에서 속성/메서드 여부 구현 시 확인
    pa.applyTo(recognizer);
  }

  try {
    const result = await new Promise<sdk.SpeechRecognitionResult>((resolve, reject) =>
      recognizer.recognizeOnceAsync(resolve, reject));
    const audioSeconds = pcm.length / 16000; // 과금 = 보낸 오디오 길이 (research 5-1)
    if (result.reason !== sdk.ResultReason.RecognizedSpeech) return { text: '', pron: null, audioSeconds };
    if (!referenceText) return { text: result.text, pron: null, audioSeconds };
    const r = sdk.PronunciationAssessmentResult.fromResult(result);
    return {
      text: result.text,
      audioSeconds,
      pron: {
        accuracy: r.accuracyScore, fluency: r.fluencyScore, completeness: r.completenessScore,
        prosody: r.prosodyScore ?? null, overall: r.pronunciationScore,
        words: r.detailResult.Words.map((w) => ({
          word: w.Word,
          accuracy: w.PronunciationAssessment?.AccuracyScore ?? 0,
          errorType: w.PronunciationAssessment?.ErrorType ?? 'None',
        })),
      },
    };
  } finally {
    recognizer.close();
  }
}
```
- `referenceText = null`: 레벨 테스트 "상황 말하기"(허용 답안이 여러 개라 기준 문장이 하나가 아님) → 프롬프트대로 단어 일치율만.
- 화면: "발음 채점" 버튼은 이미 받은 `pron`을 펼쳐 보여주기만 한다(추가 호출 0).
- `attemptService.run()`이 이 결과를 받아 `normalizeTokens` → `wordDiff` → `judge` → `attemptRepo.insert` → `usageRepo.addStt(audioSeconds)` 순으로 처리.

**대안 코드 — SDK에 마이크를 직접 맡기기**
```ts
const recognizer = new sdk.SpeechRecognizer(speechConfig, sdk.AudioConfig.fromDefaultMicrophoneInput());
recognizer.recognizeOnceAsync(cb); // SDK가 침묵을 감지해 자동 종료
```
| | 채택: 내 녹음 PCM → push stream | 대안: `fromDefaultMicrophoneInput` |
|---|---|---|
| 내 녹음 듣기·A/B 비교 | 같은 PCM으로 WAV를 만들어 바로 가능 | SDK가 오디오를 안 넘겨줘서 **녹음을 따로** 해야 함 → `getUserMedia` 이중 호출(권한 팝업·iOS 오디오 세션 충돌 위험) |
| 과금 시간 | 앞뒤 무음을 VAD로 잘라서 보냄 → 절약(research 11-2 S3) | 마이크가 열린 시간 전부 과금 |
| 첫 결과 속도 | 말 끝난 뒤 업로드 → 0.5~1초 늦음 | 말하는 동안 스트리밍 → 빠름 |
| 고치는 곳 | `azureRecognizer.ts` 한 파일 | 같은 파일 |

### 4-9. 녹음 / 재생 / A·B 비교

`public/worklets/pcm-capture.js`
```js
// 마이크 Float32 샘플을 128프레임 단위로 메인 스레드에 넘긴다
class PcmCapture extends AudioWorkletProcessor {
  process(inputs) {
    const ch = inputs[0]?.[0];
    if (ch) this.port.postMessage(ch.slice(0));
    return true;
  }
}
registerProcessor('pcm-capture', PcmCapture);
```

`src/services/audio/pcmRecorder.ts` (핵심 부분)
```ts
import { getMicStream } from './micStream';

export interface RecorderOptions { silenceMs: number; maxMs: number; energyThreshold: number; preRollMs: number }

/** 탭으로 시작 → 말이 끝나고 silenceMs 무음이면 자동 종료. 결과: 16kHz Int16 PCM (앞 무음은 preRoll만 남김) */
export async function recordUtterance(ctx: AudioContext, o: RecorderOptions, signal?: AbortSignal): Promise<Int16Array> {
  const stream = await getMicStream();                    // 세션당 1회 getUserMedia
  await ctx.audioWorklet.addModule('/worklets/pcm-capture.js');
  const src = ctx.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(ctx, 'pcm-capture');
  src.connect(node);

  const chunks: Float32Array[] = [];
  const rate = ctx.sampleRate;                            // ★ 실제 값 사용 (iOS 44.1k/48k 불일치: research 2-5)
  let voiced = false, silentSamples = 0, total = 0, voiceStartIndex = 0;

  return new Promise((resolve) => {
    const finish = () => {
      node.port.onmessage = null; src.disconnect(); node.disconnect();
      const preRoll = Math.floor((o.preRollMs / 1000) * rate / 128);
      const used = chunks.slice(Math.max(0, voiceStartIndex - preRoll), chunks.length - Math.floor(silentSamples / 128) + Math.floor(rate * 0.2 / 128));
      resolve(toInt16(resample(concat(used), rate, 16000)));
    };
    signal?.addEventListener('abort', finish);
    node.port.onmessage = (e: MessageEvent<Float32Array>) => {
      chunks.push(e.data); total += e.data.length;
      const rms = Math.sqrt(e.data.reduce((a, x) => a + x * x, 0) / e.data.length);
      if (rms > o.energyThreshold) { if (!voiced) voiceStartIndex = chunks.length - 1; voiced = true; silentSamples = 0; }
      else if (voiced) silentSamples += e.data.length;
      if ((voiced && silentSamples >= (o.silenceMs / 1000) * rate) || total >= (o.maxMs / 1000) * rate) finish();
    };
  });
}
// concat / resample(선형 보간) / toInt16 는 같은 파일의 작은 순수 함수 → 단위 테스트
```
`src/services/audio/wav.ts`: `pcmToWavBlob(pcm: Int16Array, sampleRate = 16000): Blob` (44바이트 RIFF 헤더 + 데이터).

`src/services/audio/player.ts`
```ts
/** 앱 전체에서 오디오 요소 1개만 재사용 (iOS 자동재생 규칙: research 2-3) */
const el = new Audio();
el.preload = 'auto';
(el as HTMLAudioElement & { preservesPitch?: boolean }).preservesPitch = true;

export type Speed = 0.75 | 1;

/** 반드시 탭 핸들러 안에서 동기적으로 호출할 것 */
export function play(src: string, speed: Speed = 1): Promise<void> {
  el.pause();
  el.src = src;
  el.playbackRate = speed; // 같은 mp3를 속도별로 두 번 만들지 않음
  return new Promise((resolve, reject) => {
    el.onended = () => resolve();
    el.play().catch(reject);
  });
}

export function stop() { el.pause(); }

/** A/B 비교: 원어민 → 내 녹음 (또는 순서 바꿔) 연달아 재생 */
export async function playAB(nativeSrc: string, mineBlob: Blob, order: 'native-first' | 'mine-first' = 'native-first') {
  const mine = URL.createObjectURL(mineBlob);
  try {
    const seq = order === 'native-first' ? [nativeSrc, mine] : [mine, nativeSrc];
    for (const s of seq) await play(s);
  } finally {
    URL.revokeObjectURL(mine);
  }
}
```
- `play()`는 Promise를 기다리지 않고 **탭 이벤트 안에서 시작**만 하면 됨(첫 `el.play()` 호출이 제스처 안에 있으면 iOS가 허용). A/B 연속 재생의 두 번째 재생이 막히면(⚠️ T4) "다음 재생" 버튼으로 바꾸는 대체 UI.

**대안 — Web Audio `AudioBufferSourceNode`**
```ts
const buf = await ctx.decodeAudioData(await (await fetch(src)).arrayBuffer());
const node = ctx.createBufferSource(); node.buffer = buf; node.playbackRate.value = 0.75;
node.connect(ctx.destination); node.start();
```
| | 채택: `<audio>` 1개 | 대안: Web Audio |
|---|---|---|
| 0.75배속 음높이 | `preservesPitch`로 유지(⚠️ 확인) | **음높이도 같이 낮아짐** |
| 자동재생 | 첫 탭 이후 같은 요소 재사용 | `ctx.resume()` 한 번이면 이후 자유로움 |
| 언제 바꾸나 | T4에서 `playbackRate`가 무시되면 | — |

### 4-10. 푸시: 구독 저장 → 발송 함수 → 07:00 / 20:00 스케줄

**① 구독 저장** — 별도 API 없이 `pushSubscriptionRepo`로 Supabase에 upsert (RLS). (같은 일을 하는 엔드포인트 중복 방지)
```ts
// src/services/pushService.ts (클라이언트)
export async function ensureSubscribed(client: SupabaseClient, vapidPublicKey: string) {
  const reg = await navigator.serviceWorker.ready;
  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    // ★ 반드시 버튼 탭 핸들러에서 호출되는 경로여야 한다 (research 3)
    sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(vapidPublicKey) });
  }
  const json = sub.toJSON();
  await pushSubscriptionRepo.upsert(client, {
    endpoint: json.endpoint!, p256dh: json.keys!.p256dh, auth: json.keys!.auth, userAgent: navigator.userAgent,
  });
}
// 앱 시작 시: getSubscription()만 해서 있으면 upsert(엔드포인트 바뀜 대응, research 3-1), 없으면 설정 화면 배너
```

**② 스케줄 (SQL, `20261022000300_push_scheduler.sql`)** — research 4-2 방식 A(매분 체크)
```sql
create extension if not exists pg_cron;
create extension if not exists pg_net;
create schema if not exists app;

-- Vault에 비밀 저장 (값은 대시보드/CLI로 넣고, 마이그레이션 파일에는 넣지 않는다)
--   select vault.create_secret('https://<app>.vercel.app/api/push/dispatch', 'push_dispatch_url');
--   select vault.create_secret('<랜덤 32바이트>', 'cron_secret');

create function app.dispatch_due_pushes() returns void
language plpgsql security definer set search_path = '' as $$
declare
  s record; k text; due time; local_now timestamp; svc date;
  v_url text := (select decrypted_secret from vault.decrypted_secrets where name = 'push_dispatch_url');
  v_secret text := (select decrypted_secret from vault.decrypted_secrets where name = 'cron_secret');
begin
  for s in select * from public.settings loop
    local_now := now() at time zone s.time_zone;
    svc := (local_now - make_interval(hours => s.day_start_hour))::date;
    foreach k in array array['morning', 'evening'] loop
      due := case k when 'morning' then s.morning_push_time else s.evening_push_time end;
      -- 예정 시각 ~ +30분 사이에만 (DB가 잠깐 멈췄다 돌아와도 늦은 알림 1번은 보냄, 그 이후는 버림)
      if local_now::time >= due and local_now::time < due + interval '30 minutes' then
        insert into public.push_log (user_id, kind, service_date, status)
        values (s.user_id, k, svc, 'claimed')
        on conflict (user_id, kind, service_date) do nothing;
        if found then
          perform net.http_post(
            url := v_url,
            headers := jsonb_build_object('Content-Type', 'application/json', 'x-cron-secret', v_secret),
            body := jsonb_build_object('userId', s.user_id, 'kind', k, 'serviceDate', svc),
            timeout_milliseconds := 10000
          );
        end if;
      end if;
    end loop;
  end loop;
end $$;

select cron.schedule('dispatch-due-pushes', '* * * * *', $$select app.dispatch_due_pushes()$$);
-- 매분 실행 로그 정리 (research 4-2 단점 대응)
select cron.schedule('purge-cron-history', '17 18 * * *',
  $$delete from cron.job_run_details where end_time < now() - interval '3 days'$$);
```
- 시간 비교를 DB에서 **로컬 시각(KST)** 으로 하므로 UTC 변환 실수가 없다. cron 식 자체는 `* * * * *`라 시간대와 무관.
- `push_log`의 unique 키로 **하루 1번만** 보낸다(매분 실행이어도 중복 없음).

**③ 발송 함수** `api/push/dispatch.ts` — "보낼지/무슨 내용으로"는 TS 도메인 함수가 결정(학습일 규칙을 한 곳에만 둠)
```ts
import type { VercelRequest, VercelResponse } from '@vercel/node';
import { timingSafeEqual } from 'node:crypto';
import { createClient } from '@supabase/supabase-js';
import { pushService } from '../../src/services';

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const got = Buffer.from(String(req.headers['x-cron-secret'] ?? ''));
  const want = Buffer.from(process.env.CRON_SECRET!);
  if (req.method !== 'POST' || got.length !== want.length || !timingSafeEqual(got, want)) return res.status(401).end();

  const { userId, kind, serviceDate } = req.body as { userId: string; kind: 'morning' | 'evening'; serviceDate: string };
  const admin = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!);
  const outcome = await pushService.dispatchScheduled(admin, { userId, kind, serviceDate, now: new Date() });
  return res.json(outcome); // { sent, skipped?: 'already_done' | 'nothing_pending', gone: n }
}
```
`pushService.dispatchScheduled()`(서버 경로) 내용:
1. 저장소에서 학습일·퀴즈·진행 중 세션 읽기 → `decideEveningPush()` / 아침은 "오늘 이미 완료면 skip"
2. 메시지 만들기: 아침 `"오늘의 표현 {N}개"`(N = `planStudyDay()`), 저녁 `"퀴즈 시간 · {문항 수}문항"` 또는 `"오늘 아침 학습을 아직 안 했어요"`
3. `web-push`로 활성 구독 전체에 발송: `webpush.sendNotification(sub, payload, { TTL: 3 * 3600, urgency: 'high' })`
4. 응답 404/410 → 구독 `status = 'gone'`(research 3-1), 성공 → `last_success_at` 갱신, `push_log.status` 갱신

**④ 서비스 워커** `public/sw.js` (발췌)
```js
self.addEventListener('push', (event) => {
  const data = event.data?.json() ?? { title: '영어 회화', body: '', url: '/' };
  // ★ 모든 푸시는 반드시 알림을 띄운다 (안 띄우면 구독 취소 위험: research 3)
  event.waitUntil(self.registration.showNotification(data.title, { body: data.body, data: { url: data.url }, tag: data.tag }));
});
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url ?? '/';
  event.waitUntil((async () => {
    const wins = await clients.matchAll({ type: 'window', includeUncontrolled: true });
    if (wins[0]) { await wins[0].focus(); wins[0].postMessage({ type: 'navigate', url }); }
    else await clients.openWindow(url);
  })());
});
```

**대안 코드 — 고정 cron 2개 (research 4-2 방식 B)**
```sql
select cron.schedule('push-morning', '0 22 * * *', $$select app.send_push('morning')$$); -- 07:00 KST
select cron.schedule('push-evening', '0 11 * * *', $$select app.send_push('evening')$$); -- 20:00 KST
-- 설정에서 시각 변경 시: cron.alter_job(job_id, schedule := '<UTC로 변환한 식>')
```
| | 채택: 매분 체크 | 대안: 고정 2개 |
|---|---|---|
| 시각 변경 | `settings`만 바꾸면 끝 | UTC 변환 + `cron.alter_job` 권한 필요 |
| 놓친 실행 | 30분 창 안에서 자동 복구 | 복구 없음 |
| 부하 | 하루 1,440회 아주 가벼운 쿼리 + 로그 정리 작업 | 하루 2회 |

**⑤ keep-alive** `vercel.json`
```json
{
  "rewrites": [{ "source": "/((?!api/).*)", "destination": "/index.html" }],
  "crons": [{ "path": "/api/keepalive", "schedule": "0 3 * * *" }]
}
```
`api/keepalive.ts`: `Authorization: Bearer ${CRON_SECRET}` 확인(Vercel이 cron 호출에 자동으로 붙이는 헤더 — 구현 시 Vercel 문서로 재확인) → Supabase REST로 `settings` 1행 select.

### 4-11. 사용량 카운터와 예산 단계

`src/domain/usageBudget.ts`
```ts
export type SttMode = 'normal' | 'save_drills' | 'quiz_only' | 'self_check';
export function sttMode(sttSecondsThisMonth: number, cfg: { monthlyLimitSec: number; saveAt: number; quizOnlyAt: number }): SttMode {
  const r = sttSecondsThisMonth / cfg.monthlyLimitSec;
  if (r >= 1) return 'self_check';          // Azure 거부 → 정답 공개 후 스스로 O/X
  if (r >= cfg.quizOnlyAt) return 'quiz_only';   // 0.95
  if (r >= cfg.saveAt) return 'save_drills';     // 0.80: 아침 drill은 녹음+A/B만
  return 'normal';
}
```
- `usage_monthly`는 RPC `increment_usage(p_tts_chars, p_stt_seconds)`로만 증가(동시 갱신 안전). 달 키 = KST 기준 그달 1일.
- ⚠️ 앱 카운터는 **추정치**(내가 보낸 PCM 길이). 실제 Azure 집계는 Azure 포털 "Metrics"에서 확인 → 설정 화면에 포털 링크.

---

## 5. 화면 목록과 흐름

### 5-1. 첫 실행
```
[A] 설치 안내 (standalone이 아니면 이 화면만 보임)
    "Safari 공유 → 홈 화면에 추가 → '웹 앱으로 열기' 켜기 → 홈 화면 아이콘으로 열기" (그림 3장)
      ↓ (standalone으로 열림)
[B] 로그인 (이메일 + 비밀번호)
[C] 알림 허용 — [알림 켜기] 버튼 탭 → requestPermission + subscribe (제스처 안)
[D] 하루 학습 시간 고르기 — 10/15/20/30/40분 (나중에 설정에서 변경)
[E] 마이크 테스트 — 한 문장 말해보기 (권한 팝업을 여기서 미리 + 녹음 정상 확인)
[F] 레벨 테스트 → [G] 결과 → level_changes 기록(reason='level_test') → 홈
```
### 5-2. 홈
- 오늘 상태 카드: "아침: 표현 N개 (예상 약 M분)" / "저녁 퀴즈: K문항 · 대기 중/완료/없음"
- Day N 표시, 이번 달 연속 학습일
- 대기 중인 어제 퀴즈 배너(research 9-1 #2)

### 5-3. 아침 (표현 1개당 반복, `plan`에 따라 단계 on/off)
| 단계 | 화면 | 예상 시간(초급 기준) |
|---|---|---|
| ① 소리 먼저 | 음성 자동 재생(시작 버튼 탭) · 텍스트 가림 · 탭1=영어 탭2=한국어+언제 쓰는지 · 0.75×/1× | 25초 |
| ② 따라 말하기 | 원어민 → [말하기] → 단어 하이라이트 · 원어민/내 녹음/A·B · [발음 점수 보기] · 실패 시 build-up 단계로(plan.buildUp='always'면 항상) | 20초 |
| ③ 패턴 연습 | 파생 2~3개: cue 음성 → 내 대사 말하기 → 피드백 (대치/변형 라벨 표시) | 40초 |
| ④ 대화 | A 음성 자동 → 내 차례 표시 → 말하기 → 다음 턴. 오늘 역할 교대 대상이면 끝나고 역할 바꿔 한 번 더 | 28초 (+교대 30초) |
| 완료 | "Day N 완료" → `complete_morning_session` RPC → 학습일 확정 | — |

### 5-4. 저녁 퀴즈
```
[퀴즈 시작] (탭 = 첫 cue 자동 재생 허용)
 → 문항: "1일 전 · 3/9" · 텍스트 가림 · cue 재생 · [말하기]
     통과 → 다음 (다음 버튼 탭 = 다음 cue 재생)
     실패 → [다시 말하기] (최대 2회, 설정값) → 그래도 실패 → 정답 공개 + 원어민 + 내 녹음 A/B
 → 결과: 섹션별(1·3·7일 전) 첫 시도 통과율, 틀린 문장 목록 다시 듣기, "아직 없음" 섹션 표시
 → 승급 평가 → (승급 시) 축하 화면 + "다음 학습일부터 중급"
```
### 5-5. 레벨 테스트
```
안내(약 10분, 15문항) → 1단계 6문항 → (자동 분기) → 2단계 9문항 → 결과
 - repeat: 1회 재생 → 1.5초 → 삐 → 말하기 (다시 듣기 없음)
 - choose_response: cue 재생 → 선택지 3개 각각 [듣기] → 고르기
 - situation_speak: 한국어 상황 + cue 재생 → 말하기
결과: 판정 레벨 · 유형별 점수 · 틀린 문장 다시 듣기 · 이전 테스트 비교 · [이 레벨로 시작]
```
### 5-6. 설정
- 알림 시각 2개(05:00~23:00), 저녁 리마인더 on/off
- **하루 학습 시간** (10/15/20/30/40분) + 레벨별 예상 표현 수 미리보기 + 최근 7일 실제 평균
- 레벨: 현재 레벨, 레벨 변경 이력, [레벨 테스트 다시 보기]
- 이번 달 사용량: TTS 글자 / 500,000, STT 분 / 300분, 현재 모드(정상/절약/퀴즈만/자가확인), Azure 포털 링크
- 알림 상태: 구독 활성/만료 + [알림 다시 켜기]

---

## 6. 고려사항과 트레이드오프

### 6-1. 사용량 (Q2·Q3 반영 재계산)
학습 시간이 사용량을 결정한다(아래는 어림값, 실제 기록으로 보정). research 11-2의 발화당 과금 초(VAD 적용: 초급 2.7 / 중급 4.1 / 고급 5.9초), 발음 평가는 같은 요청이라 추가 0:

| 학습 시간 | 레벨 | N | 아침 발화/일 | 퀴즈 발화/일 | **월 STT(30일)** | 5시간 대비 |
|---|---|---|---|---|---|---|
| 10분 | 고급 | 1 | 11 | 4 | 0.75h | 15% |
| 20분 | 초급 | 5 | 46 | 21 | 1.6h | 32% |
| 20분 | 고급 | 3 | 34 | 13 | 2.6h | 52% |
| 30분 | 고급 | 5 | 60+ | 21 | 4.3h | **86%** ⚠️ |
| 40분 | 고급 | 5 | 70+ | 21 | 4.9h | **98%** ❌ |

→ **30분 이상 + 고급**이면 월말에 절약 모드로 넘어갈 수 있다. 설정 화면에서 학습 시간을 고를 때 **"이 설정이면 월 STT 예상 약 X시간"** 을 같이 보여준다(`planStudyDay` + 발화 수 계산 재사용).

### 6-2. 결정 요약표

| 결정 | 채택 | 대안 | 바꾸려면 |
|---|---|---|---|
| 프런트 | Vite+React SPA | Next.js | 서버 렌더링 필요 없음. Next는 기능 대비 무거움 |
| 콘텐츠 위치 | `public/content` 정적 JSON | Supabase 테이블 | 콘텐츠는 "코드처럼" 검수·버전 관리하는 게 맞음(git diff로 리뷰). DB로 옮기려면 `contentRepo`만 교체 |
| 음성 파일 | Supabase Storage | `public/audio` | §4-6 |
| 학습일 확정 | DB 함수(서버 시각) | 클라이언트 계산 | §3-3 |
| 퀴즈 생성 시점 | 처음 열 때 + 고정 저장 | 아침 완료 시 | §4-1 |
| STT 파이프라인 | PCM push stream | SDK 마이크 직접 | §4-8 |
| 스케줄 | 매분 체크 | 고정 2개 | §4-10 |
| 토큰 보호 | 세션 JWT | 비밀값 헤더 | §4-7 |
| 로그인 | 이메일+비밀번호 | 매직 링크 | 매직 링크는 Safari로 열려 홈 화면 앱 세션과 분리됨 |
| 서비스 워커 | 직접 작성 `public/sw.js` | `vite-plugin-pwa`(injectManifest) | 아래 6-3 |

### 6-3. 서비스 워커: 직접 작성 vs `vite-plugin-pwa`
```ts
// 대안: vite.config.ts
import { VitePWA } from 'vite-plugin-pwa';
export default defineConfig({ plugins: [react(), VitePWA({ strategies: 'injectManifest', srcDir: 'src', filename: 'sw.ts' })] });
```
| | 직접 작성(채택) | vite-plugin-pwa |
|---|---|---|
| 장점 | 푸시 처리 코드가 한 파일에 다 보임, 의존성 0 | 빌드 파일 자동 프리캐시, 업데이트 알림 UI 도우미 |
| 단점 | 앱 셸 캐시를 직접 관리 | 2.0.0이 2026-10-03 출시(새 메이저) — 안정화 전 |
| 결론 | 이 앱은 "온라인 전제 + 음성 캐시"만 필요 → 직접 작성 | 오프라인 전체 지원이 필요해지면 전환 |

### 6-4. 위험 목록
| 위험 | 가능성 | 대응 |
|---|---|---|
| iOS에서 AudioWorklet 녹음 품질 문제 | 중 | T5 실기기 확인, 실패 시 `ScriptProcessorNode`(구식이지만 동작) 대체 — `pcmRecorder.ts` 안에서만 교체 |
| `preservesPitch`/`playbackRate` 미동작 | 낮음~중 | T4, Web Audio 대체 |
| F0에서 발음 평가 불가 | 낮음 | T6, 실패 시 `referenceText=null`로 STT만(점수 영역 숨김) |
| 푸시 구독 조용히 만료 | 중 | 앱 실행 시 재확인 + 410 처리 + 설정 배너 |
| Supabase 일시정지 | 낮음 | keep-alive cron |
| 콘텐츠 품질(교과서식 문장) | 중 | 표현마다 `source_check` ≥1 + 검사 스크립트 + 사용자 샘플 검수(§7 단계 4) |
| 서비스 날짜 규칙 TS/SQL 불일치 | 낮음 | 같은 입력 비교 테스트 |

---

## 7. 구현 순서 (작게 쪼갠 단계 + 확인 방법)

> 각 단계 시작 전에 **바꿀 파일 목록·이유·대안·장단점**을 먼저 보여주고 진행한다(작업 원칙).

| # | 단계 | 만들 것 | 어떻게 확인하나 |
|---|---|---|---|
| 0 | 저장소·뼈대 | 새 저장소, Vite/TS/Vitest/ESLint 설정, 계층 import 규칙, `docs/`로 md 이동 | `npm run lint && npm run typecheck && npm test && npm run build` 통과. `screens/`에서 supabase import 시 lint 에러 나는지 일부러 확인 |
| 1 | **실기기 스파이크** | `/spike` 페이지 1장(녹음→Azure 인식+발음 평가, 0.75× 재생, 푸시 구독), 임시 토큰 함수, Vercel 배포 | research 14장 T1~T9 결과를 `docs/device-spike-results.md`에 기록. **결과에 따라 계획 수정이 필요하면 여기서 멈추고 보고** |
| 2 | 도메인 함수 | `domain/*` 9개 + 테스트 | `npm test` — 학습일(경계 03:59/04:00, Day1~8 섹션 수), 퀴즈(결정성, 중복 회피, 상한 배분), 정규화(축약·숫자·시간·필러), diff(대치/누락/삽입/동치), 레벨 판정(경계값), 승급(창 리셋·표본 부족·쿨다운), 학습량(표 1-3 재현) |
| 3 | Supabase | 프로젝트 생성(사용자), 마이그레이션 3개, Auth 가입 차단, Vault 비밀 | `supabase db push` 후: ① 로그인 안 한 anon 키로 select → 0행/권한 에러 ② 내 계정으로 CRUD 성공 ③ `complete_morning_session` 두 번 호출 → 두 번째 실패 ④ SQL 서비스 날짜 = TS `serviceDateOf` (같은 시각 5개) |
| 4 | 콘텐츠 도구 + 샘플 | zod 스키마, validate, check-duplicates, build-index, **레벨별 샘플 팩 1개 + 레벨 테스트 set-a 일부** | 스크립트가 고의 오류(중복 표현, 턴 수 위반, build-up 순서 위반)를 잡는지. **사용자가 샘플 품질 검수** → 승인 후 대량 생성 |
| 5 | TTS 스크립트 | `generate-audio.ts` | 샘플 팩 생성 → 두 번째 실행 시 "새로 생성 0"(캐시) · `--dry-run` 글자 수 = 실제 과금 글자 수 · 사용량 표에 기록 |
| 6 | 인증·설정 | 로그인 화면, 설정 저장, `planStudyDay` 미리보기 | 아이폰 홈 화면 앱에서 로그인 유지(앱 종료 후 재실행) |
| 7 | 오디오 서비스 | micStream, pcmRecorder, wav, player, A/B 컴포넌트 | 아이폰: 녹음→재생, A/B, 0.75×, 권한 팝업 횟수 기록 |
| 8 | 음성 인식 | 토큰 함수(JWT), tokenClient, azureRecognizer, attemptService | 아이폰: 문장 말하기 → 하이라이트 + 발음 점수, 로그아웃 상태 토큰 요청 401, `attempts`·`usage_monthly` 증가 |
| 9 | 아침 흐름 | morningService, 화면 ①~④, 완료 | 샘플 팩으로 끝까지 1회 → Day 1 생성, 중간 이탈 후 이어하기, 같은 날 두 번째 완료 차단 |
| 10 | 저녁 퀴즈 | quizService, 화면, 미응시 처리 | 테스트용 날짜 주입(개발 모드)으로 Day 1~8 시뮬레이션 → 문항 수 0/3N 확인, 재시도 2회 후 정답 공개 |
| 11 | 레벨 테스트 | levelTestService, 화면, 결과 비교 | 두 경로(초급/고급 블록) 각각 응시, 세트 교대 확인 |
| 12 | 푸시 | sw.js, 구독, dispatch 함수, pg_cron | 알림 시각을 2분 뒤로 설정 → ±1분 도착(T7), 앱 종료 상태 수신·탭 이동(T8), 같은 날 중복 없음, 410 처리(구독 삭제 후 발송) |
| 13 | 승급·사용량·예산 모드 | levelService.afterQuizCompleted, 설정 화면 사용량 | 단위 테스트 + 개발 모드에서 통과율 데이터 주입 → 승급 알림 / 사용량 80% 주입 → 절약 모드 전환 |
| 14 | keep-alive | `api/keepalive.ts`, `vercel.json` crons | Vercel 대시보드 cron 실행 로그 + Supabase 로그 |
| 15 | 콘텐츠 대량 생성 | 현재+다음 레벨 30팩, 레벨 테스트 2세트 완성 | validate·중복 검사 통과, 각 표현 `source_check` URL 실재, TTS `--dry-run`이 한도 안 |
| 16 | 완료 기준 점검 | 프롬프트 §6 체크리스트 | 아이폰에서 항목별 확인 결과를 `docs/acceptance.md`에 기록, 클라이언트 번들에 `AZURE_SPEECH_KEY`·VAPID 개인키·service role 키 문자열이 없는지 `grep`으로 확인 |

**환경변수 (`.env.example`)**
| 이름 | 위치 | 공개 여부 |
|---|---|---|
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_VAPID_PUBLIC_KEY`, `VITE_AUDIO_BASE_URL` | 클라이언트 | 공개 가능(RLS로 보호) |
| `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` | Vercel / 로컬 `.env.local` | **비밀** |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `OWNER_USER_ID` | Vercel / 로컬 | service role은 **비밀** |
| `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` | Vercel | **비밀** |
| `CRON_SECRET` | Vercel + Supabase Vault | **비밀** |

**사용자가 직접 해야 하는 일** (내가 할 수 없음): Azure F0 리소스 생성, Supabase 프로젝트 생성, Vercel 연결, 비밀값 입력, 아이폰 실기기 테스트.

---

## 8. 확장 아이디어 (구현하지 않음, 제안만)

1. **틀린 문장 다음 날 재출제** — 퀴즈에서 최종 실패한 쌍을 다음 학습일 퀴즈 맨 앞에 1회 추가(상한 별도).
2. **저녁 퀴즈에 그날 아침 문장 추가** — "0학습일 전" 섹션(offset 0)을 설정으로 켜기. `QUIZ_OFFSETS`에 0 추가만으로 동작하게 설계됨.
3. **학습 시간 자동 보정** — 최근 7일 실제 소요 시간으로 `StudyCostTable` 상수를 개인화.
4. **표현 수 직접 지정** — 학습 시간 대신 "하루 N개" 모드.
5. **음소 단위 발음 피드백** — `granularity = Phoneme`으로 틀린 소리 표시(응답 크기·화면 복잡도 증가).
6. **Declarative Web Push** — iOS 18.4+에서 서비스 워커 없이도 표시되는 푸시(research 3). 사례가 늘면 안정성 개선용으로 검토.
7. **기기 내 Whisper(WebGPU)** — iOS 26 WebGPU로 아침 drill STT를 기기 안에서 처리해 Azure 사용량 절감(속도 실측 필요).
8. **"나" 음성 선택** — 설정에서 남/여 선택(바꾸면 "나" 문장 TTS 재생성 필요 → 글자 수 미리 보여주기).
9. **연속 학습 기록·주간 리포트 푸시**.

---

*계획 단계 종료. §0(저장소 위치)과 함께 승인해 주면 구현 0단계부터 시작한다.*
