from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..decision_engine import compute_node_status
from ..schemas import SystemStatusOut
from ..security import get_current_username

router = APIRouter(prefix="/system", tags=["system"], dependencies=[Depends(get_current_username)])


@router.get("/status", response_model=SystemStatusOut)
def system_status(db: Session = Depends(get_db)):
    nodes = db.query(models.Node).all()
    online = sum(1 for n in nodes if compute_node_status(n) == "online")
    active_alerts = (
        db.query(models.Alert).filter(models.Alert.status == models.AlertStatus.ACTIVE).count()
    )
    return SystemStatusOut(
        total_nodes=len(nodes),
        online_nodes=online,
        offline_nodes=len(nodes) - online,
        active_alerts=active_alerts,
    )
