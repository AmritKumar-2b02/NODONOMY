from datetime import datetime, timezone
from sqlalchemy.orm import Session

from . import models
from .config import settings


def evaluate_reading(db: Session, node: models.Node, reading: models.SensorReading) -> models.Alert | None:
    """
    Correlates the sensors on a single reading against Nodonomy's Ch.5 scenarios.
    Returns a created Alert, or None if the reading is normal operation.
    Battery/offline checks are handled separately since they aren't per-reading events.
    """
    motion = reading.motion
    vibration = reading.vibration
    sound = reading.sound_level or 0.0
    high_sound = sound >= settings.HIGH_SOUND_THRESHOLD

    event_type = None
    severity = None

    if motion and vibration and high_sound:
        # Scenario 2 — Potential intrusion: all three independent sensors agree
        event_type = "potential_intrusion"
        severity = models.AlertSeverity.HIGH
    elif motion and not vibration and not high_sound:
        # Scenario 1 — Possible human movement, low confidence alone
        event_type = "motion_detected"
        severity = models.AlertSeverity.LOW
    elif vibration and not motion:
        # Scenario 3 — Equipment disturbance, not escalated
        event_type = "vibration_event"
        severity = models.AlertSeverity.LOW
    elif reading.temperature is not None and reading.temperature >= settings.HIGH_TEMP_THRESHOLD:
        event_type = "elevated_temperature"
        severity = models.AlertSeverity.MEDIUM

    if event_type is None:
        return None

    alert = models.Alert(
        node_db_id=node.id,
        node_id=node.node_id,
        event_type=event_type,
        severity=severity,
        status=models.AlertStatus.ACTIVE,
    )
    db.add(alert)
    return alert


def evaluate_battery(db: Session, node: models.Node) -> models.Alert | None:
    """Scenario 4 — Maintenance required: low battery, node still communicating."""
    if node.last_battery is not None and node.last_battery < settings.LOW_BATTERY_THRESHOLD:
        existing = (
            db.query(models.Alert)
            .filter(
                models.Alert.node_db_id == node.id,
                models.Alert.event_type == "low_battery",
                models.Alert.status == models.AlertStatus.ACTIVE,
            )
            .first()
        )
        if existing:
            return None  # don't spam duplicate maintenance alerts
        alert = models.Alert(
            node_db_id=node.id,
            node_id=node.node_id,
            event_type="low_battery",
            severity=models.AlertSeverity.MEDIUM,
            status=models.AlertStatus.ACTIVE,
        )
        db.add(alert)
        return alert
    return None


def compute_node_status(node: models.Node) -> str:
    """Scenario 5 — Node offline: no telemetry within the configured timeout."""
    if node.last_seen is None:
        return "offline"
    now = datetime.now(timezone.utc)
    last_seen = node.last_seen if node.last_seen.tzinfo else node.last_seen.replace(tzinfo=timezone.utc)
    elapsed = (now - last_seen).total_seconds()
    return "online" if elapsed <= settings.NODE_OFFLINE_TIMEOUT_SECONDS else "offline"
