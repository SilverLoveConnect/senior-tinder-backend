"""추가 검증 — FCM 토큰 중복, 탈퇴자 대화 표시, 사진 검수 노출.

qa_play_store.py 와 동일한 로컬 QA 환경을 전제로 한다(운영 DB 연결 금지).

실행:
    uv run python scripts/qa_play_store_extra.py
"""
import subprocess, httpx
BASE="http://127.0.0.1:8000"; c=httpx.Client(base_url=BASE,timeout=20)
def psql(sql):
    return subprocess.run(["su","postgres","-c",f'psql -At -d sinabro -c "{sql}"'],
                          capture_output=True,text=True).stdout.strip()
def relax(p): psql(f"delete from sms_send_logs where phone='{p}'")
def code_for(p): return psql(f"select code from sms_verifications where phone='{p}' and is_used=false order by created_at desc limit 1")
def H(t): return {"Authorization": f"Bearer {t}"}
def signup(phone,name,nick,age,gender):
    c.post("/auth/sms/send",json={"phone":phone}); code=code_for(phone)
    c.post("/auth/sms/verify",json={"phone":phone,"code":code})
    r=c.post("/auth/register",json={"phone":phone,"code":code,"name":name,"nickname":nick,
                                    "age":age,"gender":gender,"region":"서울"})
    uid=r.json()["id"]; relax(phone)
    c.post("/auth/sms/send",json={"phone":phone}); c2=code_for(phone)
    t=c.post("/auth/login",json={"phone":phone,"code":c2}).json()
    return uid,t["access_token"],t.get("refresh_token")

def rec(i,n,st,d): print(f"[{st}] {i} {n}\n       {d}")

u1,t1,_=signup("01022220001","가입일","유저1",60,"male")
u2,t2,_=signup("01022220002","가입이","유저2",61,"male")
SHARED="shared-device-fcm-token-AAA"
c.post("/users/me/fcm-token",headers=H(t1),json={"fcm_token":SHARED})
c.post("/users/me/fcm-token",headers=H(t2),json={"fcm_token":SHARED})
cnt=psql(f"select count(*) from users where fcm_token='{SHARED}'")
rec("L-01","기기 공유·재로그인 시 FCM 토큰 중복","FAIL" if cnt!="1" else "PASS",
    f"동일 토큰을 보유한 계정 수={cnt} — 토큰을 다른 계정에서 회수하지 않아, 한 기기를 두 사람이 쓰거나 "
    "계정을 갈아탄 경우 이전 사용자에게 남의 매칭·메시지 알림(본문 50자 포함)이 그대로 발송됨")

u3,t3,_=signup("01022220003","여성일","여1",59,"female")
c.post(f"/matching/like/{u3}",headers=H(t1)); lk=c.post(f"/matching/like/{u1}",headers=H(t3))
room=lk.json()["chat_room_id"]
c.post(f"/chat/rooms/{room}/messages",headers=H(t1),json={"content":"안녕하세요"})
c.delete("/users/me",headers=H(t1))
r=c.get("/matching/matches",headers=H(t3))
ms=r.json()["matches"]
rec("L-02","상대가 탈퇴한 뒤의 대화 목록","INFO" if ms else "FAIL",
    f"남은 대화 {len(ms)}건, 표시 이름='{ms[0]['user']['nickname'] if ms else '-'}' "
    "— 안내문(계정 삭제 페이지) 문구와 일치하나, 대화방은 활성 상태로 남아 답장을 시도할 수 있음")
if ms:
    r=c.post(f"/chat/rooms/{ms[0]['chat_room_id']}/messages",headers=H(t3),json={"content":"탈퇴자에게 보내는 메시지"})
    rec("L-03","탈퇴한 상대에게 메시지 전송","FAIL" if r.status_code==200 else "PASS",
        f"status={r.status_code} — 탈퇴 계정과의 채팅방을 비활성화하지 않아 메시지가 그대로 저장됨(응답 없는 대화)")

pid=psql(f"insert into user_photos (user_id,s3_url,\\\"order\\\",is_primary,is_approved,review_status,created_at,updated_at) "
         f"values ('{u2}','https://bucket.s3.ap-northeast-2.amazonaws.com/photos/{u2}/x.jpg',0,false,false,'pending',now(),now()) returning id")
r=c.get("/users/me",headers=H(t2))
j=r.json()
rec("L-04","검수 대기·거부 사진의 본인 노출","PASS" if j["pending_photos"] else "FAIL",
    f"photos={len(j['photos'])} pending={len(j['pending_photos'])} rejected={len(j['rejected_photos'])}")
r=c.get("/matching",headers=H(t3))
others=[u for u in r.json()["users"] if u["id"]==u2]
rec("L-05","미승인 사진의 타인 노출 차단","PASS" if others and not others[0]["photos"] else "INFO",
    f"상대 카드 photos={others[0]['photos'] if others else '카드 없음'}")
r=c.get("/internal/photos/pending")
rec("L-06","무인증 /internal 로 검수대기 사진 URL 열람","FAIL" if r.status_code==200 else "PASS",
    f"status={r.status_code}, 반환 건수={len(r.json().get('photos',[])) if r.status_code==200 else '-'}, "
    f"샘플={str(r.json().get('photos',[])[:1])[:150]}")
