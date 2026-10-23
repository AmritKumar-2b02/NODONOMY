from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..schemas import AlertOut
from ..security import get_current_username

router = APIRouter(prefix="/alerts", tags=["alerts"], dependencies=[Depends(get_current_username)])


@router.get("", response_model=list[AlertOut])
def list_alerts(status_filter: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Alert)
    if status_filter:
        q = q.filter(models.Alert.status == status_filter)
    return q.order_by(models.Alert.detected_at.desc()).all()


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = models.AlertStatus.ACKNOWLEDGED
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = models.AlertStatus.RESOLVED
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert
