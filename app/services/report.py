from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportRequest
from app.services.manner import update_trust_score
from app.models.manner import MannerFactorEnum


def create_report(db: Session, current_user: User, data: ReportRequest) -> dict:
    exited_user = db.query(User).filter(User.id == data.reported_id).first()
    if not exited_user:
        raise HTTPException(status_code=404, detail="존재하지 않는 유저입니다.")

    if data.reported_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="본인 신고는 불가합니다."
        )

    reported_before = (
        db.query(Report)
        .filter(
            Report.reporter_id == current_user.id,
            Report.reported_id == data.reported_id,
        )
        .first()
    )
    if reported_before:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="중복 신고는 불가합니다."
        )
    report = Report(
        reporter_id=current_user.id,
        reported_id=data.reported_id,
        reason=data.reason,
    )
    db.add(report)
    db.flush()

    update_trust_score(
        db=db,
        user=exited_user,
        factor=MannerFactorEnum.report,
        delta=-10,
        reason=f"신고 접수 ({data.reason[:20]})",
    )
    report_count = (
        db.query(Report).filter(Report.reported_id == data.reported_id).count()
    )
    if report_count >= 3:
        exited_user.is_banned = True

    db.commit()
    return {"message": "신고가 접수됐습니다."}
