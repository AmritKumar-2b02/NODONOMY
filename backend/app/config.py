import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Database. Defaults to local Postgres; swap to sqlite:///./nodonomy.db for a zero-setup demo.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://nodonomy:nodonomy@localhost:5432/nodonomy"
    )

    # JWT auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-this-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

    # MQTT broker (used by the DB & MQTT ingestion module)
    MQTT_HOST: str = os.getenv("MQTT_HOST", "localhost")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", "1883"))
    MQTT_TOPIC_PREFIX: str = os.getenv("MQTT_TOPIC_PREFIX", "nodonomy")

    # Node offline threshold (seconds since last_seen before a node is Offline)
    NODE_OFFLINE_TIMEOUT_SECONDS: int = int(os.getenv("NODE_OFFLINE_TIMEOUT_SECONDS", "120"))

    # Alert thresholds
    LOW_BATTERY_THRESHOLD: int = int(os.getenv("LOW_BATTERY_THRESHOLD", "20"))
    
    HIGH_TEMP_THRESHOLD: float = float(os.getenv("HIGH_TEMP_THRESHOLD", "45.0"))


settings = Settings()
