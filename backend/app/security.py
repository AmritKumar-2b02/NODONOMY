import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------- Passwords ----------

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------- JWT ----------

def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise JWTError("missing subject")
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_username(token: str = Depends(oauth2_scheme)) -> str:
    """Dependency: protects every route it's attached to. Auth failures never reach business logic."""
    return decode_access_token(token)


# ---------- Packet integrity (DB & MQTT module) ----------

def compute_packet_checksum(node_id: str, timestamp: str, battery: int, secret: str = settings.JWT_SECRET) -> str:
    """
    HMAC-SHA256 over the packet's core fields. Real sensor nodes would compute this
    with a lightweight CRC or a shared-secret HMAC before transmitting over LoRa;
    the ingestion module recomputes it and rejects packets that don't match.
    """
    payload = f"{node_id}:{timestamp}:{battery}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()[:16]


def verify_packet_checksum(node_id: str, timestamp: str, battery: int, checksum: str) -> bool:
    if not checksum:
        return False
    expected = compute_packet_checksum(node_id, timestamp, battery)
    return hmac.compare_digest(expected, checksum)
