from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


# ---------- Auth ----------

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Telemetry packet (what the DB & MQTT module validates) ----------

class TelemetryPacket(BaseModel):
    node_id: str = Field(min_length=1, max_length=64)
    motion: bool = False
    vibration: bool = False
    temperature: Optional[float] = None
    sound_level: Optional[float] = None
    battery: int = Field(ge=0, le=100)
    timestamp: datetime
    checksum: Optional[str] = None  # hex CRC/HMAC — verified against payload before storage

    @field_validator("temperature")
    @classmethod
    def sane_temperature(cls, v):
        if v is not None and not (-40.0 <= v <= 125.0):
            raise ValueError("temperature out of plausible sensor range")
        return v

    @field_validator("sound_level")
    @classmethod
    def sane_sound(cls, v):
        if v is not None and not (0.0 <= v <= 200.0):
            raise ValueError("sound_level out of plausible sensor range")
        return v


# ---------- API response shapes ----------

class NodeOut(BaseModel):
    node_id: str
    location: Optional[str]
    status: str  # "online" | "offline", computed by the Backend
    last_battery: Optional[int]
    last_seen: Optional[datetime]

    class Config:
        from_attributes = True


class TelemetryOut(BaseModel):
    node_id: str
    motion: bool
    vibration: bool
    temperature: Optional[float]
    sound_level: Optional[float]
    battery: Optional[int]
    timestamp: datetime

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: int
    node_id: str
    event_type: str
    severity: str
    status: str
    detected_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


class SystemStatusOut(BaseModel):
    total_nodes: int
    online_nodes: int
    offline_nodes: int
    active_alerts: int


class APIResponse(BaseModel):
    status: str  # "success" | "error"
    message: Optional[str] = None
    timestamp: datetime
    data: Optional[object] = None
