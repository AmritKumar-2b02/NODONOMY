"""
Database & MQTT module.

Scope (per spec): manage MQTT subscriptions, receive telemetry, validate packet
structure, persist it unmodified, and keep node metadata (last_seen, battery) current.
Explicitly NOT in scope here: alert generation, thresholds, auth, dashboard rendering.
Those live in decision_engine.py / routers, called separately by the Backend layer.
"""

import json
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import SessionLocal
from .schemas import TelemetryPacket
from .security import verify_packet_checksum

logger = logging.getLogger("nodonomy.ingest")


def ingest_packet(db: Session, raw: dict) -> tuple[models.Node, models.SensorReading] | None:
    """
    Validates a raw telemetry dict against the packet contract and, if valid,
    stores it and updates the node's last_seen/battery. Returns (node, reading)
    on success, None if the packet was rejected.
    """
    try:
        packet = TelemetryPacket(**raw)
    except ValidationError as e:
        logger.warning("Rejected malformed packet: %s", e)
        _log_event(db, "packet_rejected", str(e)[:250])
        return None

    if packet.checksum and not verify_packet_checksum(
        packet.node_id, packet.timestamp.isoformat(), packet.battery, packet.checksum
    ):
        logger.warning("Rejected packet with bad checksum from node %s", packet.node_id)
        _log_event(db, "checksum_failed", f"node_id={packet.node_id}")
        return None

    node = db.query(models.Node).filter(models.Node.node_id == packet.node_id).first()
    if node is None:
        node = models.Node(node_id=packet.node_id)
        db.add(node)
        db.flush()  # assign node.id before use below

    node.last_seen = packet.timestamp if packet.timestamp.tzinfo else packet.timestamp.replace(tzinfo=timezone.utc)
    node.last_battery = packet.battery

    reading = models.SensorReading(
        node_db_id=node.id,
        node_id=packet.node_id,
        motion=packet.motion,
        vibration=packet.vibration,
        temperature=packet.temperature,
        sound_level=packet.sound_level,
        battery=packet.battery,
        timestamp=packet.timestamp,
    )
    db.add(reading)
    db.commit()
    db.refresh(node)
    db.refresh(reading)
    return node, reading


def _log_event(db: Session, event: str, detail: str = ""):
    db.add(models.SystemLog(event=event, detail=detail))
    db.commit()


# ---------- Live MQTT subscriber (run as a standalone process against a real broker) ----------

def _on_connect(client, userdata, flags, rc, properties=None):
    topic = f"{settings.MQTT_TOPIC_PREFIX}/nodes/+/data"
    client.subscribe(topic)
    logger.info("Connected to MQTT broker, subscribed to %s", topic)


def _on_message(client, userdata, msg):
    db = SessionLocal()
    try:
        raw = json.loads(msg.payload.decode())
        result = ingest_packet(db, raw)
        if result:
            logger.info("Stored telemetry for node %s", result[0].node_id)
    except json.JSONDecodeError:
        logger.warning("Dropped non-JSON MQTT payload on topic %s", msg.topic)
    finally:
        db.close()


def run_subscriber():
    """Blocking loop — run with: python -m app.mqtt_ingest"""
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect(settings.MQTT_HOST, settings.MQTT_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_subscriber()
