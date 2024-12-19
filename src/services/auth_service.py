from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import verify_password, get_password_hash
from src.models.user import User
from src.schemas.user import UserCreate
from src.services.user_service import find_user_by_login_and_email


async def authenticate_user(db: AsyncSession, email_login: str, password: str):
    user = await find_user_by_login_and_email(db, email_login)
    if user and verify_password(password, user.hashed_password):
        return user
    return None


async def create_user(db: AsyncSession, user: UserCreate):
    existing_login_user = await find_user_by_login_and_email(db, user.login)

    if existing_login_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with login '{user.login}' already exists."
        )

    existing_email_user = await find_user_by_login_and_email(db, user.email)

    if existing_email_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{user.email}' already exists."
        )

    hashed_password = get_password_hash(user.password)
    new_user = User(
        login=user.login,
        email=user.email,
        hashed_password=hashed_password,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
