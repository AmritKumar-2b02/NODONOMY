from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..decision_engine import compute_node_status
from ..schemas import NodeOut
from ..security import get_current_username

router = APIRouter(prefix="/nodes", tags=["nodes"], dependencies=[Depends(get_current_username)])


def _to_node_out(node: models.Node) -> NodeOut:
    return NodeOut(
        node_id=node.node_id,
        location=node.location,
        status=compute_node_status(node),
        last_battery=node.last_battery,
        last_seen=node.last_seen,
    )


@router.get("", response_model=list[NodeOut])
def list_nodes(db: Session = Depends(get_db)):
    nodes = db.query(models.Node).all()
    return [_to_node_out(n) for n in nodes]


@router.get("/{node_id}", response_model=NodeOut)
def get_node(node_id: str, db: Session = Depends(get_db)):
    node = db.query(models.Node).filter(models.Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return _to_node_out(node)
