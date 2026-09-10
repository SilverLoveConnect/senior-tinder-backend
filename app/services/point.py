from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.point import Point, PointHistory, PointTypeEnum
from app.models.user import User
from app.schemas.point import PointUseRequest


def get_balance(db: Session, current_user: User) -> dict:
    point = db.query(Point).filter(Point.user_id == current_user.id).first()
    return {"balance": point.balance if point else 0}


def get_history(db: Session, current_user: User) -> dict:
    history = (
        db.query(PointHistory)
        .filter(PointHistory.user_id == current_user.id)
        .order_by(PointHistory.created_at.desc())
        .all()
    )
    return {"history": history}


def use_points(db: Session, current_user: User, data: PointUseRequest) -> dict:
    # with_for_update = SELECT ... FOR UPDATE. 잠금이 없으면 동시 요청이 같은
    # 잔액을 읽고 각자 차감해 100P로 200P를 쓸 수 있다(동시성 테스트에서 재현).
    # 지금은 충전 경로가 없어 실피해가 없지만 결제를 켜는 순간 금전 손실이 된다.
    point = (
        db.query(Point)
        .filter(Point.user_id == current_user.id)
        .with_for_update()
        .first()
    )
    if not point or point.balance < data.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="포인트가 부족합니다."
        )
    point.balance -= data.amount
    history = PointHistory(
        user_id=current_user.id,
        amount=-data.amount,
        type=data.type,
        description=data.description,
    )
    db.add(history)
    db.commit()
    return {"balance": point.balance, "used": data.amount}
