from app.services.content_filter import find_violation

# 중장년 자기소개에 실제로 나올 법한 정상 문장 — 하나라도 막히면 오탐이다.
OK = [
    "주말마다 등산을 하며 자연과 가까워지고, 독서와 요가를 즐깁니다.",
    "아직 해보지 못한 일이 많아 새로운 분과 여행을 다니고 싶어요.",
    "남자지만 요리를 좋아해서 반찬도 곧잘 만듭니다.",
    "허리띠를 졸라매고 살아왔지만 이제는 여유를 즐기려 합니다.",
    "저녁엔 텔레비전으로 드라마를 보고 라인댄스 교실에 다녀요.",
    "카톡은 잘 못해서 천천히 대화 나눠요.",
    "은행에서 30년 일하고 은퇴했습니다.",
    "1965년생, 서울 마포구에 삽니다. 키 170cm.",
    "섹시한 옷보다 편한 옷이 좋아요.",
    None, "",
]
BAD = {
    "시 발 진짜": "abusive",
    "조건만남 구해요": "abusive",
    "fuck you": "abusive",
    "010-1234-5678로 연락주세요": "contact",
    "01012345678 문자주세요": "contact",
    "오픈채팅으로 오세요": "contact",
    "카톡 아이디 abc123": "contact",
    "텔레그램 주세요": "contact",
    "제 블로그 www.example.com": "contact",
    "메일 abc@naver.com": "contact",
    "계좌번호 알려드릴게요": "money",
    "코인투자로 수익 냈어요": "money",
    "110-123-456789 입금": "money",
}


def test_ok_sentences_pass():
    for s in OK:
        assert find_violation(s) is None, s


def test_bad_sentences_blocked():
    for s, kind in BAD.items():
        assert find_violation(s) == kind, (s, find_violation(s))
