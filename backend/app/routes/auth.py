"""
Auth routes — signup and login with bcrypt password hashing and JWT tokens.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.database.models import User
from app.services.security_service import SecurityService
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Authentication"])


# --- Schemas ---

class SignUpRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    gemini_key: str | None = None
    mapillary_token: str | None = None
    openweather_key: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


class ErrorResponse(BaseModel):
    detail: str


# --- Passlib context (lazy import so bcrypt isn't required at module load) ---

def _get_pwd_context():
    from passlib.context import CryptContext
    return CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Routes ---

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignUpRequest, db: AsyncSession = Depends(get_db)):
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not any(c.isupper() for c in body.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not any(c.islower() for c in body.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in body.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one digit")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    pwd_ctx = _get_pwd_context()
    hashed = pwd_ctx.hash(body.password)

    user = User(
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        password_hash=hashed,
        gemini_key=body.gemini_key,
        mapillary_token=body.mapillary_token,
        openweather_key=body.openweather_key,
    )
    db.add(user)
    # Commit happens in get_db dependency

    security = SecurityService()
    token = security.create_demo_token(
        subject=user.id,
        role="technician",
        expires_minutes=60 * 24,
    )

    return AuthResponse(
        token=token,
        user={
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        },
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    pwd_ctx = _get_pwd_context()
    if not pwd_ctx.verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    security = SecurityService()
    token = security.create_demo_token(
        subject=user.id,
        role="technician",
        expires_minutes=60 * 24,
    )

    return AuthResponse(
        token=token,
        user={
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        },
    )


@router.get("/me")
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    security = SecurityService()
    verification = security.verify_authorization_header(
        request.headers.get("authorization")
    )
    if not verification.get("valid"):
        raise HTTPException(status_code=401, detail=verification.get("reason"))
    user_id = verification["claims"].get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
    }
