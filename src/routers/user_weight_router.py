from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import Security
from src.database.database import get_async_session
from src.models.user import User
from src.schemas.user_weight import UserWeightUpdate
from src.services.user_weight_service import UserWeightService


user_weight_router = APIRouter(tags=["User_Weight"])


# Эндпоинт для обновления веса текущего пользователя
@user_weight_router.put("/me")
async def update_user_weight(
        user_weight: UserWeightUpdate,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(Security.get_required_user),
):
    return await UserWeightService.save_or_update_weight(user_weight, db, current_user.id)


# Эндпоинт для получения веса пользователя на определенную дату
@user_weight_router.get("/me/{current_date}")
async def get_user_weight(
        current_date: str,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(Security.get_required_user)
):
    return await UserWeightService.get_current_weight(current_date, db, current_user.id)


# Эндпоинт для получения истории веса пользователя
@user_weight_router.get("/history/me")
async def get_user_weight_history(
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(Security.get_required_user)
):
    return await UserWeightService.get_weights(db, current_user.id)
