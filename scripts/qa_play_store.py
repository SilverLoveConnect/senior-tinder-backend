"""Google Play 심사 관점 백엔드 E2E QA — 로컬 실서버(127.0.0.1:8000) 대상.

경고: 실행 시작 시 로컬 QA DB(sinabro)의 모든 테이블을 TRUNCATE 한다.
     반복 실행 결과를 동일하게 만들기 위한 것이므로 운영 DB에는 절대 연결하지 말 것.

사전 준비:
    service postgresql start
    su postgres -c "createdb sinabro"
    su postgres -c "psql -d sinabro -c 'CREATE EXTENSION IF NOT EXISTS pgcrypto;'"
    uv run alembic upgrade head
    uv run uvicorn app.main:app --host 127.0.0.1 --port 8000

실행:
    uv run python scripts/qa_play_store.py
"""
import json, subprocess, sys, uuid
import httpx

BASE = "http://127.0.0.1:8000"
c = httpx.Client(base_url=BASE, timeout=20)
RESULTS = []

def psql(sql):
    r = subprocess.run(["su", "postgres", "-c", f'psql -At -d sinabro -c "{sql}"'],
                       capture_output=True, text=True)
    return r.stdout.strip()

def rec(id_, name, status, detail):
    RESULTS.append((id_, name, status, detail))
    mark = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN", "INFO": "INFO"}[status]
    print(f"[{mark}] {id_} {name}\n       {detail}")

def code_for(phone):
    return psql(f"select code from sms_verifications where phone='{phone}' and is_used=false order by created_at desc limit 1")

def relax(phone):
    """1분 rate limit 통과를 위해 발송 로그를 비운다(시간 경과 시뮬레이션)."""
    psql(f"delete from sms_send_logs where phone='{phone}'")

def signup(phone, name, nick, age, gender, region="서울"):
    c.post("/auth/sms/send", json={"phone": phone})
    code = code_for(phone)
    c.post("/auth/sms/verify", json={"phone": phone, "code": code})
    r = c.post("/auth/register", json={"phone": phone, "code": code, "name": name,
                                       "nickname": nick, "age": age, "gender": gender,
                                       "region": region, "marketing_consent": False})
    assert r.status_code == 200, (phone, r.status_code, r.text)
    uid = r.json()["id"]
    relax(phone)
    c.post("/auth/sms/send", json={"phone": phone})
    code2 = code_for(phone)
    lr = c.post("/auth/login", json={"phone": phone, "code": code2})
    assert lr.status_code == 200, lr.text
    tok = lr.json()
    return uid, tok["access_token"], tok.get("refresh_token")

def H(t): return {"Authorization": f"Bearer {t}"}

# --- 테스트 시작 전 DB 초기화(멱등 실행 보장) ---
subprocess.run(["su","postgres","-c",
  'psql -q -d sinabro -c "TRUNCATE users, user_profiles, user_photos, likes, matches, chat_rooms, '
  'chat_messages, blocks, reports, points, point_history, payments, subscriptions, badges, boosts, '
  'manner_history, sms_verifications, sms_send_logs RESTART IDENTITY CASCADE;"'],
  capture_output=True, text=True)

print("=" * 70)
print("STEP 1. 심사관 전용 고정코드 로그인 경로 (Play 리뷰어 계정)")
print("=" * 70)
RP = "01099998888"
r = c.post("/auth/sms/send", json={"phone": RP})
r2 = c.post("/auth/sms/verify", json={"phone": RP, "code": "112233"})
r3 = c.post("/auth/register", json={"phone": RP, "code": "112233", "name": "심사관",
                                    "nickname": "리뷰어", "age": 55, "gender": "male", "region": "서울"})
rec("A-01", "REVIEW_TEST_PHONE 고정코드 가입",
    "PASS" if r3.status_code == 200 else "FAIL",
    f"sms/send={r.status_code} verify={r2.status_code} register={r3.status_code} {r3.text[:120]}")
c.post("/auth/sms/send", json={"phone": RP})
rl = c.post("/auth/login", json={"phone": RP, "code": "112233"})
rec("A-02", "심사관 고정코드 반복 로그인(횟수 제한 없이 재사용)",
    "PASS" if rl.status_code == 200 else "FAIL", f"login={rl.status_code}")
rl2 = c.post("/auth/login", json={"phone": RP, "code": "112233"})
rec("A-03", "심사관 계정 — sms/send 재호출 없이 곧바로 재로그인", "INFO",
    f"login(재호출 없음)={rl2.status_code} {rl2.text[:80]} — 앱은 항상 인증번호 요청을 먼저 하므로 "
    "정상 흐름에는 영향 없음. 심사용 번호는 1분 rate limit을 우회하므로 재요청이 곧바로 성공한다")
rev_tok = rl.json()["access_token"]

print()
print("=" * 70)
print("STEP 2. 일반 회원가입 / SMS 인증 보안")
print("=" * 70)
NP = "01011119999"
c.post("/auth/sms/send", json={"phone": NP})
_c = code_for(NP)
c.post("/auth/sms/verify", json={"phone": NP, "code": _c})
_reg = c.post("/auth/register", json={"phone": NP, "code": _c, "name": "신규가입",
                                      "nickname": "신규", "age": 60, "gender": "male"})
_tok_in_reg = [k for k in _reg.json().keys() if "token" in k]
_login_now = c.post("/auth/login", json={"phone": NP, "code": _c})
_resend = c.post("/auth/sms/send", json={"phone": NP})
rec("B-00", "가입 완료 직후 로그인 가능 여부",
    "FAIL" if (not _tok_in_reg and _login_now.status_code != 200 and _resend.status_code == 429) else "PASS",
    f"register 응답에 토큰 {('있음' if _tok_in_reg else '없음')} / "
    f"방금 인증한 코드로 login={_login_now.status_code}({_login_now.json().get('detail')}) / "
    f"인증번호 재요청={_resend.status_code}({_resend.json().get('detail')}) "
    "→ 가입 직후 로그인 경로가 막혀 최대 1분 대기해야 함")
relax(NP)

uid_a, tok_a, ref_a = signup("01011110001", "김철수", "철수", 62, "male")
uid_b, tok_b, ref_b = signup("01011110002", "이영희", "영희", 58, "female")
rec("B-01", "일반 가입+로그인 정상 동작", "PASS", f"userA={uid_a[:8]} userB={uid_b[:8]}")

r = c.post("/auth/sms/send", json={"phone": "01011110003"})
r2 = c.post("/auth/sms/send", json={"phone": "01011110003"})
rec("B-02", "SMS 재발송 1분 rate limit", "PASS" if r2.status_code == 429 else "FAIL",
    f"1회={r.status_code} 2회={r2.status_code}")

r = c.post("/auth/register", json={"phone": "01011110004", "code": "123456", "name": "미성년",
                                   "nickname": "미성년", "age": 30, "gender": "male"})
rec("B-03", "만 50세 미만 가입 차단(연령 하한)", "PASS" if r.status_code == 422 else "FAIL",
    f"status={r.status_code}")

# register 무차별 대입: 피해자가 인증만 마치고 가입 안 한 15분 창
VP = "01011110005"
c.post("/auth/sms/send", json={"phone": VP})
vcode = code_for(VP)
c.post("/auth/sms/verify", json={"phone": VP, "code": vcode})
fails = 0
blocked_at = None
for i in range(60):
    guess = f"{i:06d}"
    rr = c.post("/auth/register", json={"phone": VP, "code": guess, "name": "공격자",
                                        "nickname": "공격자", "age": 60, "gender": "male"})
    if rr.status_code in (429, 403):
        blocked_at = i
        break
    fails += 1
rec("B-04", "register 코드 무차별 대입 시도 제한",
    "FAIL" if blocked_at is None else "PASS",
    f"틀린 코드 {fails}회 연속 시도 — 차단/지연 없음(모두 400)" if blocked_at is None
    else f"{blocked_at}회에서 차단")
rr = c.post("/auth/register", json={"phone": VP, "code": vcode, "name": "공격자",
                                    "nickname": "공격자", "age": 60, "gender": "male"})
rec("B-05", "무차별 대입 후 정답 코드로 타인 번호 가입 성공 여부",
    "FAIL" if rr.status_code == 200 else "PASS",
    f"정답 코드 register={rr.status_code} → 15분 창 안에서 6자리 전수조사 시 타인 번호 계정 생성 가능")

r = c.post("/auth/sms/verify", json={"phone": "01011110002", "code": "000000"})
rec("B-06", "verify 5회 실패 시 코드 폐기", "INFO", f"단건 오답 응답={r.status_code} (코드상 5회 후 is_used=True)")

print()
print("=" * 70)
print("STEP 3. 매칭 / 좋아요 / 채팅 (Play UGC 핵심 플로우)")
print("=" * 70)
r = c.get("/matching", headers=H(tok_a))
rec("C-01", "매칭 추천 목록 조회", "PASS" if r.status_code == 200 else "FAIL",
    f"status={r.status_code} 노출 {len(r.json().get('users', []))}명, 필드={list((r.json().get('users') or [{}])[0].keys())}")
leaked = [k for k in (r.json().get("users") or [{}])[0].keys() if k in ("phone", "name")]
rec("C-02", "추천 카드에 실명/전화번호 미노출", "PASS" if not leaked else "FAIL",
    f"노출 필드={leaked or '없음'}")

c.post(f"/matching/like/{uid_b}", headers=H(tok_a))
r = c.post(f"/matching/like/{uid_a}", headers=H(tok_b))
room = r.json().get("chat_room_id")
rec("C-03", "상호 좋아요 → 매칭+채팅방 생성", "PASS" if r.json().get("is_matched") else "FAIL",
    f"{r.json()}")

r = c.post(f"/chat/rooms/{room}/messages", headers=H(tok_a), json={"content": "안녕하세요 반갑습니다"})
rec("C-04", "채팅 메시지 전송", "PASS" if r.status_code == 200 else "FAIL", f"status={r.status_code}")

r = c.get("/matching/matches", headers=H(tok_b))
m = r.json()["matches"][0]
rec("C-05", "대화 목록 unread_count 표시", "PASS" if m["unread_count"] == 1 else "FAIL",
    f"unread_count={m['unread_count']}")
c.get(f"/chat/rooms/{room}/messages", headers=H(tok_b))
r = c.get("/matching/matches", headers=H(tok_b))
m2 = r.json()["matches"][0]
rec("C-06", "메시지 조회 후 읽음 처리 → unread_count 감소",
    "PASS" if m2["unread_count"] == 0 else "FAIL",
    f"이력 조회 후에도 unread_count={m2['unread_count']} — is_read를 갱신하는 코드 경로가 없음(배지 영구 잔존)")

uid_c, tok_c, _ = signup("01011110006", "박무단", "무단", 61, "male")
r = c.get(f"/chat/rooms/{room}/messages", headers=H(tok_c))
rec("C-07", "제3자의 타인 채팅방 접근 차단", "PASS" if r.status_code == 403 else "FAIL",
    f"status={r.status_code}")

print()
print("=" * 70)
print("STEP 4. 차단 / 신고 (Play UGC 정책 필수 요건)")
print("=" * 70)
r = c.post(f"/blocks/{uid_b}", headers=H(tok_a))
rec("D-01", "사용자 차단 API", "PASS" if r.status_code == 200 else "FAIL", f"status={r.status_code}")
r = c.get("/blocks", headers=H(tok_a))
bl = r.json()["blocks"][0]
real_name = psql(f"select name from users where id='{uid_b}'")
db_nick = psql(f"select nickname from users where id='{uid_b}'")
rec("D-02", "차단 목록 응답의 개인정보 노출",
    "FAIL" if bl["nickname"] == real_name else "PASS",
    f"nickname 필드값='{bl['nickname']}' / DB 실명='{real_name}' / DB 닉네임='{db_nick}'"
    " → 스키마가 validation_alias='name'이라 닉네임 자리에 실명을 반환")

r = c.get("/matching/matches", headers=H(tok_a))
rec("D-03", "차단 후 대화 목록에서 제거", "PASS" if len(r.json()["matches"]) == 0 else "FAIL",
    f"남은 대화 {len(r.json()['matches'])}건")
r = c.post(f"/chat/rooms/{room}/messages", headers=H(tok_b), json={"content": "차단당한 쪽에서 전송"})
rec("D-04", "차단당한 쪽의 메시지 전송 차단", "PASS" if r.status_code == 403 else "FAIL",
    f"status={r.status_code}")
r = c.get("/matching", headers=H(tok_b))
ids = [u["id"] for u in r.json()["users"]]
rec("D-05", "차단 관계 양방향 피드 제외", "PASS" if uid_a not in ids else "FAIL",
    f"차단한 상대가 피드에 {'있음' if uid_a in ids else '없음'}")

r = c.post("/reports", headers=H(tok_a), json={"reported_id": uid_c, "reason": "부적절한 메시지를 반복적으로 보냅니다"})
rec("D-06", "사용자 신고 API", "PASS" if r.status_code == 200 else "FAIL", f"status={r.status_code}")
r = c.post("/reports", headers=H(tok_a), json={"reported_id": uid_c, "reason": "같은 사유로 재신고합니다"})
rec("D-07", "중복 신고 방지", "PASS" if r.status_code == 400 else "FAIL", f"status={r.status_code}")

uid_d, tok_d, _ = signup("01011110007", "최신고", "신고자", 59, "female")
uid_e, tok_e, _ = signup("01011110008", "정신고", "신고자2", 57, "female")
c.post("/reports", headers=H(tok_d), json={"reported_id": uid_c, "reason": "신고 사유 테스트입니다"})
c.post("/reports", headers=H(tok_e), json={"reported_id": uid_c, "reason": "신고 사유 테스트입니다"})
banned = psql(f"select is_banned from users where id='{uid_c}'")
r = c.get("/users/me", headers=H(tok_c))
rec("D-08", "신고 3회 누적 → 자동 정지", "PASS" if banned == "t" and r.status_code == 403 else "FAIL",
    f"is_banned={banned}, 정지 계정 API 접근={r.status_code}")
rec("D-09", "신고 3회 자동 정지의 어뷰징 가능성", "WARN",
    "서로 다른 계정 3개(가입에 SMS 인증만 필요)면 임의 사용자를 즉시 정지시킬 수 있음. "
    "해제 경로는 /internal API뿐이라 앱 내 이의제기 수단 없음")
rec("D-10", "메시지/사진 단위 신고 엔드포인트", "FAIL",
    "신고는 /reports(사용자 단위)만 존재. 특정 메시지·사진을 신고하는 경로가 없어 "
    "Play UGC 정책이 요구하는 '문제 콘텐츠 신고' 요건을 사용자 단위 신고로만 충족")
rec("D-11", "프로필 텍스트(닉네임·자기소개) 모더레이션", "FAIL",
    "AI 검수는 사진(has_face/is_inappropriate)에만 적용. bio·life_story·nickname은 어떤 필터도 거치지 않고 "
    "즉시 다른 회원에게 노출되며, 신고가 들어와도 텍스트만 내리는 수단이 없음(계정 정지뿐)")

print()
print("=" * 70)
print("STEP 5. 결제 — Google Play 결제 정책")
print("=" * 70)
r = c.post("/payments/points/charge", headers=H(tok_a), json={"imp_uid": "imp_x", "package": "basic"})
rec("E-01", "PAYMENTS_ENABLED=false 시 포인트 충전 차단", "PASS" if r.status_code == 404 else "FAIL",
    f"status={r.status_code}")
r = c.post("/payments/subscriptions", headers=H(tok_a), json={"imp_uid": "imp_x", "plan": "gold"})
rec("E-02", "PAYMENTS_ENABLED=false 시 구독 결제 차단", "PASS" if r.status_code == 404 else "FAIL",
    f"status={r.status_code}")
r = c.get("/payments", headers=H(tok_a))
rec("E-03", "결제 이력 조회는 개방(기존 결제자용)", "INFO", f"status={r.status_code}")
r = c.delete("/payments/subscriptions", headers=H(tok_a))
rec("E-04", "구독 해지는 개방", "INFO", f"status={r.status_code}")
r = c.get("/points", headers=H(tok_a))
rec("E-05", "포인트 잔액 조회", "PASS" if r.status_code == 200 else "FAIL", f"{r.status_code} {r.text[:60]}")

print()
print("=" * 70)
print("STEP 6. 내부(관리자) API 노출")
print("=" * 70)
r = c.get("/internal/photos/pending")
rec("F-01", "INTERNAL_TOKEN 미설정 시 관리자 API 무인증 통과",
    "FAIL" if r.status_code == 200 else "PASS",
    f"토큰 헤더 없이 GET /internal/photos/pending = {r.status_code} "
    f"(전 사용자 검수대기 사진 URL과 user_id가 그대로 반환)")
r = c.post(f"/internal/users/{uid_a}/ban", json={"banned": True})
rec("F-02", "무인증 계정 정지 호출", "FAIL" if r.status_code == 200 else "PASS",
    f"status={r.status_code} {r.text[:80]}")
c.post(f"/internal/users/{uid_a}/ban", json={"banned": False})

print()
print("=" * 70)
print("STEP 7. 계정 삭제 (Play '계정 삭제' 정책 필수 요건)")
print("=" * 70)
uid_x, tok_x, ref_x = signup("01011110009", "탈퇴자", "탈퇴자", 60, "male")
c.post("/users/me/fcm-token", headers=H(tok_x), json={"fcm_token": "dummy-fcm-token-1234"})
r = c.delete("/users/me", headers=H(tok_x))
rec("G-01", "앱 내 회원 탈퇴 엔드포인트", "PASS" if r.status_code == 204 else "FAIL", f"status={r.status_code}")
row = psql(f"select phone||'|'||name||'|'||coalesce(nickname,'')||'|'||coalesce(fcm_token,'NULL')||'|'||is_active from users where id='{uid_x}'")
rec("G-02", "탈퇴 시 식별정보 익명화 + FCM 토큰 삭제",
    "PASS" if row.startswith("deleted:") and "NULL" in row else "FAIL", f"users row = {row}")
r = c.get("/users/me", headers=H(tok_x))
rec("G-03", "탈퇴 후 기존 액세스 토큰 무효화", "PASS" if r.status_code == 403 else "FAIL",
    f"status={r.status_code}")
r = c.post("/auth/refresh", json={"refresh_token": ref_x})
rec("G-04", "탈퇴 계정의 refresh 토큰으로 액세스 토큰 재발급",
    "FAIL" if r.status_code == 200 else "PASS",
    f"status={r.status_code} — refresh_access_token()이 is_active/is_banned를 확인하지 않음. "
    "발급된 토큰은 get_current_user에서 막히지만, 정지 계정도 동일하게 토큰을 계속 받아감")
relax("01011110009")
r = c.post("/auth/sms/send", json={"phone": "01011110009"})
code = code_for("01011110009")
r = c.post("/auth/login", json={"phone": "01011110009", "code": code})
rec("G-05", "탈퇴한 번호로 재로그인 불가", "PASS" if r.status_code == 400 else "FAIL", f"status={r.status_code}")
relax("01011110009")
c.post("/auth/sms/send", json={"phone": "01011110009"})
code = code_for("01011110009")
r = c.post("/auth/sms/verify", json={"phone": "01011110009", "code": code})
r = c.post("/auth/register", json={"phone": "01011110009", "code": code, "name": "재가입",
                                   "nickname": "재가입", "age": 60, "gender": "male"})
rec("G-06", "동일 번호 재가입 가능(신규 계정)", "PASS" if r.status_code == 200 else "FAIL", f"status={r.status_code}")
rec("G-07", "탈퇴 시 S3 원본 사진 파기", "FAIL",
    "delete_account()는 user_photos 행만 DELETE하고 S3 객체는 지우지 않음. "
    "DELETE /users/me/photos도 동일. 처리방침 제4조 '저장소 원본 30일 내 파기'를 이행하는 코드/배치가 없음")

print()
print("=" * 70)
print("STEP 8. 개인정보 — 처리방침 대비 실제 동작")
print("=" * 70)
rec("H-01", "채팅 메시지의 외부 전송", "FAIL",
    "app/routers/chat.py:85 — 메시지 원문을 AI_API_URL(외부 스캠탐지 서버)로 POST. "
    "처리방침 제8조 2항은 '회사의 서버 안에서만 이루어지며 메시지 내용이 외부 사업자에게 전송되지 않습니다'라고 명시하고, "
    "제6조 위탁 목록·제7조 국외이전 항목에도 채팅 메시지 수탁자가 없음 → 문서와 코드가 정면으로 불일치")
r = c.get("/users/me", headers=H(tok_a))
rec("H-02", "본인 프로필 응답 필드", "INFO", f"{sorted(r.json().keys())}")
r = c.get(f"{BASE}/openapi.json")
rec("H-03", "프로덕션 API 문서(/docs, /openapi.json) 공개", "WARN",
    f"인증 없이 openapi.json 접근={r.status_code} — 전체 엔드포인트/스키마가 공개. "
    "/internal 관리자 API 경로까지 그대로 노출")

print()
print("=" * 70)
print("STEP 9. 데이터 정합성 / 동시성")
print("=" * 70)
has_point_row = psql(f"select count(*) from points where user_id='{uid_a}'")
rec("J-01", "회원가입 시 포인트 레코드 생성",
    "FAIL" if has_point_row == "0" else "PASS",
    f"가입 직후 points 행 수={has_point_row} — register_user()가 Point를 만들지 않아 "
    "포인트 사용 API가 항상 '포인트가 부족합니다'로 실패. PR #18 설명에 있던 자동 생성 코드가 현재 없음")
psql(f"insert into points (user_id, balance) values ('{uid_a}', 100) "
     f"on conflict (user_id) do update set balance=100")
import concurrent.futures as cf
def use():
    return c.post("/points/use", headers=H(tok_a),
                  json={"amount": 100, "type": "use", "description": "동시성 테스트"}).status_code
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    codes = list(ex.map(lambda _: use(), range(8)))
bal = psql(f"select balance from points where user_id='{uid_a}'")
ok200 = codes.count(200)
rec("I-01", "포인트 차감 동시성(중복 차감)",
    "PASS" if ok200 == 1 and bal == "0" else "FAIL",
    f"100P 잔액에 100P 사용 8회 동시 요청 → 성공 {ok200}건, 최종 잔액={bal} "
    f"(SELECT 후 UPDATE 사이에 잠금이 없어 음수/중복 차감 가능)")

uid_f, tok_f, _ = signup("01011110010", "한나가", "나가기", 63, "male")
uid_g, tok_g, _ = signup("01011110011", "서나가", "나가기2", 61, "female")
c.post(f"/matching/like/{uid_g}", headers=H(tok_f))
_lk = c.post(f"/matching/like/{uid_f}", headers=H(tok_g))
room2 = _lk.json()["chat_room_id"]
r = c.post(f"/chat/rooms/{room2}/leave", headers=H(tok_g))
rec("I-02", "채팅방 나가기", "PASS" if r.status_code == 200 else "FAIL", f"status={r.status_code}")
r = c.post(f"/chat/rooms/{room2}/messages", headers=H(tok_f), json={"content": "나간 뒤 전송"})
rec("I-03", "나간 대화방에 상대가 메시지 전송 시 차단", "PASS" if r.status_code == 400 else "FAIL",
    f"status={r.status_code}")
r = c.post(f"/chat/rooms/{room}/leave", headers=H(tok_b))
rec("I-04", "차단 상태에서 채팅방 나가기", "WARN" if r.status_code == 403 else "PASS",
    f"status={r.status_code} — 차단 관계면 _get_room_or_403이 먼저 403을 내서 방을 나갈 수 없음(목록에선 이미 숨겨짐)")

print()
print("=" * 70)
print("STEP 10. 프로필 / 동의 관리 / 사진 업로드 검증")
print("=" * 70)
r = c.put("/users/me", headers=H(tok_a), json={"nickname": "바뀐닉", "age": 20, "gender": "female"})
after = psql(f"select age||'/'||gender from users where id='{uid_a}'")
rec("K-01", "프로필 수정으로 나이·성별 변조 불가", "PASS" if after.startswith("62") else "FAIL",
    f"수정 요청 후 DB age/gender={after}")
mc_before = psql(f"select marketing_consent from users where id='{uid_a}'")
r1 = c.put("/users/me/settings", headers=H(tok_a), json={"chat_push_enabled": False, "marketing_consent": False})
r2 = c.put("/users/me", headers=H(tok_a), json={"marketing_consent": False})
rec("K-02", "마케팅 수신동의 철회 경로",
    "FAIL",
    f"settings 스키마는 chat_push_enabled만 받음(응답={r1.json()}), 프로필 수정도 marketing_consent 미지원. "
    "가입 시 받은 동의를 앱에서 철회할 API가 없음 — 처리방침 제1조 '동의는 언제든지 철회할 수 있습니다'와 불일치")
r = c.put("/users/me/settings", headers=H(tok_a), json={"chat_push_enabled": False})
push_off = psql(f"select chat_push_enabled from users where id='{uid_a}'")
rec("K-03", "채팅 푸시 수신 거부 설정", "PASS" if push_off == "f" else "FAIL",
    f"status={r.status_code}, DB chat_push_enabled={push_off}")

files = {"file": ("evil.jpg", b"MZ\x90\x00 not an image at all", "image/jpeg")}
r = c.post("/users/me/photos", headers=H(tok_a), files=files)
rec("K-04", "확장자·Content-Type 위조 파일 업로드 차단", "PASS" if r.status_code == 400 else "FAIL",
    f"status={r.status_code} {r.text[:80]}")
files = {"file": ("doc.txt", b"hello", "text/plain")}
r = c.post("/users/me/photos", headers=H(tok_a), files=files)
rec("K-05", "비이미지 Content-Type 차단", "PASS" if r.status_code == 400 else "FAIL", f"status={r.status_code}")

r = c.options("/health", headers={"Origin": "https://evil.example.com",
                                  "Access-Control-Request-Method": "GET"})
rec("K-06", "CORS 설정", "WARN",
    f"Origin=https://evil.example.com 프리플라이트 → allow-origin={r.headers.get('access-control-allow-origin')} "
    "(CORS_ALLOWED_ORIGINS 미설정 시 '*' + allow_credentials=True 조합. 프로덕션 환경변수 설정 필수)")

print()
print("=" * 70)
s = {}
for _, _, st, _ in RESULTS:
    s[st] = s.get(st, 0) + 1
print("요약:", json.dumps(s, ensure_ascii=False))
with open("/tmp/qa_results.json", "w") as f:
    json.dump(RESULTS, f, ensure_ascii=False, indent=2)
