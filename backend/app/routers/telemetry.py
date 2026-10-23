from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..decision_engine import evaluate_reading, evaluate_battery
from ..mqtt_ingest import ingest_packet
from ..schemas import TelemetryOut, TelemetryPacket, APIResponse
from ..security import get_current_username

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

VALID_TAGS = {"temperature", "ir_detected", "vibration", "motion", "battery"}


@router.get("/latest/{node_id}", response_model=TelemetryOut, dependencies=[Depends(get_current_username)])
def latest_telemetry(node_id: str, db: Session = Depends(get_db)):
    reading = (
        db.query(models.SensorReading)
        .filter(models.SensorReading.node_id == node_id)
        .order_by(models.SensorReading.timestamp.desc())
        .first()
    )
    if not reading:
        raise HTTPException(status_code=404, detail="No telemetry for this node yet")
    return reading


@router.get("/history/{node_id}", response_model=list[TelemetryOut], dependencies=[Depends(get_current_username)])
def historical_telemetry(
    node_id: str,
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(models.SensorReading).filter(models.SensorReading.node_id == node_id)
    if start:
        q = q.filter(models.SensorReading.timestamp >= start)
    if end:
        q = q.filter(models.SensorReading.timestamp <= end)
    return q.order_by(models.SensorReading.timestamp.asc()).limit(limit).all()


@router.get("/search", dependencies=[Depends(get_current_username)])
def search_telemetry(
    start: Optional[datetime] = Query(None, description="Start of the time window (ISO 8601)"),
    end: Optional[datetime] = Query(None, description="End of the time window (ISO 8601)"),
    tags: Optional[str] = Query(None, description="Comma-separated sensor fields: temperature,ir_detected,vibration,motion,battery"),
    limit: int = Query(500, le=2000),
    db: Session = Depends(get_db),
):
    """
    Database panel search, across ALL nodes at once. Three rules:
    1. tags + time range given      -> only those fields, within that window
    2. tags empty, time range given -> all fields, within that window
    3. time range empty, tags given -> those fields, but only for today (UTC)
    (Neither given at all also falls back to today, all fields.)
    """
    requested_tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    requested_tags = [t for t in requested_tags if t in VALID_TAGS]
    fields_to_return = requested_tags if requested_tags else sorted(VALID_TAGS)

    if start is None and end is None:
        now = datetime.now(timezone.utc)
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        end = now
    elif start is not None and end is None:
        end = datetime.now(timezone.utc)
    elif start is None and end is not None:
        start = end - timedelta(days=30)  # safety default if only an end bound was given

    q = (
        db.query(models.SensorReading)
        .filter(models.SensorReading.timestamp >= start, models.SensorReading.timestamp <= end)
        .order_by(models.SensorReading.timestamp.desc())
        .limit(limit)
    )
    readings = q.all()

    results = []
    for r in readings:
        row = {"node_id": r.node_id, "timestamp": r.timestamp.isoformat()}
        for field in fields_to_return:
            row[field] = getattr(r, field)
        results.append(row)

    return {
        "status": "success",
        "count": len(results),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "tags": fields_to_return,
        "results": results,
    }


@router.post("/ingest", response_model=APIResponse)
def manual_ingest(packet: TelemetryPacket, db: Session = Depends(get_db)):
    """
    Stands in for the MQTT path when no broker is running (e.g. this dev environment).
    Runs the exact same validation the real subscriber uses, then triggers the
    Decision Engine — mirroring what the live pipeline does end to end.
    """
    result = ingest_packet(db, packet.model_dump(mode="json"))
    if result is None:
        raise HTTPException(status_code=422, detail="Packet failed validation or integrity check")

    node, reading = result
    evaluate_reading(db, node, reading)
    evaluate_battery(db, node)
    db.commit()

    return APIResponse(status="success", message="Telemetry ingested", timestamp=datetime.now(timezone.utc))
