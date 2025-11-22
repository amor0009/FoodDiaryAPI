from dataclasses import dataclass
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models.meal_products import MealProducts
from api.src.repositories.meal_products.base import BaseMealProductsRepository
from api.src.repositories.crud import CrudOperations


@dataclass(slots=True)
class SqlAlchemyMealProductsRepository(BaseMealProductsRepository):
    def __init__(self) -> None:
        self._crud = CrudOperations(MealProducts)

    async def get_meal_products(self, session: AsyncSession, meal_id: UUID) -> list[MealProducts]:
        query = select(MealProducts).where(MealProducts.meal_id == meal_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_meal_product(
        self,
        session: AsyncSession,
        meal_id: UUID,
        product_id: UUID
    ) -> MealProducts | None:
        query = select(MealProducts).where(
            and_(
                MealProducts.meal_id == meal_id,
                MealProducts.product_id == product_id
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create_meal_product(
        self,
        session: AsyncSession,
        meal_id: UUID,
        product_id: UUID,
        product_weight: float
    ) -> MealProducts:
        meal_product = MealProducts(
            meal_id=meal_id,
            product_id=product_id,
            product_weight=product_weight
        )
        return await self._crud.insert(session, meal_product)

    async def update_meal_product(
        self,
        session: AsyncSession,
        meal_product: MealProducts,
        new_weight: float
    ) -> MealProducts:
        meal_product.product_weight = new_weight
        await session.commit()
        await session.refresh(meal_product)
        return meal_product

    async def delete_meal_product(
        self,
        session: AsyncSession,
        meal_product: MealProducts
    ) -> None:
        await self._crud.delete(session, meal_product.id)
