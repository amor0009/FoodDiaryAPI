from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import get_current_user
from src.database.database import get_async_session
from src.models.user import User
from src.schemas.user import UserUpdate
from src.services.user_service import delete_user
from src.services.user_service import update_user, find_user_by_login_and_email


user_router = APIRouter()


@user_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(current_user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_async_session)):
    deleted_user = await delete_user(db, current_user)
    return {"status": status.HTTP_200_OK, "user": deleted_user}


@user_router.get("/me")
async def get_current_user_data(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"status": status.HTTP_200_OK, "user": current_user}


@user_router.get("/{login_email}")
async def find_user(login_email: str, db: AsyncSession = Depends(get_async_session)):
    user = await find_user_by_login_and_email(db, login_email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"status": status.HTTP_200_OK, "user": user}


@user_router.put("/me")
async def update_current_user(user: UserUpdate, db: AsyncSession = Depends(get_async_session),
                              current_user: User = Depends(get_current_user)):
    updated_user = await update_user(user, db, current_user)
    return {"status": status.HTTP_200_OK, "user": updated_user}
