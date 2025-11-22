from abc import ABC, abstractmethod
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models.meal_products import MealProducts


class BaseMealProductsRepository(ABC):
    @abstractmethod
    async def get_meal_products(self, session: AsyncSession, meal_id: UUID) -> list[MealProducts]: ...

    @abstractmethod
    async def get_meal_product(
        self,
        session: AsyncSession,
        meal_id: UUID,
        product_id: UUID
    ) -> MealProducts | None: ...

    @abstractmethod
    async def create_meal_product(
        self,
        session: AsyncSession,
        meal_id: UUID,
        product_id: UUID,
        product_weight: float
    ) -> MealProducts: ...

    @abstractmethod
    async def update_meal_product(
        self,
        session: AsyncSession,
        meal_product: MealProducts,
        new_weight: float
    ) -> MealProducts: ...

    @abstractmethod
    async def delete_meal_product(
        self,
        session: AsyncSession,
        meal_product: MealProducts
    ) -> None: ...
