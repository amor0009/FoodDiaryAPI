from datetime import date, timedelta
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from src.daos.base_dao import BaseDAO
from src.models.meal import Meal
from src.models.meal_products import MealProducts


class MealDAO(BaseDAO):
    model = Meal

    @classmethod
    async def get_user_meals(cls, session: AsyncSession, user_id: int):
        query = select(cls.model).where(cls.model.user_id == user_id)
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_meals_with_products_by_date(
            cls,
            session: AsyncSession,
            user_id: int,
            target_date: date
    ):
        query = (
            select(cls.model)
            .options(
                joinedload(Meal.meal_products)
                .joinedload(MealProducts.product)
            )
            .where(and_(
                cls.model.user_id == user_id,
                cls.model.recorded_at == target_date
            ))
        )
        result = await session.execute(query)
        return result.unique().scalars().all()

    @classmethod
    async def get_meal_by_id_with_products(
            cls,
            session: AsyncSession,
            meal_id: int,
            user_id: int
    ):
        query = (
            select(cls.model)
            .options(
                joinedload(Meal.meal_products)
                .joinedload(MealProducts.product)
            )
            .where(and_(
                cls.model.id == meal_id,
                cls.model.user_id == user_id
            ))
        )
        result = await session.execute(query)
        return result.unique().scalar_one_or_none()

    @classmethod
    async def get_meals_by_date(
            cls,
            session: AsyncSession,
            user_id: int,
            target_date: date
    ):
        query = select(cls.model).where(and_(
            cls.model.user_id == user_id,
            cls.model.recorded_at == target_date
        ))
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_meals_last_days(
            cls,
            session: AsyncSession,
            user_id: int,
            days: int = 7
    ):
        query = select(cls.model).where(and_(
            cls.model.user_id == user_id,
            cls.model.recorded_at >= date.today() - timedelta(days=days)
        ).order_by(cls.model.recorded_at.desc()))
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def create_with_products(
            cls,
            session: AsyncSession,
            meal_data: dict,
            products_data: list[dict]
    ) -> Meal:
        meal = cls.model(**meal_data)
        session.add(meal)

        for product in products_data:
            meal_product = MealProducts(
                meal_id=meal.id,
                product_id=product["product_id"],
                product_weight=product["product_weight"]
            )
            session.add(meal_product)

        await session.commit()
        await session.refresh(meal)
        return meal

    @classmethod
    async def delete_meal_products(
            cls,
            session: AsyncSession,
            meal_id: int
    ):
        await session.execute(
            delete(MealProducts)
            .where(MealProducts.meal_id == meal_id)
        )
