from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from api.src.core.security import Security
from api.src.database.database import get_async_session
from api.src.models.user import User
from api.src.schemas.user_weight import UserWeightRead, UserWeightCreate
from api.src.services.user_weight import UserWeightService
from api.src.dependencies.services import get_user_weight_service


user_weight_router = APIRouter(prefix="/api/user-weight", tags=["user-weight"])


@user_weight_router.get("/")
async def get_weight_history(
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    user_weight_service: UserWeightService = Depends(get_user_weight_service),
) -> list[UserWeightRead] | None:
    return await user_weight_service.get_last_30_days(session, current_user.id)


@user_weight_router.get("/current")
async def get_current_weight(
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    user_weight_service: UserWeightService = Depends(get_user_weight_service),
) -> UserWeightRead | None:
    return await user_weight_service.get_current_weight(session, current_user.id)


@user_weight_router.get("/date/{target_date}")
async def get_weight_by_date(
    target_date: date,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    user_weight_service: UserWeightService = Depends(get_user_weight_service),
) -> UserWeightRead | None:
    return await user_weight_service.get_by_date(session, current_user.id, target_date)


@user_weight_router.get("/trend")
async def get_weight_trend(
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    user_weight_service: UserWeightService = Depends(get_user_weight_service),
) -> dict:
    return await user_weight_service.get_weight_trend(session, current_user.id)


@user_weight_router.post("/")
async def create_or_update_weight(
    weight_data: UserWeightCreate,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    user_weight_service: UserWeightService = Depends(get_user_weight_service),
) -> UserWeightRead:
    return await user_weight_service.create_or_update(session, current_user.id, weight_data)


@user_weight_router.delete("/date/{target_date}")
async def delete_weight_record(
    target_date: date,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    user_weight_service: UserWeightService = Depends(get_user_weight_service),
) -> dict:
    success = await user_weight_service.delete_weight_record(session, current_user.id, target_date)
    if not success:
        raise HTTPException(status_code=404, detail="Weight record not found")
    return {"message": "Weight record deleted successfully"}
