from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.daos.base_dao import BaseDAO
from src.models.meal_products import MealProducts


class MealProductsDAO(BaseDAO):
    model = MealProducts

    @classmethod
    async def get_meal_products(cls, session: AsyncSession, meal_id: int):
        query = select(cls.model).where(cls.model.meal_id == meal_id)
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_meal_product(
        cls,
        session: AsyncSession,
        meal_id: int,
        product_id: int
    ):
        query = select(cls.model).where(
            and_(
                cls.model.meal_id == meal_id,
                cls.model.product_id == product_id
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def create_meal_product(
        cls,
        session: AsyncSession,
        meal_id: int,
        product_id: int,
        product_weight: float
    ):
        meal_product = cls.model(
            meal_id=meal_id,
            product_id=product_id,
            product_weight=product_weight
        )
        session.add(meal_product)
        await session.commit()
        await session.refresh(meal_product)
        return meal_product

    @classmethod
    async def update_meal_product(
        cls,
        session: AsyncSession,
        meal_product: MealProducts,
        new_weight: float
    ):
        meal_product.product_weight = new_weight
        await session.commit()
        await session.refresh(meal_product)
        return meal_product

    @classmethod
    async def delete_meal_product(
        cls,
        session: AsyncSession,
        meal_product: MealProducts
    ):
        await session.delete(meal_product)
        await session.commit()
