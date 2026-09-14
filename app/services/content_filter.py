"""프로필 텍스트(닉네임·자기소개·인생이야기·직업) 금칙 검사.

Apple 가이드라인 1.2와 Google Play 사용자 제작 콘텐츠 정책은 다른 회원에게
노출되는 글에서 부적절한 내용을 걸러내는 수단을 요구한다. 사진에는 AI 검수·신고·
차단이 있었지만 텍스트는 아무 검사 없이 저장 즉시 노출됐다.

모델 없이 규칙으로 막는다. 목표는 '확실히 부적절하거나 앱 밖으로 끌어내려는 글'을
저장 단계에서 막는 것이지 미묘한 표현까지 판정하는 게 아니다. 오탐으로 멀쩡한
중장년 자기소개가 막히면 가입 이탈로 이어지므로 목록을 보수적으로 잡았다.
일상 문장에 흔히 섞이는 단어는 일부러 넣지 않았다:
  "보지"(해보지 못했다) · "자지"(남자지만) · "졸라"(허리띠를 졸라매고) ·
  "텔레"(텔레비전) · "라인"(몸매 라인·라인댄스) · "카톡"(카톡은 잘 못해요)
"""

import re

from fastapi import HTTPException, status

# 띄어쓰기·특수문자를 걷어낸 뒤 부분 문자열로 찾는다("시 발", "섹.스" 우회 방지).
_ABUSIVE = (
    "씨발", "시발", "씨바", "ㅅㅂ", "ㅆㅂ", "병신", "ㅄ", "좆", "존나", "개새끼",
    "새끼야", "썅", "미친년", "미친놈", "닥쳐", "엠창", "느금", "니애미",
    "틀딱", "한남충", "김치녀",
    "섹스", "쎅스", "섹파", "조건만남", "원나잇", "원나이트", "애인대행",
    "용돈만남", "성인만남", "야동",
)
_ABUSIVE_LATIN = re.compile(r"\b(fuck|shit|bitch|sex)\b", re.IGNORECASE)

# 앱 밖 연락 유도 — 로맨스 스캠이 대화를 외부 메신저로 옮기는 첫 단계다.
_CONTACT_WORDS = (
    "카톡아이디", "카톡id", "카카오톡아이디", "오픈채팅", "오픈톡", "텔레그램",
    "라인아이디", "라인id", "위챗", "wechat", "telegram",
)
_PHONE = re.compile(r"01[016789][\s.\-]?\d{3,4}[\s.\-]?\d{4}")
_LINK = re.compile(
    r"(https?://|www\.|[a-z0-9\-]+\.(com|net|org|kr|me|io|ly|kr/)\b|[\w.+\-]+@[\w\-]+\.\w+)",
    re.IGNORECASE,
)

# 금전 유도
_MONEY_WORDS = ("계좌번호", "입금해", "송금해", "코인투자", "리딩방", "투자수익")
_ACCOUNT = re.compile(r"\d{2,6}-\d{2,6}-\d{2,8}")


def _squash(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣ㄱ-ㅎㅏ-ㅣ]", "", text.lower())


def find_violation(text: str | None) -> str | None:
    """위반 종류("abusive" | "contact" | "money")를 돌려준다. 문제없으면 None."""
    if not text:
        return None
    squashed = _squash(text)
    if any(w in squashed for w in _ABUSIVE) or _ABUSIVE_LATIN.search(text):
        return "abusive"
    if (
        any(w in squashed for w in _CONTACT_WORDS)
        or _PHONE.search(text)
        or _LINK.search(text)
    ):
        return "contact"
    if any(w in squashed for w in _MONEY_WORDS) or _ACCOUNT.search(text):
        return "money"
    return None


_MESSAGES = {
    "abusive": "{field}에 사용할 수 없는 표현이 들어 있어요. 다른 표현으로 바꿔주세요.",
    "contact": "{field}에는 연락처·메신저 아이디·링크를 적을 수 없어요. 대화는 앱 안에서 나눠주세요.",
    "money": "{field}에는 계좌나 송금·투자 관련 내용을 적을 수 없어요.",
}


def check_profile_text(field: str, text: str | None) -> None:
    """위반이면 400. 메시지는 앱에 그대로 보여줄 수 있는 문장이다."""
    kind = find_violation(text)
    if kind:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_MESSAGES[kind].format(field=field),
        )
