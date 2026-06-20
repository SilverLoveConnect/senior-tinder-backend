import uuid as uuid_lib
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.matching import ChatMessage, ChatRoom, Match
from app.models.user import User

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

    return {
        "id": str(msg.id),
        "sender_id": str(msg.sender_id),
        "content": msg.content,
        "is_scam": msg.is_scam,
        "scam_type": msg.scam_type,
        "is_read": msg.is_read,
        "created_at": str(msg.created_at),
    }


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
