from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..schemas import UserCreate, LoginRequest, TokenResponse, APIResponse
from ..security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    user = models.User(username=payload.username, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    return APIResponse(status="success", message="User registered", timestamp=datetime.now(timezone.utc))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        db.add(models.SystemLog(event="failed_login", detail=f"username={payload.username}"))
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    db.add(models.SystemLog(event="login", detail=f"username={payload.username}"))
    db.commit()
    token = create_access_token(subject=user.username)
    return TokenResponse(access_token=token)
