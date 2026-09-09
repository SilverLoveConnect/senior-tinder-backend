import uuid as uuid_lib
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.matching import Block, ChatMessage, ChatRoom, Match
from app.models.user import User
from app.services.fcm import notify_new_message

router = APIRouter(prefix="/chat", tags=["chat"])


class SendMessageRequest(BaseModel):
    content: str


def _get_room_or_403(db: Session, room_id: str, current_user: User) -> ChatRoom:
    """채팅방 조회 + 현재 유저가 참여자인지 검증"""
    try:
        room_uuid = UUID(room_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")

    room = db.query(ChatRoom).filter(ChatRoom.id == room_uuid).first()
    if not room:
        raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")

    # 현재 유저가 해당 매칭의 참여자인지 확인
    match = db.query(Match).filter(Match.id == room.match_id).first()
    if not match or current_user.id not in (match.user1_id, match.user2_id):
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    # 차단 관계면 대화를 막는다. 참여자 검증만으로는 차단 후에도 메시지가
    # 그대로 오가고 상대 폰에 푸시까지 가서, 앱이 안내한 차단 효과가 없다.
    opponent_id = (
        match.user2_id if match.user1_id == current_user.id else match.user1_id
    )
    blocked = (
        db.query(Block)
        .filter(
            or_(
                and_(
                    Block.blocker_id == current_user.id,
                    Block.blocked_id == opponent_id,
                ),
                and_(
                    Block.blocker_id == opponent_id,
                    Block.blocked_id == current_user.id,
                ),
            )
        )
        .first()
    )
    if blocked:
        raise HTTPException(status_code=403, detail="차단된 상대와는 대화할 수 없습니다.")

    return room


@router.post("/rooms/{room_id}/messages")
def send_message(
    room_id: str,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """메시지 전송 — AI 스캠 감지 후 DB 저장"""
    room = _get_room_or_403(db, room_id, current_user)

    # 한쪽이 나간 대화에는 더 이상 쓸 수 없다. 막지 않으면 목록에서 사라진
    # 상대에게 메시지와 푸시가 계속 가고, 받는 쪽은 답할 방법이 없다.
    if not room.is_active:
        raise HTTPException(status_code=400, detail="종료된 대화입니다.")

    # AI 서버 스캠 감지 (실패해도 메시지 전송 허용)
    is_scam = False
    scam_type = None
    try:
        res = httpx.post(
            f"{settings.AI_API_URL}/api/v1/nlp/scam",
            json={
                "message_id": str(uuid_lib.uuid4()),
                "sender_id": str(current_user.id),
                "receiver_id": "",
                "content": body.content,
                "room_id": room_id,
            },
            timeout=2,
        )
        if res.status_code == 200:
            data = res.json()
            is_scam = data.get("is_scam", False)
            scam_type = data.get("scam_type")
    except Exception:
        pass

    msg = ChatMessage(
        room_id=room.id,
        sender_id=current_user.id,
        content=body.content,
        is_scam=is_scam,
        scam_type=scam_type,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    match = db.query(Match).filter(Match.id == room.match_id).first()
    opponent_id = match.user2_id if match.user1_id == current_user.id else match.user1_id
    opponent = db.query(User).filter(User.id == opponent_id).first()
    if opponent and opponent.fcm_token and opponent.chat_push_enabled:
        notify_new_message(
            token=opponent.fcm_token,
            sender_nickname=current_user.nickname or current_user.name,
            message=body.content,
            room_id=str(room.id),
        )

    return {
        "id": str(msg.id),
        "sender_id": str(msg.sender_id),
        "content": msg.content,
        "is_scam": msg.is_scam,
        "scam_type": msg.scam_type,
        "is_read": msg.is_read,
        "created_at": str(msg.created_at),
    }


@router.post("/rooms/{room_id}/leave")
def leave_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """채팅방 나가기.

    방은 매칭 1건에 1개(1:1)라서 한쪽만 남기고 유지할 수가 없다. 상대만 계속
    쓸 수 있게 두면 답이 오지 않는 방에 계속 말을 걸게 되므로, 방 자체를
    비활성으로 내려 양쪽 목록에서 사라지게 한다. 앱도 "상대방도 이 대화를 볼
    수 없어요"라고 미리 알린다.

    매칭 기록(Like·Match)은 남긴다. 지우면 상대가 다시 추천 카드로 떠서
    나간 대화를 또 시작하게 된다.
    """
    room = _get_room_or_403(db, room_id, current_user)

    if room.is_active:
        room.is_active = False
        db.commit()

    return {"left": True}


@router.get("/rooms/{room_id}/messages")
def get_messages(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """채팅 이력 조회"""
    room = _get_room_or_403(db, room_id, current_user)

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.room_id == room.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        {
            "id": str(m.id),
            "sender_id": str(m.sender_id),
            "content": m.content,
            "is_scam": m.is_scam,
            "scam_type": m.scam_type,
            "is_read": m.is_read,
            "created_at": str(m.created_at),
        }
        for m in messages
    ]
