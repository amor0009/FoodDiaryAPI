from dataclasses import dataclass
from datetime import date, timedelta, datetime, time
from uuid import UUID
from sqlalchemy import select, and_, delete, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from api.src.models.meal import Meal
from api.src.repositories.meal.base import BaseMealRepository
from api.src.repositories.crud import CrudOperations

from api.src.models.meal_products import MealProducts


@dataclass(slots=True)
class SqlAlchemyMealRepository(BaseMealRepository):
    def __init__(self) -> None:
        self._crud = CrudOperations(Meal)

    async def get_user_meals(self, session: AsyncSession, user_id: UUID) -> list[Meal]:
        query = (
            select(Meal)
            .options(
                joinedload(Meal.meal_products)
                .joinedload(MealProducts.product)
            )
            .where(Meal.user_id == user_id)
        )
        result = await session.execute(query)
        return list(result.unique().scalars().all())

    async def get_meals_with_products_by_date(
        self,
        session: AsyncSession,
        user_id: UUID,
        target_date: date
    ) -> list[Meal]:
        query = (
            select(Meal)
            .options(
                joinedload(Meal.meal_products)
                .joinedload(MealProducts.product)
            )
            .where(and_(
                Meal.user_id == user_id,
                Meal.created_at == target_date
            ))
        )
        result = await session.execute(query)
        return list(result.unique().scalars().all())

    async def get_meal_by_id_with_products(
        self,
        session: AsyncSession,
        meal_id: UUID,
        user_id: UUID
    ) -> Meal | None:
        query = (
            select(Meal)
            .options(
                joinedload(Meal.meal_products)
                .joinedload(MealProducts.product)
            )
            .where(and_(
                Meal.id == meal_id,
                Meal.user_id == user_id
            ))
        )
        result = await session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_meals_by_date(
        self,
        session: AsyncSession,
        user_id: UUID,
        target_date: date
    ) -> list[Meal]:
        start_datetime = datetime.combine(target_date, time.min)
        end_datetime = datetime.combine(target_date, time.max)

        query = (
            select(Meal)
            .where(
                and_(
                    Meal.user_id == user_id,
                    Meal.created_at >= start_datetime,
                    Meal.created_at <= end_datetime
                )
            )
            .options(
                joinedload(Meal.meal_products)
                .joinedload(MealProducts.product)
            )
        )
        result = await session.execute(query)
        return list(result.unique().scalars().all())

    async def get_meals_last_days(
        self,
        session: AsyncSession,
        user_id: UUID,
        days: int = 7
    ) -> list[Meal]:
        query = (
            select(Meal)
            .where(
                and_(
                    Meal.user_id == user_id,
                    Meal.created_at >= date.today() - timedelta(days=days)
                )
            )
            .options(
                joinedload(Meal.meal_products)
                .joinedload(MealProducts.product)
            )
            .order_by(Meal.created_at.desc())
        )
        result = await session.execute(query)
        return list(result.unique().scalars().all())

    async def create_meal(
        self,
        session: AsyncSession,
        meal_data: dict
    ) -> Meal:
        meal = Meal(**meal_data)
        return await self._crud.insert(session, meal)

    async def delete_meal_products(
        self,
        session: AsyncSession,
        meal_id: UUID
    ) -> None:
        await session.execute(
            delete(MealProducts)
            .where(MealProducts.meal_id == meal_id)
        )

    async def get_by_id(self, session: AsyncSession, meal_id: UUID) -> Meal | None:
        return await self._crud.get_by_id(session, meal_id)

    async def delete(self, session: AsyncSession, meal_id: UUID) -> None:
        await self._crud.delete(session, meal_id)
