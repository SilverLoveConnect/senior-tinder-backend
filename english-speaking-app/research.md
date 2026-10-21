# research.md — 영어회화 앱 (청화식 · 개인용) 0단계 리서치

- 작성일 / 출처 확인일: **2026-10-21** (모든 출처의 "확인 날짜"는 이 날짜)
- 입력 문서: `english-speaking-app-prompt.md` (v2)
- 상태: **리서치 완료 → 사용자 확인 대기** (plan.md는 승인 후 작성)

---

## 0. 이 문서를 읽기 전에 — 확인 방법과 한계

### 0-1. 출처를 어떻게 확인했나
- 이 작업 환경(클라우드 컨테이너)의 네트워크 정책 때문에 **공식 문서 페이지를 직접 열 수 없었다** (`vercel.com`, `learn.microsoft.com`, `supabase.com` 직접 접속 시 `403 / ENOTFOUND`).
- 그래서 모든 사실은 **웹 검색 엔진 결과(공식 문서 페이지의 발췌 포함)** 로 확인했다. 각 항목에 신뢰도를 붙였다.

| 표시 | 의미 |
|---|---|
| ✅ 공식 | 공식 문서(벤더 docs / changelog / WebKit 블로그 / 논문)의 문장을 검색 결과로 확인 |
| 🟡 2차 | 벤더 문서가 아닌 블로그·포럼·서드파티 정리. 여러 출처가 일치하면 표시 |
| ⚠️ 실기기 | 문서로 확정이 안 됨. **사용자 아이폰에서 직접 테스트해야 확정** (14장 체크리스트) |

### 0-2. 리서치로 바뀐 것 — 프롬프트 v2의 기본값과 다른 결론 (중요도 순)

| # | 프롬프트의 가정 | 리서치 결과 | 영향 |
|---|---|---|---|
| **1** | 마이크 인식 1순위 = 브라우저 내장 `webkitSpeechRecognition` | **아이폰 홈 화면 웹앱(standalone)에서는 공식 지원이 아니다.** WebKit 버그 225298에서 WebKit 측이 "홈 화면 웹앱에서는 SpeechRecognition API를 쓸 수 없다"고 답했고, 상태는 `RESOLVED LATER`(나중에)이지 "고쳐짐"이 아님. 2026년 8~9월에도 "마이크 표시는 켜지는데 `onresult`가 안 온다"는 보고(버그 321436)가 있다. | 푸시 알림은 **홈 화면 앱에서만** 되므로, 앱은 반드시 standalone으로 쓴다 → **내장 STT를 1순위로 설계하면 안 된다.** Azure STT를 1순위로 올리고, 내장 STT는 "실기기 테스트에서 되면 쓰는 보너스"로 내린다. (2-1, 11장) |
| **2** | Azure STT는 대안 | Azure를 모든 말하기에 쓰면 **월 2.3시간(초급) ~ 5.0시간(고급)** 으로 계산됨. 무료 한도는 **월 5시간**. 고급 레벨에서는 한도에 닿는다. | 사용량 절약 설계(버튼식 녹음, 녹음 버퍼 재사용, 발음 채점을 인식 요청에 합치기, 예산 80% 넘으면 "자가 확인 모드")가 필수. (11장) |
| **3** | 아침 12분 / 저녁 8분 | 프롬프트대로(표현마다 backward build-up 전체 + 대화 역할 교대 매번) 하면 **아침만 초급 16분, 고급 25분**. | 아침 흐름을 줄여야 한다: build-up은 "처음 말하기 실패 시에만", 역할 교대는 "하루 1개 대화만". 그래도 고급은 약 17분. (10장) |
| **4** | 토큰 함수·푸시 함수를 "비밀값(환경변수)"으로 보호 | **토큰 함수는 브라우저가 호출한다.** 클라이언트 번들에 넣은 비밀값은 누구나 볼 수 있어 보호가 안 된다. | 토큰 함수는 **Supabase 로그인 세션(JWT) 검증 + 내 user id 일치 확인**으로 보호. 비밀값 헤더 방식은 서버↔서버(pg_cron→푸시 함수)에만 쓴다. (5-4) |
| **5** | Supabase 무료 = 매일 쓰면 문제 없음 | 매일 쓰면 문제없다. 단, **7일 넘게 안 쓰면 프로젝트가 일시정지 → pg_cron도 멈춤 → 알림도 끊김.** 알림이 끊기면 다시 돌아올 계기도 없어진다. | 외부 keep-alive 1개 필요. Vercel 무료 cron(하루 1회, 시각 부정확)이 **이 용도에는 딱 맞다.** (4-3) |
| **6** | (언급 없음) | Supabase가 **2026-05-30 이후 생성된 새 프로젝트**는 `public` 스키마 새 테이블이 Data API에 자동 노출되지 않는다. **명시적 `GRANT`가 필요.** (기존 프로젝트는 2026-10-30 강제 적용) | 마이그레이션 파일마다 `GRANT` + RLS 정책을 같이 넣어야 한다. 안 그러면 `42501` 에러. (4-5) |
| **7** | 0.75배속은 `playbackRate` | 방향은 맞다. 단 Apple의 옛 문서에 "iOS에서 playbackRate 미지원"이라는 문장이 남아 있다(오래된 문서로 보임). | ⚠️ 실기기 확인 항목에 추가. 안 되면 대안은 Web Audio `AudioBufferSourceNode.playbackRate`. (2-3) |

---

## 1. 청화식 교수법 (Audio-Lingual Method)

### 1-1. 핵심 원리 (출처: 교재 강의노트, Richards & Rodgers 계열 정리 🟡)
- 행동주의 학습 이론 기반: **듣기 → 모방 → 반복 → 강화(즉시 피드백) → 습관 형성**.
- 대화(dialogue)로 수업을 시작하고, 대화 속 문장 패턴을 drill로 연습한다.
- 문법은 **설명하지 않고 예문에서 귀납적으로** 익히게 한다.
- 원어민 수준의 발음·억양을 목표로, 오류는 즉시 교정한다.
- "Michigan Method"라는 별칭도 있다.

### 1-2. Drill 종류별 정의와 순서

| Drill | 정의 (원문 요지) | 이 앱에서의 형태 | 화면 |
|---|---|---|---|
| **Repetition (반복)** | 교사의 모델을 "가능한 정확하고 빠르게" 따라 한다. 대화 문장을 가르칠 때 주로 쓴다. | 원어민 음성 → 내 발화 → 단어 하이라이트 + A/B 비교 | 아침 ①② |
| **Backward build-up (확장)** | 긴 문장이 어려울 때 문장을 덩어리로 나누고, **맨 끝 덩어리부터** 따라 하면서 앞 덩어리를 하나씩 붙여 전체 문장까지 간다. 끝에서 시작하는 이유: **문장 끝 억양이 자연스럽게 유지되고, 새 정보가 보통 문장 끝에 있기 때문.** | `a bit late` → `running a bit late` → `Sorry, I'm running a bit late.` | 아침 ② (처음 시도 실패 시) |
| **Single-slot substitution (단일 대치)** | 문장 하나 + 단서 단어 → 단서를 맞는 자리에 넣어 말한다. 목적: 문장의 "빈칸(slot)"을 찾아 채우는 연습. | 파생 문장 중 `type: substitution` | 아침 ③ |
| **Multiple-slot substitution (다중 대치)** | 단서가 여러 자리 중 하나에 들어간다. 학습자가 품사를 판단해야 한다. | 중·고급 파생 문장에서 선택 사용 | 아침 ③ |
| **Transformation (변형)** | 긍정↔부정, 평서문↔의문문, 능동↔수동, 현재↔과거로 바꿔 말한다. | 파생 문장 중 `type: transformation` | 아침 ③ |
| **Question-and-answer** | 질문에 빠르게 답한다. | 모든 파생 문장이 "상대 cue → 내 대답" 쌍 = 사실상 Q&A drill | 아침 ③, 저녁 퀴즈 |
| **Chain drill** | 학생들이 차례로 묻고 답하며 교실을 한 바퀴 돈다. | **1인 앱이라 해당 없음.** 대화 역할 교대로 대체 | — |
| **Dialogue memorization (대화 암기)** | 짧은 2인 대화를 모방으로 외운다. 학생이 한 역할, 교사가 다른 역할을 맡고, **다 외우면 역할을 바꾼다.** | A=원어민 음성, B=나 → 역할 교대 | 아침 ④ |

### 1-3. 교과서적인 수업 순서 → 앱 화면 대응

```
[교과서 순서]
 대화 듣기 → 대화 문장 반복(+backward build-up) → 대화 암기(역할 교대)
 → 대화 속 패턴으로 대치·변형 drill → 즉시 피드백

[이 앱의 아침 흐름(제안)]
 ① 소리 먼저: 핵심 표현 음성 (텍스트 가림, 탭 1번=영어, 탭 2번=한국어)
 ② 따라 말하기: 핵심 표현 repetition (실패하면 backward build-up 자동 진입)
 ③ 패턴 연습: 파생 3개 (cue 듣기 → 내 대사 말하기) = 대치·변형·Q&A
 ④ 대화: 그 표현이 들어간 대화를 B 역할로 (하루 1개 대화는 역할 교대)
```

- 교과서는 "대화 → drill" 순서지만, 이 앱은 **표현 1개 단위**로 "표현 → drill → 대화"로 묶는다. 이유: 표현 5개를 하루에 다루므로, 대화를 먼저 보면 아직 안 배운 표현이 섞여 인지 부담이 커진다. 대화를 마지막에 두면 "배운 걸 실제 맥락에서 써보는" 정리 단계가 된다.
- 버린 대안: 5개 대화를 먼저 다 듣고 drill을 몰아서 하기 → 한 화면 흐름이 길어지고 "오늘 어디까지 했는지" 끊기 어렵다.

### 1-4. 청화식의 한계와 앱에서의 보완 (트레이드오프)
- 청화식은 의미 없는 기계적 반복이라는 비판이 있다(1960년대 이후 의사소통 중심 교수법이 등장한 배경). → 이 앱은 **모든 단위를 "상대 대사 → 내 대사" 쌍**으로 만들어 의미 맥락을 붙였다(프롬프트 1-4 요구사항). 이 점은 청화식 원형보다 좋은 선택이다.
- 문법 설명 최소화 → `when_to_use` 한 줄과 자연스러운 한국어 뜻만 제공.

---

## 2. 아이폰 Safari / 홈 화면 웹앱 (PWA standalone)

### 2-1. `webkitSpeechRecognition` (내장 음성인식)

| 항목 | 결과 | 신뢰도 |
|---|---|---|
| Safari **탭**에서 동작 | iOS 14.5+에서 `webkitSpeechRecognition` 접두사로 사용 가능. **네트워크 연결 필요**(Siri 서버 사용). | 🟡 (여러 튜토리얼 일치) |
| **홈 화면 웹앱(standalone)**에서 동작 | WebKit 버그 225298: WebKit 측 답변 "SpeechRecognition API is not available in SafariViewController and web apps added to Home Screen for now". 상태 `RESOLVED LATER`. Apple 개발자 포럼에도 "Safari에선 되는데 홈 화면에 추가하면 안 된다"는 보고. 2026년 8~9월 WebKit 버그 321436: standalone에서 마이크 표시는 켜지지만 `onresult`가 오지 않음. 반대로 "내 앱에선 됐다"는 개발자 보고도 있음. | ✅ 공식 버그 트래커 + ⚠️ 실기기 |
| `lang = 'en-US'` | 설정 가능(표준 속성). | 🟡 |
| 침묵 시 자동 종료 | `continuous = false`이면 한 발화 후 종료가 표준 동작. iOS에서는 `start`/`audiostart` 이후 결과가 "몇 초 또는 영원히" 안 오는 경우가 보고됨 → 개발자들은 **750ms 정도 중간 결과가 없으면 직접 `stop()`** 하는 우회책을 씀. | 🟡 |
| 중간 결과(`interimResults`) | Apple 포럼: iOS에서 `interimResults = true`가 기대대로 안 될 때가 있고, 느려지면서 `isFinal=true`로 바로 넘어가 클라우드 인식으로 바뀐다고 보고. **`continuous = true`는 `onresult`가 안 오는 멈춤 현상**이 보고됨. | 🟡 |
| Safari 26 변경 | "SpeechRecognition 인터페이스를 secure context(HTTPS)에서만 노출" 수정(151240414). 홈 화면 지원 여부와는 무관. | ✅ WebKit 블로그 |
| 다른 오디오와 충돌 | HTML `<audio>` 요소가 오디오 세션을 잡고 있으면 인식이 "켜진 것처럼 보이지만 소리를 못 받는" 상태가 된다는 보고. 이 앱은 원어민 음성 재생 직후 인식을 시작하므로 **정확히 이 패턴에 해당.** | 🟡 (1개월 된 서드파티 글, 단서 수준) |

**결론**
- 이 앱은 푸시 알림 때문에 **반드시 홈 화면 웹앱으로 쓴다.** 그런데 그 모드에서 내장 STT는 "공식적으로 지원 안 됨 + 동작 보고가 엇갈림"이다.
- → **설계 기본값: Azure STT(Speech SDK, 브라우저)를 1순위.** 내장 STT는 `STT_ENGINE` 설정값으로 남겨두고, 14장 실기기 테스트에서 사용자 iOS 버전에서 안정적으로 되면 아침 따라 말하기에 한해 켠다(Azure 사용량 절약용).
- 또 다른 대안: 기기 안에서 도는 Whisper(transformers.js / whisper.cpp WASM). Safari 26부터 WebGPU가 iOS에서 기본 활성화(✅ WebKit 블로그)라 이론상 가능하지만, **아이폰 Safari에서의 속도 벤치마크를 찾지 못했다.** 모델 다운로드 수십 MB. → plan.md에서 "확장 아이디어"로만 둔다.

### 2-2. 마이크 권한 팝업

| 항목 | 결과 | 신뢰도 |
|---|---|---|
| standalone에서 매번 뜨는가 | 개발자 보고: "PWA에는 마이크 권한 설정이 따로 없어서 **앱을 열거나 다시 포커스할 때마다** 다시 묻는다." 네이티브 앱의 '항상 허용'이 없다. | 🟡 (여러 보고 일치, 2020~2023년 위주) |
| 페이지 이동 시 | WebKit 버그 215884: standalone에서 **hash가 바뀔 때마다** 카메라/마이크 권한을 다시 물음. Safari 탭에서는 유지. 우회: 라우터를 hash 방식이 아닌 방식으로. (이후 "configuration changed"로 종결) | ✅ 공식 버그 트래커 |
| Apple 공식 설명 | 홈 화면 앱의 권한 유지 정책에 대한 Apple 공식 문서를 찾지 못함. | ⚠️ 실기기 |

**줄이는 방법 (설계 반영)**
1. **SPA 1페이지 구조 + hash 라우팅 금지** (`history.pushState` 기반 또는 상태 기반 화면 전환). 전체 페이지 새로고침 금지.
2. `getUserMedia`는 **세션당 1번만** 호출하고 `MediaStream`을 앱 전역(오디오 서비스 계층)에 보관해 재사용한다. 화면마다 새로 요청하지 않는다.
3. Azure SDK에 마이크를 직접 넘기지 않는다(`fromDefaultMicrophoneInput`는 SDK가 자체 `getUserMedia`를 호출 → 내 녹음용 스트림과 이중 요청 가능). 대신 **내 스트림 → PCM → Azure push stream** 구조로 1개 스트림만 쓴다(5-3).
4. 트레이드오프: 앱이 백그라운드로 가면(`visibilitychange: hidden`) 마이크 표시등을 끄려면 트랙을 멈춰야 하는데, 멈추면 다시 돌아올 때 팝업이 또 뜰 수 있다. → 기본값: **백그라운드 전환 시 트랙 정지**(프라이버시 우선), 설정으로 바꿀 수 있게.
5. 결과: 하루 2번(아침/저녁) 앱을 열 때 **각 1회 팝업**은 감수해야 할 가능성이 높다. ⚠️ 14장에서 확인.

### 2-3. 오디오 자동재생 제한

| 항목 | 결과 | 신뢰도 |
|---|---|---|
| 사용자 터치 필요 여부 | iOS Safari는 `<audio>`/`<video>`의 소리 있는 재생에 **사용자 제스처가 필요**. 무음/음소거 video만 예외. `play()`는 Promise를 반환하고 조건 미충족 시 reject. | ✅ WebKit 블로그 "New video Policies for iOS" |
| 한 번 터치하면 이후 자유? | 서드파티(Agora) 문서: iOS Safari는 오디오 재생을 "사용자 상호작용으로 직접 트리거될 때만" 허용하고, 상호작용 후에도 제한이 풀리지 않는다고 설명. | 🟡 |
| `playbackRate` | Apple 옛 문서(레거시 "iOS-Specific Considerations")에 "iOS에서 playbackRate 설정은 현재 미지원" 문장. 오래된 문서로 보이며 최신 동작과 다를 가능성 큼. | ⚠️ 실기기 |
| `preservesPitch` | 검색으로 iOS 동작 확인 실패. 0.75배속에서 음높이가 낮아지면 듣기 이상함. | ⚠️ 실기기 |

**설계 반영**
- 모든 원어민 음성 재생은 **버튼 탭 핸들러 안에서 동기적으로** `play()` 호출(퀴즈의 "다음 문제" 버튼 탭 = 다음 cue 자동 재생으로 처리).
- 오디오 요소를 문장마다 새로 만들지 말고 **재사용 가능한 플레이어 1개**(또는 첫 탭에서 `AudioContext.resume()`으로 잠금 해제한 Web Audio)를 오디오 서비스 계층에 둔다.
- 0.75배속: 1순위 `audio.playbackRate = 0.75` (+`preservesPitch = true`). 실기기에서 안 되면 Web Audio `AudioBufferSourceNode.playbackRate`(이 경우 음높이도 같이 내려감 → 품질 저하 감수 또는 대안 검토).

### 2-4. IndexedDB 데이터가 삭제되는 조건

| 조건 | 내용 | 신뢰도 |
|---|---|---|
| **7일 상한 (ITP)** | Safari에서 **7일 동안 사이트와 상호작용이 없으면** 스크립트로 쓴 저장소(IndexedDB, LocalStorage, SessionStorage, Service Worker 등록·캐시, media keys)를 삭제. | ✅ webkit.org/tracking-prevention |
| **홈 화면 웹앱 예외** | 홈 화면 웹앱은 Safari와 분리된 저장소를 가지며, **자기 자신의 "사용한 날" 카운터**를 쓴다 → 앱을 쓰면 타이머가 리셋. ITP가 웹사이트 데이터를 지울 때 홈 화면 앱의 1st-party 도메인은 건너뜀. | ✅ WebKit 블로그 10218 |
| 저장 공간 부족 시 축출 | 기기 저장 공간이 부족하면 브라우저 수준 축출은 여전히 가능. `navigator.storage.persist()` 승인은 휴리스틱(홈 화면 실행 등). | 🟡 |
| 사용자가 앱 삭제 | 홈 화면에서 앱 아이콘 삭제 시 데이터도 삭제. | 🟡 (일반 지식) |

**결론**: IndexedDB는 **"원본 데이터 저장소"로 쓰지 않는다.** 원본은 Supabase.
IndexedDB는 다음 용도만 (plan.md에서 확정):
1. 오늘/내일 음성 mp3 캐시(Service Worker Cache Storage가 더 적합할 수 있음)
2. 오프라인/전송 실패 시 **학습 결과 보낼 대기열**(outbox) → 온라인 되면 Supabase로 전송
3. 지워져도 Supabase에서 다시 받아오면 되는 데이터만.

### 2-5. 녹음 포맷 (내 녹음 듣기·Azure 전송)
- `MediaRecorder`: iOS 14.3 이후 **`audio/mp4`(AAC)** 가 기본. iOS 18.4+는 webm/opus도 녹음 가능하다는 2차 정보. → `MediaRecorder.isTypeSupported()`로 기능 검사, UA로 버전 판정 금지. 🟡
- Azure 입력: SDK push stream은 **PCM 16kHz 16bit mono**, REST 단문 API는 `WAV(PCM)` 또는 `OGG(OPUS)`만 받음 ✅. **iOS의 mp4/AAC는 Azure에 바로 못 보낸다.**
- → 설계: `MediaRecorder`를 쓰지 않고 **Web Audio로 PCM을 직접 수집**(AudioWorklet) → (a) Azure push stream으로 전송 (b) 같은 PCM으로 WAV Blob 생성 → "내 녹음 듣기". 녹음 1번으로 두 용도.
- 주의: iOS에서 트랙 설정은 44.1kHz인데 `AudioContext.sampleRate`는 48kHz라 샘플이 빠지는 버그 보고(WebKit 244203) 🟡 → **`AudioContext.sampleRate`를 실제 값으로 읽고 16kHz로 직접 리샘플링**. ⚠️ 실기기.

---

## 3. 웹 푸시 (아이폰)

| 항목 | 결과 | 신뢰도 |
|---|---|---|
| 지원 iOS 버전 | **iOS/iPadOS 16.4 이상** | 🟡 (벤더 문서 다수 일치) |
| 설치 조건 | Safari 공유 버튼 → **"홈 화면에 추가"** 로 설치하고 **홈 화면 아이콘으로 연 앱**에서만 권한 요청 가능. iOS 26부터는 공유 시트의 "웹 앱으로 열기"가 기본 켜짐 — 사용자가 끄면 북마크로 저장되어 푸시 불가. | 🟡 |
| manifest 요구사항 | `manifest.json`의 `display`가 **`standalone` 또는 `fullscreen`**. `browser`/`minimal-ui`는 북마크로 저장됨. 아이콘·`name`·`start_url` 일반 요구사항. | 🟡 |
| 권한 요청에 사용자 터치 필요? | **필요.** 버튼 탭 같은 사용자 제스처 안에서 `Notification.requestPermission()` / `pushManager.subscribe()` 호출. 페이지 로드·`setTimeout`·`DOMContentLoaded`에서 호출하면 실패. | 🟡 (다수 일치) |
| standalone 감지 | `navigator.standalone === true` 또는 `matchMedia('(display-mode: standalone)').matches` | 🟡 |
| VAPID 키 | 표준 Web Push(RFC 8030 + VAPID). Apple 푸시 서버 엔드포인트 도메인 `web.push.apple.com`. **Apple 개발자 계정 불필요.** Node `web-push` 라이브러리로 VAPID 키 생성·발송. | 🟡 |
| 서비스 워커 | `push` 이벤트에서 **`event.waitUntil(self.registration.showNotification(...))`** 필수. | 🟡 |
| **조용한 푸시 금지** | 푸시를 받고 알림을 안 띄우면(`userVisibleOnly` 약속 위반) **구독이 취소**될 수 있다. → 모든 푸시는 반드시 알림 표시. | 🟡 |
| Declarative Web Push | **Safari 18.4(iOS 18.4)** 에서 도입: 서비스 워커 없이도 푸시 메시지 자체(JSON)에 알림 내용을 담아 표시. 서비스 워커가 있으면 내용 수정 가능, 실패 시 선언된 내용이 대체 표시. | ✅ WebKit 블로그 "Meet Declarative Web Push" |

### 3-1. 알려진 안정성 문제와 대응

| 문제 | 보고 내용 | 대응 (plan.md 반영 예정) |
|---|---|---|
| 구독이 조용히 만료 | "엔드포인트가 1~2주 후 사라진다", "3~4번 받고 끊긴다" (Apple 포럼) 🟡 | ① **앱을 열 때마다** `pushManager.getSubscription()`으로 현재 구독을 읽어 Supabase에 upsert(엔드포인트 바뀌었으면 갱신). ② 없으면 설정 화면에 "알림 다시 켜기" 배너. |
| 유효성 사전 확인 불가 | 토큰 유효성을 미리 확인할 방법이 없다 🟡 | 발송 응답 **404/410 → 구독 삭제 + `push_subscriptions.status = 'gone'`** 기록 → 다음 앱 실행 시 재구독 유도. 429 → 재시도 보류. |
| 앱이 열려 있을 때 권한 상실 | Discourse 포럼: 사용자가 앱을 사용 중일 때 푸시를 받으면 문제 생길 수 있다는 보고 🟡 | 서비스 워커에서 **항상** `showNotification` 호출(포커스된 창이 있어도). |
| 백그라운드 동기화 없음 | iOS Safari는 Background Sync 미지원 🟡 | 학습 결과 전송은 앱이 열려 있는 동안 + 다음 실행 시 outbox 재전송. |
| 정시 도착 | Apple 푸시 서버의 지연 SLA 공식 문서 없음 | `Urgency: high`, `TTL` 짧게(예: 아침 알림 3시간). 지연이 크면 오래된 알림은 의미 없으므로 버림. |

**권장**: 1순위는 검증된 **서비스 워커 + `web-push`** 방식. Declarative Web Push는 사용자 iOS가 18.4+이면 쓸 수 있으나 2026년 포럼에 "성공했냐"는 질문이 있을 정도로 사례가 적어서 **확장 아이디어**로 둔다.

---

## 4. 정시 스케줄러 비교 + Supabase 일시정지

### 4-1. 비교표

| 옵션 | 실행 시각 정확도 | 무료 한도 | 설정 난이도 | 시간대 | 신뢰도 / 비고 |
|---|---|---|---|---|---|
| **Vercel Cron (Hobby)** | **지정 시각 ~ +59분 사이 아무 때나** (예: 1:00 설정 → 1:00~1:59) | 프로젝트당 100개, **하루 1회만**. 더 잦은 식은 배포 실패 | 매우 쉬움 (`vercel.json`) | UTC | ✅ Vercel docs (2026-01-28 갱신본). 2024/2025년 버전 문서는 내용이 달랐음 → 날짜 주의. **알림용 부적합 확정.** |
| **Supabase pg_cron + pg_net** | 분 단위 (cron 표준). pg_cron 1.5+는 초 단위(30초 등)도 지원 | 별도 한도 없음(DB 리소스 안). Edge Function 호출은 월 500k(🟡) | 중간 (SQL + Vault) | **GMT/UTC 기본.** `cron.timezone`은 postgresql.conf 설정이라 호스팅 Supabase에서 바꿀 수 있는지 확인 못 함 → **UTC로 생각하고 변환** | ✅ Supabase 공식 문서 (pg_net으로 함수 호출 패턴, Vault로 비밀 보관). **프로젝트가 일시정지되면 같이 멈춤.** |
| cron-job.org | 분 단위. 2차 정보로 지터 4~40초 | 무료, 작업 무제한(공정 사용), 작업당 시간당 60회, 요청 타임아웃 30초, 25회 연속 실패 시 자동 비활성 | 쉬움 (웹 UI) | 시간대 선택 가능(🟡) | 🟡 공식 FAQ 직접 확인 못 함. 외부 서비스 의존 1개 추가. |
| GitHub Actions `schedule` | **부정확.** 공식 문서: 부하가 높을 때 지연, **매 정시(:00)가 고부하**, 심하면 **실행 누락(drop)**. 사용자 보고 15분 이상 지연 흔함 | 공개 저장소 무료 | 쉬움 | UTC | ✅ GitHub docs. **알림용 부적합.** keep-alive 용도엔 가능. |
| Cloudflare Workers Cron Triggers | 2차 정보 ±1분 | **계정당 5개**(무료), CPU 10ms, 서브요청 50 | 중간 | UTC만, DST는 직접 | 🟡/✅ 한도는 공식 limits 페이지. 새 플랫폼 하나 추가. |

### 4-2. 결론: **Supabase pg_cron → (pg_net) → Vercel 푸시 발송 함수**
- 이유: 데이터(알림 시각 설정, 오늘 학습 여부, 퀴즈 대기 여부)가 이미 Supabase에 있으므로 **"보낼지 말지"를 DB 안에서 판단**할 수 있다. 외부 스케줄러는 판단을 위해 또 DB를 불러야 한다.
- KST는 서머타임이 없어 UTC 변환이 항상 `-9시간`으로 고정 → 변환 리스크 낮음.
  - 07:00 KST = 전날 22:00 UTC, 20:00 KST = 11:00 UTC.

**구현 방식 2가지 (plan.md에서 선택)**

| 방식 | 내용 | 장점 | 단점 |
|---|---|---|---|
| A. **매분 체크** | `* * * * *` 작업 1개가 SQL 함수 `dispatch_due_pushes()` 실행 → `settings`의 알림 시각(KST)과 `now() at time zone 'Asia/Seoul'` 비교 → 시각이 됐고 오늘 안 보냈으면(`push_log` unique) `net.http_post` 호출 | 설정 화면에서 시각을 바꿔도 **스케줄 수정 불필요**. 놓친 분(예: DB 순간 장애)도 "시각 이후 & 미발송"이면 다음 분에 보냄 | 하루 1,440번 실행 → `cron.job_run_details` 로그가 쌓임 → **로그 정리 작업 필요** |
| B. 고정 2개 | `0 22 * * *`, `0 11 * * *` 2개 작업. 설정에서 시각 바꾸면 RPC가 `cron.alter_job`으로 재설정 | 실행 횟수 최소 | 시각 변경 = 스케줄 변경(권한·변환 로직 필요), 놓친 실행 복구 없음 |

→ 개인 앱이라 로그 정리만 해주면 A가 단순하고 견고하다(권장).

### 4-3. Supabase 무료 프로젝트 일시정지 조건

| 항목 | 내용 | 신뢰도 |
|---|---|---|
| 규칙 | **"Free projects are paused after 1 week of inactivity."** 유료 플랜은 일시정지 없음. | ✅ supabase.com/pricing |
| 무엇이 "활동"인가 | 출처마다 다름: "DB 쿼리", "API 요청", "Edge Function 호출". 대시보드 방문만으로는 안 됨. | 🟡 (공식 정의 문장 확인 못 함) |
| **pg_cron 자체가 활동으로 인정되나** | 확인 못 함. 확실한 것: **일시정지되면 pg_cron 작업도 멈추고, 재개해도 자동으로 다시 돌지 않는다**는 보고. | 🟡 |
| 일시정지 후 | 데이터는 보존, 대시보드에서 수동 복구 필요. | 🟡 |

**매일 쓸 때 문제 없나?** → 매일 앱을 열면 Supabase에 쿼리가 가므로 **문제 없다.**
**위험 시나리오**: 여행·아픔으로 7일 넘게 안 열면 → 일시정지 → 푸시 끊김 → 다시 돌아올 계기 상실.
**대응 (권장)**: **Vercel Cron(하루 1회, 시각 상관없음)** 으로 `/api/keepalive` → Supabase REST에 가벼운 `select` 1회. Vercel cron의 단점(하루 1회·부정확)이 이 용도에선 문제가 안 됨. 대안: GitHub Actions 3일마다.

### 4-4. 그 밖의 무료 한도 (호스팅)

| 항목 | 값 | 신뢰도 |
|---|---|---|
| Vercel Hobby 함수 호출 | 월 1,000,000 (구버전 100,000) | 🟡 2026-07 서드파티 + 문서 미러 |
| Vercel Hobby 용도 | **비상업·개인 용도만** → 이 앱(1인 개인용) 해당 | ✅ Vercel fair use |
| Vercel 함수 최대 시간 | 출처 충돌(10~60초 vs 300초). 이 앱의 함수(토큰·푸시)는 1초 내외라 무관 | 🟡 |
| Supabase DB | 500 MB | 🟡 |
| Supabase Storage | **1 GB 파일 저장** | ✅ pricing |
| Supabase egress | 5 GB cached (+ 5 GB uncached로 늘었다는 문서도 있음) | ✅/🟡 문서 버전 차이 |
| Supabase 활성 프로젝트 | 2개 | ✅ |

### 4-5. ⚠️ Supabase 2026 변경: 새 테이블 자동 노출 중단 (마이그레이션에 영향)
- **2026-05-30부터 새로 만든 프로젝트**: `public` 스키마에 새로 만든 테이블은 Data API(supabase-js, `/rest/v1`)에 **명시적 Postgres `GRANT`가 있어야** 보인다. 기존 프로젝트는 **2026-10-30** 강제 적용. ✅ Supabase changelog #45329
- 이전에는 `anon`/`authenticated`/`service_role`에 자동 권한이 있었음. RLS 동작은 그대로.
- 권한이 없으면 에러 코드 `42501` + 고칠 `GRANT` 문이 안내됨.
- → **이 앱은 새 프로젝트이므로 해당.** 모든 마이그레이션 파일에 `create table` + `alter table ... enable row level security` + `create policy` + **`grant ... to authenticated`** 를 한 세트로 넣는다. (plan.md 데이터 모델에서 확정)

---

## 5. Azure AI Speech

### 5-1. F0(무료) 한도와 초과 시 동작

| 항목 | 값 | 신뢰도 |
|---|---|---|
| STT 실시간 | **월 5 오디오시간**(Standard·Custom 공유). Batch는 무료 미지원 | ✅ 가격 페이지(검색 발췌) |
| 신경망 TTS | **월 50만(0.5M) 글자** (약 10~11시간 분량) | ✅ |
| F0 한도 조정 | **불가** ("not adjustable") | ✅ quotas 페이지 |
| F0 TTS 요청 속도 | 60초당 20건 (S0는 초당 30건) | 🟡 (2차, plan에서 설정값으로) |
| STT 과금 단위 | **보낸 오디오 길이** 기준, 초 단위. **무음도 포함**(`AudioSecondsTranscribed`). SDK 결과의 `Duration`은 앞뒤 무음 제외라 실제 과금과 다름 | ✅ 가격 페이지 + 🟡 MS 직원 Q&A(2023) |
| TTS 과금 글자 | 요청의 **모든 글자**(문자·숫자·공백·구두점) + SSML 마크업. 단 **`<speak>`, `<voice>` 태그는 제외.** 음성이 생성되지 않아도 성공 처리된 요청이면 과금. 한자는 2글자로 계산 | ✅ Azure 문서 |
| 한 번 인식의 최대 길이 | `recognizeOnceAsync`: 끝 침묵 또는 타임아웃까지, **최대 15초**(C++/Python 최신 문서) — 옛 문서는 30초 | ✅ (문서 간 불일치, 이 앱 문장은 최대 18단어 ≈ 7초라 무관) |
| **초과 시 동작** | F0에서 월 한도를 넘으면 **자동 과금되지 않고 요청이 거부**되며 다음 달 초기화 때 재개. 에러는 "Quota exceeded"(코드 1007 사례), 속도 제한은 429. 해결책은 "다음 달까지 기다리거나 S0로 전환". | 🟡 MS Q&A(모더레이터 답변 포함) — **F0 리소스는 과금 자체가 없는 등급**이므로 위험은 "기능 정지"뿐 |
| 발음 평가 과금 | S0에서는 "STT와 같은 요금"(+ 일부 표에서는 add-on). **F0에서 발음 평가가 5시간 안에서 되는지 공식 문장은 못 찾음.** | ✅(S0) / ⚠️(F0) |

**안전장치 (설계 반영)**
1. Azure 리소스는 반드시 **F0**로 생성(포털에서 가격 책정 계층 "Free F0"). F0 → S0 변경은 사용자가 직접 해야만 일어남.
2. 앱 내부 카운터(Supabase `usage` 테이블)로 **이번 달 TTS 글자 수 / STT 초**를 기록, 설정 화면에 표시.
3. **예산 단계**: STT 80% 도달 → 아침 따라 말하기를 "자가 확인 모드"(녹음 + A/B 비교, STT 없음)로 전환 안내 / 95% → 퀴즈만 STT 사용 / 100%(Azure가 거부) → 퀴즈도 "정답 공개 후 스스로 O/X 체크" 모드. 비율은 설정값.
4. 첫 실기기 테스트에서 **F0 키로 발음 평가 1회 호출**해 되는지 확인(14장).

### 5-2. 브라우저 JS SDK로 발음 평가

- 패키지: `microsoft-cognitiveservices-speech-sdk` (npm). JS 발음 평가는 SDK 1.15.0부터, 운율(prosody) 평가 속성은 **1.34.0**부터. ✅
- `PronunciationAssessmentConfig(referenceText, gradingSystem, granularity, enableMiscue)` ✅
  - `gradingSystem`: 기본 `FivePoint` → 이 앱은 `HundredMark`(0~100) 사용.
  - `granularity`: 기본 `Phoneme`. 선택지 `Phoneme | Word | FullText`. → 단어별 점수만 필요하면 `Word`(응답이 작음). 음소 단위 피드백은 확장 아이디어.
  - `enableMiscue`: true면 참조문과 다른 단어를 **생략(Omission)/삽입(Insertion)** 으로 표시 → 틀린 단어 하이라이트에 활용 가능.
  - `phonemeAlphabet`: `"SAPI"`(기본) 또는 `"IPA"`.
  - `enableProsodyAssessment`: 문서에는 **속성**, MS how-to 샘플에선 **메서드**로 호출 → SDK 버전에 맞춰 확인 (⚠️ 구현 시 확인).
- 결과 점수: `accuracyScore`, `fluencyScore`, `completenessScore`, `prosodyScore`, `pronunciationScore`(종합) + `detailResult.Words[]`(단어별 `AccuracyScore`, `ErrorType`).
- 흔한 에러: `RuntimeError: 5` = 설정 문제(버전 미지원 기능 등). 🟡

예시(리서치용 스케치 — 실제 코드는 plan.md에서 확정):
```ts
import * as sdk from 'microsoft-cognitiveservices-speech-sdk';

// 토큰은 서버리스 함수에서 받는다 (키를 클라이언트에 두지 않음)
const speechConfig = sdk.SpeechConfig.fromAuthorizationToken(token, region);
speechConfig.speechRecognitionLanguage = 'en-US';

// 내가 이미 잡고 있는 마이크 스트림의 PCM(16kHz/16bit/mono)을 밀어 넣는 구조
const format = sdk.AudioStreamFormat.getWaveFormatPCM(16000, 16, 1);
const push = sdk.AudioInputStream.createPushStream(format);
const recognizer = new sdk.SpeechRecognizer(speechConfig, sdk.AudioConfig.fromStreamInput(push));

const pa = new sdk.PronunciationAssessmentConfig(
  referenceText,
  sdk.PronunciationAssessmentGradingSystem.HundredMark,
  sdk.PronunciationAssessmentGranularity.Word,
  true, // enableMiscue
);
pa.enableProsodyAssessment = true; // SDK 버전에 따라 메서드일 수 있음
pa.applyTo(recognizer);

recognizer.recognizeOnceAsync((result) => {
  const r = sdk.PronunciationAssessmentResult.fromResult(result);
  // r.accuracyScore, r.fluencyScore, r.completenessScore, r.prosodyScore, r.detailResult.Words
});
// 녹음 버퍼(Int16Array)를 push.write(buffer) 후 push.close()
```

**사용량 절약 핵심 아이디어 (중요)**
- 녹음한 PCM을 **앱 메모리에 보관**해 두면, "발음 채점" 버튼을 눌렀을 때 **다시 말하게 하지 않고 같은 녹음을 다시 보내면** 된다 → 사용자 경험도 좋고, 재발화 시간이 안 든다.
- 더 아끼려면: 퀴즈/따라 말하기의 STT 요청에 **처음부터 발음 평가 설정을 붙여** 한 번에 받으면 STT 1회로 텍스트 + 점수를 모두 얻는다. 단 프롬프트 1-7은 "학습 화면에서는 버튼을 눌렀을 때만 호출"이라고 했다 → **"점수 표시"만 버튼 뒤로 숨기고 호출은 합치는** 방식이 가능한지 plan.md에서 사용자 결정 필요 (F0에서 발음 평가 포함 요청이 STT 시간 외 별도 소모가 있는지 ⚠️ 확인 후).

### 5-3. 마이크 → Azure 오디오 파이프라인
```
getUserMedia (세션당 1회, 오디오 서비스가 보관)
  → AudioContext(실제 sampleRate 읽기, 보통 48000) → AudioWorklet에서 Float32 수집
  → 16kHz로 리샘플링 + Int16 변환
      ├─ Azure PushAudioInputStream.write()   (인식/발음 평가)
      └─ 메모리 버퍼 → WAV Blob → <audio> "내 녹음 듣기" / A·B 비교
```
- **버튼식(push-to-talk) 녹음** 권장: "말하기" 탭 → 말하기 → 자동 종료(무음 감지) 또는 다시 탭. 퀴즈에서 생각하는 동안의 무음이 과금되지 않는다(5-1: 무음도 과금).
- 클라이언트 VAD(간단한 에너지 기반): 말 시작 300ms 전부터만 전송(pre-roll), 말 끝난 뒤 700ms 무음이면 종료. 값은 설정값.

### 5-4. 단기 토큰 발급 방식
- `POST https://<region>.api.cognitive.microsoft.com/sts/v1.0/issueToken`
  - 헤더 `Ocp-Apim-Subscription-Key: <키>`, 빈 body → 응답 body가 **JWT 토큰(유효 10분)** ✅
  - 커스텀 도메인 리소스는 `https://<리소스명>.cognitiveservices.azure.com/sts/v1.0/issueToken` ✅
  - 지역이 포털의 리소스 지역과 다르면 404 ✅(Q&A)
  - VNet/방화벽 규칙을 켜면 토큰 API가 막힌다는 보고 🟡 → 개인용이라 네트워크 규칙은 켜지 않는다.
- 클라이언트는 `SpeechConfig.fromAuthorizationToken(token, region)`으로 사용, **9분마다 갱신**(`recognizer.authorizationToken = 새토큰`).

**토큰 함수 보호 — 프롬프트 v2의 "비밀값으로 보호"를 수정 제안**
| 방법 | 동작 | 판단 |
|---|---|---|
| 비밀값 헤더(`x-app-secret`) | 클라이언트가 비밀값을 헤더에 넣어 호출 | ❌ 비밀값이 **클라이언트 번들에 들어가야 하므로** 누구나 볼 수 있다. 보호 효과 없음 |
| **Supabase 세션 JWT 검증** | 클라이언트가 로그인 세션의 `access_token`을 `Authorization: Bearer`로 보냄 → 함수가 Supabase로 검증 → `user.id === OWNER_USER_ID`(환경변수)일 때만 토큰 발급 | ✅ 권장. 키·비밀값이 번들에 없음. 로그인한 "나"만 통과 |
| 고정 IP 제한 | — | 모바일이라 불가 |

푸시 **발송** 함수는 브라우저가 아니라 pg_cron(pg_net)이 호출하므로 **비밀값 헤더 방식이 맞다**(비밀값은 Supabase Vault + Vercel 환경변수에만 존재).

### 5-5. 대화용 음성 2개 추천

| 역할 | 추천 1 | 추천 2(대안) | 메모 |
|---|---|---|---|
| 상대방(partner) | `en-US-AvaNeural` (여) | `en-US-JennyNeural` (여, "친근·명료") | |
| 나(me) | `en-US-AndrewNeural` (남) | `en-US-GuyNeural` (남) | |

- 근거: en-US 목록에 Ava/Andrew/Emma/Brian이 일반판과 `Multilingual`판으로 나란히 있고, Jenny/Guy는 오래된 표준 음성. 🟡 (MS 공식 음성 갤러리를 직접 확인하지 못함 → **구현 1단계에서 Speech Studio 음성 갤러리로 실제 들어보고 확정**)
- `Multilingual` 판은 영어만 쓰는 이 앱에 필요 없음. **HD/Dragon 계열** 음성은 가격·F0 지원 여부를 확인하지 못했으므로 쓰지 않는다.
- 사용자 성별에 따라 "나" 음성을 여성으로 바꾸고 싶을 수 있음 → 음성 이름은 **설정 파일(`config/voices`)** 에만 두고, 파일명 해시에 음성 이름이 포함되므로 바꾸면 "나" 문장만 새로 생성된다(이전 파일은 그대로 남음).

---

## 6. 음성인식 결과와 정답 비교

### 6-1. 정규화 — 왜 필요한가
- 음성인식 평가(WER)에서 **정답과 인식 결과 양쪽에 같은 정규화**를 적용해야 형식 차이(대소문자, 구두점, `you're`/`you are`, `ten`/`10`)가 오답으로 잡히지 않는다. Whisper 논문은 이런 무해한 차이를 할인하는 영어 정규화기를 만들었고, 축약형이 많은 CallHome/Switchboard, 숫자가 많은 WSJ에서 WER이 크게 줄었다. ✅ arXiv 2212.04356
- 숫자 정규화를 **정답·인식 결과 둘 다**에 할 때 WER이 가장 낮았다. ✅ arXiv 2609.21084(2026)
- Whisper 영어 정규화기 동작 예: `can't` → `can not`, `twenty-one` → `21`. 🟡

### 6-2. 정규화 규칙 (제안 순서)
1. 유니코드 정리: `’ ‘ ʼ` → `'`, `“ ”` → `"`, 전각 → 반각.
2. 소문자화.
3. **숫자 단어 ↔ 숫자 통일**: 숫자 단어를 숫자로 (`ten` → `10`, `twenty-one` → `21`, `three o'clock` → `3:00`?) — 시간 표현은 `3`, `3:00`, `three`, `three o'clock`을 모두 `3`으로 축약하는 규칙을 별도 처리.
4. **축약형 펼치기** (양쪽 모두): `i'm→i am`, `you're→you are`, `can't→can not`, `won't→will not`, `n't→ not`, `'ll→ will`, `'ve→ have`, `'d→ would`(★모호), `'s→ is`(★모호: is/has/소유격).
   - ★모호한 축약은 "펼친 형태 후보 여러 개"를 허용: 정답 `he's been`과 인식 `he has been` 둘 다 맞게. 구현은 정답 쪽을 후보 집합으로 펼쳐 **가장 잘 맞는 후보**로 채점.
   - 소유격 `'s`(`Jake's car`)는 펼치면 안 됨 → 다음 단어가 명사인지 판단은 어렵다 → **정답 텍스트의 `'s`가 소유격이면 콘텐츠 데이터에 표시**하는 방법(데이터 쪽 해결)이 간단.
5. 구두점 제거(단 `:`는 시간 처리 후 제거), 하이픈은 공백으로(`e-mail`→`e mail`, 양쪽 동일하므로 OK).
6. 간투사(filler) 제거: `um, uh, er, hmm`.
7. 미/영 철자 통일 소사전(소수: `okay/ok`, `alright/all right`, `gonna/going to`(★ 인식기가 `gonna`로 적는 경우), `wanna/want to`, `yeah/yes`는 **동일 처리 안 함**(의미상 같지만 drill 목표 표현일 수 있음) → 동치 사전은 설정 파일로).
8. 공백 기준 토큰화.

### 6-3. 단어 단위 diff 알고리즘
- **단어 단위 Levenshtein 편집 거리 + 역추적(backtrace)**: 정답 N단어, 인식 M단어로 (N+1)×(M+1) DP 표 → 각 단어를 `일치 / 대치 / 누락(정답엔 있고 말 안 함) / 삽입(말했는데 정답에 없음)`으로 분류 → 화면 하이라이트에 그대로 사용.
- 문장이 최대 18단어라 O(N·M) = 324칸, 성능 문제 없음.
- 지표: `WER = (S + D + I) / N`, `단어 정확도 = 일치 / N`.
- 대안: `diff` 라이브러리의 LCS 기반 `diffWords` → 대치를 "삭제+삽입" 2개로 보여줘 하이라이트가 덜 직관적. 직접 구현(30줄)이 낫다.

### 6-4. 통과 기준 (제안, 설정값)
- 인식기 자체 오류(비원어민 발화 WER은 원어민보다 높음)를 감안해 **약간 관대하게**.
- 제안: **허용 오류 수 = max(1, round(0.2 × N))** 이하 **그리고** 그 문장의 **핵심 표현 토큰은 순서대로 모두 일치**.
  - N=5 → 1개까지, N=10 → 2개, N=15 → 3개.
  - 핵심 표현 토큰: 콘텐츠 데이터의 `expression`을 정규화한 토큰(예: `running a bit late`).
- 레벨 테스트 "따라 말하기"는 통과/실패가 아니라 **단어 일치율(0~1)** 을 점수로 사용.
- 상황 말하기(허용 답안 여러 개)는 **허용 답안 각각과 비교해 최고 일치율** 사용.

---

## 7. 레벨 테스트 설계 근거

### 7-1. 듣고 따라 말하기(Elicited Imitation, EI)의 타당성
| 연구 | 내용 | 신뢰도 |
|---|---|---|
| 메타분석 (Kostromitina & Plonsky 2021 요약 포함) | EI 점수와 L2 숙달도 기준 측정의 평균 상관 **r = .75** (자기평가 .81, 표준화 시험 .74) | ✅ 논문(검색 발췌) |
| 같은 메타분석 — 설계 요인 | **응답 전에 잠깐 쉬는(pause) 설계가 상관이 더 높음(r = .76)**, 즉시 따라 하게 한 설계는 r = .63 | ✅ |
| Graham et al. 2008 | 영어 EI vs OPI(구술 인터뷰) **r = .658** (n=156) | ✅ |
| Cox & Davis 2012 | EI와 **배치고사 총점**의 강한 상관 | ✅(인용 발췌) |
| ETS 2021 (Davis 외) | 영어 EI 과제 vs C-test **r = .69** | ✅ ETS Research Report |
| ASR 채점 EI | 자동 음성인식으로 EI 채점하는 연구 존재 ("Elicited Imitation as an Oral Proficiency Measure with ASR Scoring") | ✅ |
| 한계 | **영어 배치 결정에 EI만으로 직접 타당화한 연구는 찾지 못함.** EFL 학습자 집단에서의 일반화 근거도 더 필요하다는 지적 | ✅ |

**설계 반영**
1. **응답 전 짧은 지연**: 문장 재생이 끝나고 바로 말하게 하지 말고 **1.5초(설정값) 후 "삐" 신호 → 말하기**. 메타분석에서 pause 설계가 더 타당 → 단순 소리 기억(echoic memory)으로 따라 하는 걸 막는다.
2. **문장 길이를 점점 늘림** (프롬프트와 일치): 짧고 쉬운 문장 → 길고 복잡한 문장. EI는 길이가 작업기억 한계를 넘을 때 문법 지식으로 재구성해야 하므로 숙달도가 드러난다.
3. **1회만 들려준다** (다시 듣기 금지).
4. 채점: 단어 일치율(6장) + Azure 발음 정확도. EI 연구에서 흔히 쓰는 0~4점 척도(완벽 4 / 의미 유지 소수 오류 3 / …)는 사람 채점용이라, 이 앱은 **단어 일치율을 0~4로 구간화**하는 방식으로 근사(plan.md에서 기준 제안).

### 7-2. 2단계 적응형(Multistage Testing, MST) 구조
- **1-2 구조**(1단계 라우팅 모듈 1개 → 2단계 모듈 2개 중 하나). 라우팅 점수가 기준 이하면 쉬운 모듈, 초과면 어려운 모듈. 각 경로가 하나의 "booklet". ✅(MST 교과서/문서)
- Luecht & Nungester(1998): **복잡도와 적응성 사이 균형**이 중요. ✅
- Kim & Moses(ETS 2014) 시뮬레이션: 2단계 MST에서 **잘못된 경로 배정(misrouting)의 영향은 대체로 작았다.** ✅ → 1단계 6문항으로 라우팅해도 괜찮다는 근거.
- 프롬프트 기본값: 1단계 중급 6문항 → 2단계 초급 블록 또는 고급 블록 9문항 (총 15문항, 약 10분).

**판정 로직 스케치 (기준값은 plan.md에서 근거와 함께 확정, 모두 설정값)**
```
stage1 (중급 6문항) 점수 s1 (0~1)
  s1 >= 0.60 → 고급 블록 9문항
  s1 <  0.60 → 초급 블록 9문항

고급 블록 점수 s2:  s2 >= 0.65 → 고급   /  그 외 → 중급
초급 블록 점수 s2:  s2 >= 0.75 → 중급   /  그 외 → 초급
```
- 2단계 블록이 2개뿐이라 "중급"은 **두 경로 모두에서 도달 가능한 중간 결과**로 정의한다.
- 문항 유형 배분(각 블록): 따라 말하기 / 대답 고르기 / 상황 말하기를 대략 1:1:1.

### 7-3. CEFR 레벨 설명과 판정 기준 잡는 법
- CEFR Companion Volume(2018, 2020 개정): A1~C2 + **pre-A1**, A2+/B1+/B2+ "plus" 레벨, C레벨 설명 보강, **온라인 상호작용** 척도 추가. 원문 PDF는 Council of Europe 사이트에서 무료. ✅
- 이 앱의 대응(프롬프트 1-3): 초급 A1–A2 / 중급 B1 / 고급 B2–C1.
- 판정 기준 잡는 법 (개인용 현실안):
  1. 문항 난이도를 CEFR 기술문(예: B1 "익숙한 주제에 대해 준비 없이 대화에 참여")에 맞춰 **작성 단계에서 레벨 태그**를 단다.
  2. 기준 점수는 **"그 레벨 문항의 대부분(60~75%)을 해낼 수 있으면 그 레벨"** 이라는 일반적 숙달 판정 관행으로 시작.
  3. 1인용이라 통계적 표준 설정(Angoff 등)은 불가 → **초기값 + 사용 데이터로 조정**: 레벨 테스트 후 첫 10학습일 퀴즈 정답률이 50% 미만/95% 이상이면 기준이 잘못된 것 → 설정값 조정 근거로 기록.
- ⚠️ 이번 리서치에서 CEFR 말하기 상호작용 기술문의 **원문 문장**은 검색으로 가져오지 못했다 → 콘텐츠 생성 단계에서 PDF 원문 기준으로 레벨 태그를 검토할 것.

---

## 8. 자동 승급 기준 (85% / 10학습일)

### 8-1. 근거
| 근거 | 내용 | 신뢰도 |
|---|---|---|
| 완전학습(Mastery Learning) | 숙달 기준은 **보통 80~90% 정답**(Bloom 계열, Slavin 1987 리뷰) | ✅ Slavin 1987 / 🟡 2차 정리 |
| D'Albro 연구(학위논문) | 80% 고정 vs 90% 고정 vs 점진 상승 비교 → **기준을 높여도 성취가 더 높지 않았고**, 90%는 학습 효율·태도가 더 나빴음. **80%가 최선**이라는 결론. 단 소규모 1건 | ✅(원문 발췌) |
| "85% 규칙" (Wilson et al. 2019, *Nature Communications* 10:4646) | 경사하강 학습 알고리즘의 이진 분류에서 **최적 훈련 정확도 ≈ 85%(오류 15.87%)**. 저자 스스로 인간 적용은 "지각 학습" 쪽이 유력하고 복잡한 학습은 후속 과제라고 함 | ✅ — 단, 언어 학습 승급 기준의 직접 근거는 아님 |

**판단: 85%는 완전학습 범위(80~90%)의 중간이라 기본값으로 적절하다.** 다만 아래 4가지를 정의하지 않으면 실제로는 엉뚱하게 동작한다.

### 8-2. 85% / 10학습일을 그대로 쓰면 생기는 문제와 보완(제안)

| 문제 | 설명 | 보완 (설정값) |
|---|---|---|
| ① "정답률"의 정의 | 다시 말하기 2회까지 허용하면 **최종 통과율**은 쉽게 90%+ | **첫 시도 통과율**로 계산 (재시도 통과는 별도 기록) |
| ② 퀴즈는 "복습"이다 | 퀴즈는 이미 배운 문장을 기억하는지 보는 것 → 레벨 실력보다 **기억력**을 측정. 그래도 "이 레벨 내용을 잘 소화하고 있다"는 신호로는 타당 | 이 한계를 인정하고 사용. 하향은 자동으로 안 하므로 위험 낮음 |
| ③ 이전 레벨 문장이 섞임 | 승급 후 퀴즈에 이전(쉬운) 레벨 문장이 나와 정답률이 부풀려짐 | **현재 레벨 문항만** 승급 계산에 포함 |
| ④ 표본 크기 | 처음 7학습일은 퀴즈가 5~10문항뿐. 10학습일 중 퀴즈를 빼먹은 날도 있음 | 최근 10학습일 중 **퀴즈 응시 8일 이상** **AND** 현재 레벨 채점 문항 **100개 이상** 일 때만 판정 |
| ⑤ 승급 직후 | 창(window)에 이전 레벨 기록이 남아 바로 또 판정될 수 있음 | 승급하면 창을 **리셋**(새 레벨의 학습일만 카운트) |
| 하향 권유 | 50% 미만이면 레벨 테스트 재응시 "권유만" | 같은 표본 조건 적용 + 권유 알림은 **7학습일에 1번** 이하 |

---

## 9. 학습일 기준 스케줄러 엣지 케이스

### 9-0. 용어 정의 (제안)
- **서비스 날짜(service date)**: Asia/Seoul 기준, **새벽 4시 경계**. `serviceDate(t) = toKST(t - 4h).date`. (01:30에 한 활동은 전날 서비스 날짜)
- **학습일(learning day)**: 아침 학습을 **끝낸** 서비스 날짜. 순번 `n` (Day N). **서비스 날짜당 최대 1개.**
- 학습일 `n`의 저녁 퀴즈 = 학습일 `n-1`, `n-3`, `n-7`의 콘텐츠에서 각 5문항.
- 학습일 기록에는 `(n, service_date, level, level_day_k)` 를 남긴다 → "그날 어느 레벨의 몇 일차를 배웠는지"가 확정되어 레벨이 바뀌어도 퀴즈 출제가 흔들리지 않는다.
- 이 계산은 **순수 함수 1개**(`learning-day.ts`)에 모으고 단위 테스트(프롬프트 요구).

### 9-1. 케이스 표

| # | 상황 | 제안 동작 |
|---|---|---|
| 1 | **처음 7학습일** | Day1: 세 섹션 모두 "아직 없음" → **퀴즈 0문항 → 퀴즈 없음**(20:00 푸시도 보내지 않거나 "오늘은 퀴즈 없음, 내일부터!"). Day2~3: n-1만 5문항. Day4~7: n-1, n-3 → 10문항. Day8~: 15문항. |
| 2 | **아침은 했는데 저녁 퀴즈를 빠짐** | 다음 아침 학습을 **시작**하기 전까지 풀 수 있음(프롬프트 기본값). 다음 아침 시작 버튼을 누르면 "어제 퀴즈 안 풀었어요. 지금 풀까요? / 건너뛰기(미응시 기록)" 확인. 건너뛰면 `quiz_sessions.status = 'missed'`. |
| 3 | **아침 없이 저녁만 연 날** (오늘은 학습일 아님) | 학습일이 아니므로 "오늘의 퀴즈"는 없음. 단 **직전 학습일의 퀴즈가 아직 대기 중**(2번 규칙)이면 그걸 보여줌. 20:00 푸시는 상태에 따라: 대기 퀴즈 있음 → "퀴즈 시간" / 오늘 아침 안 함 → "오늘 아침 학습을 아직 안 했어요"(보낼지 여부 설정값) / 둘 다 아님 → 보내지 않음. **이를 위해 푸시 판단이 DB 상태를 봐야 함 → 4-2의 pg_cron 판단 방식과 맞물림.** |
| 4 | **레벨 변경 직후** | 승급/재응시 결과는 **다음 학습일부터** 적용(오늘 아침을 이미 했다면 내일부터). 퀴즈는 학습일 기록에 저장된 `(level, level_day_k)`를 따르므로 이전 레벨 문장도 그대로 출제. 진도는 레벨별 독립(`progress(level) = 마지막 level_day_k`). 고급→재응시로 초급이 되면 초급은 **멈췄던 일차 다음부터** 재개. |
| 5 | **하루 경계(새벽 4시)** | 03:50에 아침 학습 시작, 04:10에 끝냄 → 학습일 = **끝낸 시각의 서비스 날짜**(프롬프트: "학습일 = 아침 학습을 끝낸 날"). 퀴즈는 **시작 시각** 기준으로 귀속(풀다가 4시가 지나도 같은 세션 유지). |
| 6 | 같은 서비스 날짜에 아침 학습 2번 | 두 번째는 **새 학습일이 아님**("오늘은 이미 완료. 복습 모드로 다시 보기"만 제공). 하루에 Day를 2개 소진하면 1·3·7 간격이 무너짐. |
| 7 | 콘텐츠 소진 | 레벨의 30일치를 다 쓰면 다음 학습일 시작 시 "다음 30일치를 생성해야 해요" 안내 + 학습 불가(또는 복습 모드). |
| 8 | 아침 학습 중간에 그만둠 | 진행 위치를 저장(어느 표현·단계까지) → 다시 열면 이어서. **끝내야** 학습일 확정. 서비스 날짜가 바뀐 뒤 끝내면 새 날짜로 확정. |
| 9 | 퀴즈 도중 이탈 | 답한 문항까지 저장, 같은 문항 세트로 재개. 문항 세트는 **학습일 번호를 시드로 결정적(deterministic)** 으로 뽑아 다시 열어도 같게. |
| 10 | "직전 퀴즈에 나온 문장 피하기" | 학습일 k의 콘텐츠는 k+1, k+3, k+7 퀴즈에 3번 출제된다. 표현 1개당 후보 쌍 = 파생 3개 + 대화 속 내 대사 2~4개 = **5~7개** → 3번 모두 **서로 다른 쌍**으로 뽑을 수 있음. → 규칙을 "직전 퀴즈"보다 강하게 "**그 표현에서 이미 출제된 쌍 제외, 후보가 없으면 가장 오래전에 나온 것**"으로 제안. |
| 11 | 시간대 | 고정 `Asia/Seoul`(설정값). 해외여행 중에도 KST 기준. 기기 시간대 무시. |
| 12 | 기기 시계가 틀림 | 학습일 확정 시각은 **서버(Supabase `now()`)** 기준으로 기록. 클라이언트 시각은 표시용. |

---

## 10. 하루 20분 분량 검증

### 10-1. 단위 시간 가정 (근거: 일반 발화 속도 약 2.5단어/초 + 조작 시간)
| 동작 | 시간 |
|---|---|
| 원어민 문장 1회 재생 | 초급 2.5초 / 중급 3.5초 / 고급 5초 |
| 내 발화 | 위와 비슷 + 시작 지연 1초 |
| 피드백 보기(하이라이트) | 4초 |
| 텍스트/뜻 열어보기 + when_to_use 읽기 | 표현당 15초 |
| 화면 전환 | 표현당 5~10초 |

### 10-2. 프롬프트 그대로(모든 단계 풀 버전) 계산 — 초과
| 단계 (표현 1개, 초급) | 계산 | 초 |
|---|---|---|
| 소리 먼저 (2회 듣기 + 탭 + 읽기) | 2.5×2 + 15 + 5 | 25 |
| 핵심 표현 따라 말하기 + backward build-up(3덩어리+전체=4회) | 4 × (2.5+3.5+4) + 재시도 20% | 45 |
| 파생 3개 (cue + 모델 + 발화 + 피드백) | 3 × 15 + 재시도 | 55 |
| 대화 4턴: 전체 듣기 → B역 → 역할 교대 | 12 + 22 + 22 | 60 |
| 전환 | | 10 |
| **표현 1개** | | **195초** |
| **×5 = 아침** | | **약 16분** (목표 12분 초과) |

같은 방식으로 중급 약 20분, **고급 약 25분**. + 퀴즈 → 하루 25~33분. **20분 불가.**

### 10-3. 조정안 (권장) — 다음 3가지만 바꾼다
1. **backward build-up은 "첫 전체 시도 실패 시"에만** 자동 진입(성공하면 건너뜀). 기대 진입률 50%.
2. **대화 처음 "전체 듣기" 생략** → 바로 B역(상대 대사가 들리므로 듣기는 자연히 포함).
3. **역할 교대는 하루 1개 대화만**(그날 점수가 가장 낮았던 표현의 대화, 또는 5번째 표현). 나머지는 "역할 바꿔 한 번 더" 선택 버튼.

| 단계 (표현 1개) | 초급 | 중급 | 고급 |
|---|---|---|---|
| 소리 먼저 | 25 | 25 | 25 |
| 따라 말하기(+조건부 build-up) | 20 | 25 | 30 |
| 파생 3개 | 40 | 45 | 50 |
| 대화 B역 (초급 2턴 / 중급 3턴 / 고급 3.5턴 평균) | 28 | 50 | 80 |
| 전환 | 5 | 5 | 5 |
| **표현 1개** | **118초** | **150초** | **190초** |
| ×5 | 9.8분 | 12.5분 | 15.8분 |
| + 역할 교대 1개 + 시작/마무리 | +1분 | +1분 | +1.3분 |
| **아침 합계** | **≈ 11분** ✅ | **≈ 13.5분** | **≈ 17분** ❌ |

### 10-4. 저녁 퀴즈
| 단계 | 계산(15문항) | 초급 | 고급 |
|---|---|---|---|
| cue 듣기 + 생각 + 말하기 + 피드백 | 15 × (3 + 2 + 3.5 + 3) / 고급 15 × (5+3+6+3) | 173초 | 255초 |
| 재시도(첫 시도 실패 30%, 두 번째 실패 10%) | +0.4 × 문항시간 × 15 | +69초 | +102초 |
| 정답 공개 + A/B 비교(실패 10%) | 1.5문항 × 12초 | +18초 | +18초 |
| 결과 화면 | | 30초 | 30초 |
| **합계** | | **≈ 4.8분** ✅ | **≈ 6.7분** ✅ |

### 10-5. 결론
| 레벨 | 아침 | 저녁 | **합계** | 판정 |
|---|---|---|---|---|
| 초급 | 11 | 4.8 | **≈ 16분** | ✅ 여유 |
| 중급 | 13.5 | 5.8 | **≈ 19분** | ✅ 빠듯 |
| 고급 | 17 | 6.7 | **≈ 24분** | ❌ 4분 초과 |

**고급을 20분에 맞추는 선택지 (plan.md 전에 사용자 결정 필요)**
- (a) 고급 대화를 6턴(하한)으로 고정 → 약 -1.5분 / 그래도 22분
- (b) 고급만 파생 문장 2개(대치 1 + 변형 1, 프롬프트 최소 조건은 충족) → 약 -1.5분
- (c) 고급은 "22~24분"을 허용 (난이도가 오른 만큼 시간 증가 인정)
- (d) (a)+(b) → 약 20.5분
- 추천: **(d)** — 프롬프트의 "대치 1개 이상, 변형 1개 이상" 조건을 지키면서 20분에 근접. 단, 이 숫자는 추정이므로 **구현 후 실제 소요 시간을 기록**(세션 시작/끝 타임스탬프)해서 재조정.

---

## 11. 월 예상 사용량과 무료 한도 대비 여유

### 11-1. TTS (글자 수) — 콘텐츠 생성 시 1회만 발생
가정한 평균 글자 수(공백·구두점 포함, SSML은 `<speak><voice>`만 사용 → 마크업 과금 0):

| 레벨 | 표현 | 파생 3쌍(cue+me) | 대화 | build-up 덩어리 | **표현당** | **하루(×5)** | **30일** |
|---|---|---|---|---|---|---|---|
| 초급 | 25 | 3×(35+30)=195 | 4턴×35=140 | 2×15=30 | 390 | 1,950 | **58,500** |
| 중급 | 35 | 3×(45+45)=270 | 6턴×50=300 | 2×22=44 | 649 | 3,245 | **97,350** |
| 고급 | 45 | 3×(60+60)=360 | 7턴×65=455 | 3×25=75 | 935 | 4,675 | **140,250** |
| 레벨 테스트 2세트 | 세트당 24문항 × 평균 70자 | | | | | | **3,360** |
| **합계 (3레벨 30일 + 테스트)** | | | | | | | **≈ 299,460** |

- **계산식**: `월 TTS = Σ_레벨 [ 30 × 5 × (표현 + 3×(cue+me) + 턴수×턴길이 + 덩어리수×덩어리길이) ] + 테스트`
- **무료 한도 대비**: 299,460 / 500,000 = **60%** → 3레벨을 한 달에 다 만들어도 **여유 40%**.
- 주의 ①: 같은 문장+같은 음성은 해시 캐시로 **재생성 0**. 다시 만들 때(문장 수정) 그 문장만 다시 과금.
- 주의 ②: build-up 덩어리를 **따로 합성**하는 이유 — 문장 녹음을 잘라 쓰면 글자 0이지만, 잘린 덩어리는 문장 중간 억양이라 청화식 원칙("끝 덩어리는 문장 끝 억양으로")에 안 맞음. 따로 합성하면 덩어리 끝이 자연스러운 하강조가 된다(글자 약 +7%).
- 주의 ③: 다음 달 "다음 30일치 생성" 때도 같은 양(≈30만) → 매달 60% 수준. 단, **사용자가 쓰는 레벨만 생성**하면 초급 6만 / 고급 14만으로 크게 줄어듦 → plan.md에서 "현재 레벨 + 다음 레벨만 생성" 옵션 제안.
- **요청 수와 시간(F0 60초당 20건 가정)**: 클립 수 ≈ 초급 1,950 + 중급 2,250 + 고급 2,550 + 테스트 ~150 = **약 6,900건 → 약 5.8시간** 연속 실행. 1회성이지만 길다 → 스크립트는 **중단 후 이어하기**(해시 캐시) + 속도 제한 설정값 필수.
- 저장 용량: `audio-24khz-48kbitrate-mono-mp3`(6KB/초) × 평균 2.5초 ≈ 15KB × 6,900 ≈ **100MB** → Supabase Storage 1GB의 10%, 또는 Vercel 정적 파일(plan.md에서 비교). 하루 재생 트래픽은 약 1MB → egress 문제 없음.

### 11-2. STT (오디오 시간) — 매일 발생 ← 핵심 리스크
가정: 10장 조정안 흐름, 재시도 계수 1.2, 과금 초 = 발화 길이 + 1초(시작 지연·끝 무음 감지), 버튼식 녹음(생각하는 무음 제외).

| 항목 | 초급 | 중급 | 고급 |
|---|---|---|---|
| 아침 발화 수/일 (표현당 9.1 / 10.5 / 11.2 × 5) | 45.5 | 52.5 | 56 |
| 발화당 과금 초 (평균 단어수/2.5 + 1) | 3.4 | 4.8 | 6.6 |
| **아침 초/일** | 155 | 252 | 370 |
| 퀴즈 발화 수/일 (15 × 1.4) | 21 | 21 | 21 |
| 퀴즈 초/일 (+생각 후 시작 지연 1초) | 92 | 122 | 160 |
| 발음 채점 버튼 (하루 10회, 녹음 재전송) | 34 | 48 | 66 |
| **하루 합계(초)** | **281** | **422** | **596** |
| **월(30일) 시간** | **2.34h** | **3.52h** | **4.97h** |
| 5시간 대비 | 47% | 70% | **99%** ❌ |
| + 레벨 테스트 1회(15문항×6초) | +0.03h | | |

**계산식**: `월 STT(시간) = 30 × [ 아침발화수×과금초 + 퀴즈발화수×(과금초+1) + 채점횟수×과금초 ] / 3600`

**고급에서 한도에 닿는 문제 — 대응 시나리오**

| 시나리오 | 내용 | 고급 월 사용 |
|---|---|---|
| S1. 전부 Azure | 위 표 그대로 | 4.97h ❌ |
| S2. 발음 평가를 인식 요청에 합침 | "채점" 버튼은 이미 받은 점수를 보여주기만 → 재전송 0 | 4.42h (88%) ⚠️ |
| S3. S2 + VAD로 시작 지연 제거(pre-roll 0.3초) | 발화당 -0.7초 | 3.82h (76%) ✅ |
| S4. S3 + 내장 STT가 standalone에서 동작(실기기 확인 시) | 아침 따라 말하기는 내장 STT, Azure는 퀴즈·채점만 | ≈ 1.6h (32%) ✅✅ |
| S5. S3 + 예산 가드 | 80% 넘으면 아침 drill을 자가 확인 모드로 | 상한 보장 |

**권장**: **S3 + S5를 기본**, 실기기 테스트로 내장 STT가 되면 S4로 개선.
- 31일 달은 ×31/30 (+3.3%).
- 초과해도 F0라 **과금 0**(요청 거부) → 리스크는 "그달 말 STT 정지"뿐이며, 예산 가드로 퀴즈용 여유를 남긴다.

---

## 12. 출처 목록 (확인일: 2026-10-21, 모두 웹 검색 결과로 확인 — 0-1 참고)

### 플랫폼 / 인프라
| 주제 | 출처 | 신뢰도 |
|---|---|---|
| Vercel Cron 한도 | https://vercel.com/docs/cron-jobs/usage-and-pricing | ✅ |
| Vercel Hobby 플랜 | https://vercel.com/docs/plans/hobby | ✅ |
| Vercel 한도(2차) | https://deploywise.dev/blog/vercel-free-tier-limits-2026 | 🟡 |
| Supabase 가격·일시정지 | https://supabase.com/pricing | ✅ |
| Supabase 일시정지(2차) | https://github.com/travisvn/supabase-pause-prevention , https://simplebackups.com/blog/supabase-free-tier-paused | 🟡 |
| Supabase Edge Function 스케줄 | https://supabase.com/docs/guides/functions/schedule-functions | ✅ |
| Supabase pg_cron | https://supabase.com/docs/guides/database/extensions/pgcron | ✅ |
| pg_cron 시간대 | https://access.crunchydata.com/documentation/pg_cron/1.6.2/pdf/pg_cron.pdf | ✅ |
| Supabase 새 테이블 GRANT 변경 | https://supabase.com/changelog/45329-breaking-change-tables-not-exposed-to-data-and-graphql-api-automatically | ✅ |
| Supabase Storage 대역폭 | https://supabase.com/docs/guides/storage/serving/bandwidth | ✅ |
| GitHub Actions 스케줄 지연 | https://docs.github.com/en/actions (troubleshooting workflows), https://github.com/orgs/community/discussions/201738 | ✅ |
| cron-job.org | https://blog.cron-job.org/service/2021/12/01/errors-explained-timeout.html , https://www.fastcron.com/blog/free-cron-job-services | 🟡 |
| Cloudflare Workers 한도 | https://developers.cloudflare.com/workers/platform/limits | ✅ |

### iOS / Safari / 웹 푸시
| 주제 | 출처 | 신뢰도 |
|---|---|---|
| 홈 화면 앱 SpeechRecognition 미지원 | https://bugs.webkit.org/show_bug.cgi?id=225298 | ✅ |
| standalone STT 실패 보고 | https://developer.apple.com/forums/thread/748048 | 🟡 |
| standalone `onresult` 미수신(버그 321436 인용) | https://github.com/megulus/practice-journal/pull/338 | 🟡 |
| iOS interimResults 문제 | https://developer.apple.com/forums/thread/775699 | 🟡 |
| Safari 26 WebKit 기능 | https://webkit.org/blog/17333/webkit-features-in-safari-26-0/ | ✅ |
| 마이크 권한 재요청(hash) | https://bugs.webkit.org/show_bug.cgi?id=215884 | ✅ |
| 마이크 권한 재요청(2차) | https://garden.r0b.io/notes/192/ , https://github.com/ionic-team/capacitor/issues/5580 | 🟡 |
| 자동재생 정책 | https://webkit.org/blog/6784/new-video-policies-for-ios/ | ✅ |
| playbackRate(옛 문서) | https://developer.apple.com/library/safari/documentation/audiovideo/conceptual/using_html5_audio_video/Device-SpecificConsiderations/Device-SpecificConsiderations.html | ✅(오래됨) |
| ITP 7일 / 홈 화면 예외 | https://webkit.org/tracking-prevention/ , https://webkit.org/blog/10218/full-third-party-cookie-blocking-and-more/ | ✅ |
| MediaRecorder | https://webkit.org/blog/11353/mediarecorder-api/ , https://addpipe.com/media-recorder-api-demo/ | ✅/🟡 |
| AudioWorklet 샘플레이트 버그 | https://bugs.webkit.org/show_bug.cgi?id=244203 | ✅ |
| iOS 웹 푸시 조건 | https://documentation.onesignal.com/docs/en/web-push-for-ios , https://github.com/andreinwald/webpush-ios-example | 🟡 |
| 웹 푸시 안정성 | https://developer.apple.com/forums/thread/728796 , https://developer.apple.com/forums/thread/786360 , https://meta.discourse.org/t/ios-notifications-can-lose-permission-to-push-if-the-user-is-currently-active/290225 | 🟡 |
| Declarative Web Push | https://webkit.org/blog/16535/meet-declarative-web-push/ , https://webkit.org/blog/16574/ (Safari 18.4) | ✅ |

### Azure
| 주제 | 출처 | 신뢰도 |
|---|---|---|
| 가격·무료 한도 | https://azure.microsoft.com/en-us/pricing/details/speech/ | ✅ |
| 할당량·한도 | https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-services-quotas-and-limits | ✅ |
| F0 초과 시 동작 | https://learn.microsoft.com/en-us/answers/questions/5566384/ , https://learn.microsoft.com/en-us/answers/questions/1642305/ | 🟡 |
| STT 무음 과금 | https://learn.microsoft.com/en-us/answers/questions/1299865/ | 🟡 |
| TTS 과금 글자 | https://docs.azure.cn/en-us/ai-services/speech-service/text-to-speech | ✅ |
| 발음 평가 how-to | https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment | ✅ |
| PronunciationAssessmentConfig (JS) | https://learn.microsoft.com/en-us/javascript/api/microsoft-cognitiveservices-speech-sdk/pronunciationassessmentconfig | ✅ |
| 발음 평가 과금 | https://learn.microsoft.com/en-us/answers/questions/5608069/ | 🟡 |
| REST 단문 API(오디오 형식) | https://learn.microsoft.com/en-in/azure/ai-services/speech-service/rest-speech-to-text-short | ✅ |
| 토큰 발급 | https://learn.microsoft.com/en-za/Azure/ai-services/speech-service/rest-text-to-speech | ✅ |
| recognizeOnce 최대 길이 | https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.speechrecognizer | ✅ |
| 음성 목록(2차) | https://docs.signalwire.com/voice/tts/azure , https://json2video.com/ai-voices/azure/voices/ | 🟡 |

### 교수법 / 평가 / 학습 이론
| 주제 | 출처 | 신뢰도 |
|---|---|---|
| 청화식 drill 정의 | https://lecture-notes.tiu.edu.iq/wp-content/uploads/2021/02/CHAPTER-4-THE-AUDIO-LINGUAL-METHOD.pdf , https://c036.wzu.edu.tw/datas/upload/files/EMI%E7%B7%9A%E4%B8%8A%E8%BC%94%E5%B0%8E%E6%95%99%E6%9D%90/111-1%20%E5%A4%96%E8%AA%9E%E6%95%99%E5%AD%B8%E6%A6%82%E8%AB%96(Janny)/Unit_3_Audio_Lingual_Method.pdf | 🟡(대학 강의자료) |
| EI 메타분석 | https://www.researchgate.net/publication/353888463_ELICITED_IMITATION_TASKS_AS_A_MEASURE_OF_L2_PROFICIENCY_A_META-ANALYSIS | ✅ |
| EI ETS 보고서 | https://onlinelibrary.wiley.com/doi/full/10.1002/ets2.12338 | ✅ |
| EI 표준화 측정 특성 | https://www.cambridge.org/core/journals/studies-in-second-language-acquisition/article/measurement-properties-of-a-standardized-elicited-imitation-test-an-integrative-data-analysis/D25501C0180D2327C935B8315D97A9AA | ✅ |
| EI ASR 채점 | https://www.researchgate.net/publication/220746202_Elicited_Imitation_as_an_Oral_Proficiency_Measure_with_ASR_Scoring | ✅ |
| EI EFL 교실 | https://files.eric.ed.gov/fulltext/EJ1463869.pdf | ✅ |
| MST misrouting | https://www.ets.org/research/policy_research_reports/publications/report/2014/jseg.html | ✅ |
| MST 기초 | https://cran.r-universe.dev/dexterMST/doc/multistage_fundamentals.Rmd | ✅ |
| CEFR Companion Volume | https://rm.coe.int/cefr-companion-volume-with-new-descriptors-2018/1680787989 | ✅ |
| 완전학습 기준 | https://www.gwern.net/doc/psychology/1987-slavin.pdf , https://d.lib.msu.edu/etd/25195 | ✅ |
| 85% 규칙 | https://doaj.org/article/d1aeacdf1f304a25962f05454cebb437 (Nature Communications 10:4646) | ✅ |
| 정규화(Whisper) | https://arxiv.org/pdf/2212.04356 | ✅ |
| 숫자 정규화와 WER | https://arxiv.org/pdf/2609.21084 | ✅ |

---

## 13. plan.md로 넘기기 전에 사용자가 정해야 할 것

| # | 질문 | 선택지 | 리서치 추천 |
|---|---|---|---|
| Q1 | 마이크 인식 1순위 | (a) Azure STT 1순위 + 내장 STT는 실기기에서 되면 보너스 (b) 원래대로 내장 STT 1순위 | **(a)** — 2-1 |
| Q2 | 고급 레벨 20분 맞추기 | 10-5의 (a)/(b)/(c)/(d) | **(d)** 6턴 대화 + 파생 2개 |
| Q3 | 발음 평가 호출 방식 | (i) 프롬프트대로 버튼 누를 때만 별도 호출(녹음 재전송) (ii) 인식 요청에 합쳐서 받고 버튼은 "표시"만 | **(ii)** — 단 F0에서 추가 소모 없는지 실기기 확인 후 |
| Q4 | 저녁 20:00에 오늘 아침을 안 했을 때 | 알림 안 보냄 / "아침 학습 아직 안 했어요" 알림 | 리마인더 보냄(설정으로 끌 수 있게) |
| Q5 | 퀴즈 출제 중복 회피 범위 | 직전 퀴즈만 / 그 표현에서 이미 나온 쌍 전부 | **이미 나온 쌍 전부** — 9-1 #10 |
| Q6 | 콘텐츠 생성 범위 | 3레벨 30일 전부 / 현재 레벨 + 다음 레벨만 | 레벨 테스트 후 결정 → **현재+다음** (TTS 절약, 품질 검수 부담 감소) |
| Q7 | "나" 음성 성별 | 남성(Andrew) / 여성 | 사용자 선택 |
| Q8 | 승급 판정 보완(8-2) 적용 | 그대로 85%/10일 / 보완 규칙 포함 | **보완 포함** |

---

## 14. 실기기 확인 체크리스트 (구현 1단계 "스파이크"로 제안)

> 문서로 확정 못 한 것들. **사용자 아이폰 + 사용자 iOS 버전**에서 30분짜리 테스트 페이지로 확인하고, 결과에 따라 설정값을 확정한다. (구현 단계 첫 작업으로 plan.md에 넣을 예정)

| # | 확인할 것 | 성공 기준 | 실패 시 |
|---|---|---|---|
| T1 | 홈 화면 앱에서 `webkitSpeechRecognition` 존재 + 결과 수신 | 5문장 연속 결과 수신 | Azure 전용(S3+S5) |
| T2 | 원어민 mp3 재생 직후 내장 STT 시작 | 소리 받음 | 내장 STT 미사용 |
| T3 | 마이크 권한 팝업 빈도 | 앱 실행당 1회 이하 | UX 문구로 안내 |
| T4 | `playbackRate = 0.75` + `preservesPitch` | 느려지고 음높이 유지 | Web Audio 대체 |
| T5 | AudioWorklet 녹음 샘플레이트 | 48k→16k 리샘플 후 Azure 인식 정상 | ScriptProcessor 대체 |
| T6 | Azure F0 키로 발음 평가 + prosody 1회 | 점수 반환 | 발음 평가 OFF(텍스트 비교만) |
| T7 | 푸시 구독 → pg_cron 매분 → 발송 | 지정 시각 ±1분 내 도착 | 스케줄러 재검토 |
| T8 | 앱 완전 종료 상태에서 푸시 수신 + 탭 시 해당 화면 열림 | 정상 | 서비스 워커 `notificationclick` 수정 |
| T9 | Azure 토큰 함수 — 로그인 안 한 요청 차단 | 401 | 보안 수정 |

---

*리서치 단계 종료. 13장 질문에 대한 답과 함께 승인해 주면 plan.md를 작성한다.*
