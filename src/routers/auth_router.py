from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import create_access_token
from src.database.database import get_async_session
from src.schemas.user import UserCreate
from src.services.auth_service import create_user, authenticate_user


auth_router = APIRouter()


@auth_router.post("/registration")
async def registration(user: UserCreate, db: AsyncSession = Depends(get_async_session)):
    new_user = await create_user(db, user)
    access_token = create_access_token(data={"sub": new_user.login})
    await db.commit()
    await db.refresh(new_user)
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.post("/login")
async def login(email_login: str, password: str, db: AsyncSession = Depends(get_async_session)):
    user = await authenticate_user(db, email_login, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Неверный логин или пароль")

    access_token = create_access_token(data={"sub": email_login})
    return {"access_token": access_token, "token_type": "bearer"}
