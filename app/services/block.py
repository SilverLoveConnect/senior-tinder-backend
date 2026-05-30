from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.matching import Block
from app.models.user import User
from app.schemas.block import BlockListResponse


def create_block(db: Session, current_user: User, target_user_id: str) -> dict:

    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="등록되지 않은 회원입니다."
        )
    block = Block(blocker_id=current_user.id, blocked_id=target_user_id)
    db.add(block)
    db.commit()
    return {"message": "차단됐습니다."}


def delete_block(db: Session, current_user: User, target_user_id: str) -> dict:
    block = (
        db.query(Block)
        .filter(
            Block.blocker_id == current_user.id,
            Block.blocked_id == target_user_id,
        )
        .first()
    )
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="차단 내역이 없습니다."
        )
    db.delete(block)
    db.commit()
    return {"message": "차단이 해제됐습니다."}


def get_blocks(db: Session, current_user: User) -> dict:
    blocks = db.query(Block).filter(Block.blocker_id == current_user.id).all()
    blocked_users = [block.blocked for block in blocks]
    return {"blocks": blocked_users}
