from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import date
from api.src.core.security import Security
from api.src.database.database import get_async_session
from api.src.models.user import User
from api.src.schemas.meal import MealRead, MealCreate, MealUpdate
from api.src.services.meal import MealService
from api.src.dependencies.services import get_meal_service


meal_router = APIRouter(prefix="/api/meals", tags=["meals"])


@meal_router.get("/")
async def get_user_meals(
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    meal_service: MealService = Depends(get_meal_service),
) -> list[MealRead]:
    return await meal_service.get_user_meals(session, current_user.id)


@meal_router.get("/date/{target_date}")
async def get_meals_by_date(
    target_date: date,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    meal_service: MealService = Depends(get_meal_service),
) -> list[MealRead]:
    return await meal_service.get_meals_by_date(session, current_user.id, target_date.isoformat())


@meal_router.get("/recent")
async def get_recent_meals(
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    meal_service: MealService = Depends(get_meal_service),
) -> list[MealRead]:
    return await meal_service.get_meals_last_7_days(session, current_user.id)


@meal_router.get("/{meal_id}")
async def get_meal(
    meal_id: UUID,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    meal_service: MealService = Depends(get_meal_service),
) -> MealRead:
    meal = await meal_service.get_meal_by_id(session, meal_id, current_user.id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    return meal


@meal_router.post("/")
async def create_meal(
    meal_data: MealCreate,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    meal_service: MealService = Depends(get_meal_service),
) -> MealRead:
    return await meal_service.add_meal(session, meal_data, current_user.id)


@meal_router.put("/{meal_id}")
async def update_meal(
    meal_id: UUID,
    meal_update: MealUpdate,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    meal_service: MealService = Depends(get_meal_service),
) -> MealRead:
    return await meal_service.update_meal(session, meal_update, meal_id, current_user.id)


@meal_router.delete("/{meal_id}")
async def delete_meal(
    meal_id: UUID,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    meal_service: MealService = Depends(get_meal_service),
) -> dict:
    return await meal_service.delete_meal(session, meal_id, current_user.id)
