import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertStatus(str, enum.Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class User(Base):
    """Dashboard operators. Passwords are always stored hashed, never plaintext."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utcnow)


class Node(Base):
    """Node metadata — owned by the Database & MQTT module, read by the Backend."""
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String(64), unique=True, index=True, nullable=False)
    location = Column(String(128), nullable=True)
    last_seen = Column(DateTime, nullable=True)
    last_battery = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    readings = relationship("SensorReading", back_populates="node")
    alerts = relationship("Alert", back_populates="node")


class SensorReading(Base):
    """Raw validated telemetry, stored exactly as received — no modification, per spec."""
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    node_db_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
    node_id = Column(String(64), index=True, nullable=False)  # denormalized for fast queries
    motion = Column(Boolean, default=False)
    vibration = Column(Boolean, default=False)
    temperature = Column(Float, nullable=True)
    sound_level = Column(Float, nullable=True)
    battery = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False)  # from the packet itself
    received_at = Column(DateTime, default=utcnow)  # when the module ingested it

    node = relationship("Node", back_populates="readings")


class Alert(Base):
    """Produced only by the Backend Decision Engine — never by the DB & MQTT module."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    node_db_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
    node_id = Column(String(64), index=True, nullable=False)
    event_type = Column(String(64), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.ACTIVE)
    detected_at = Column(DateTime, default=utcnow)
    resolved_at = Column(DateTime, nullable=True)

    node = relationship("Node", back_populates="alerts")


class SystemLog(Base):
    """Operational log: logins, ingestion failures, alert generation, server errors."""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    event = Column(String(64), nullable=False)
    detail = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)
