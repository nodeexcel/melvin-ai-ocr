from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import authenticate_user, create_access_token, create_user
from app.config import settings
from app.database import get_db
from app.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if settings.register_secret and body.invite_code != settings.register_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid invite code")
    try:
        user = await create_user(db, body.username, body.password)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)
