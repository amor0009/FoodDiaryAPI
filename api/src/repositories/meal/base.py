from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models.meal import Meal


class BaseMealRepository(ABC):
    @abstractmethod
    async def get_user_meals(self, session: AsyncSession, user_id: UUID) -> list[Meal]: ...

    @abstractmethod
    async def get_meals_with_products_by_date(
        self,
        session: AsyncSession,
        user_id: UUID,
        target_date: date
    ) -> list[Meal]: ...

    @abstractmethod
    async def get_meal_by_id_with_products(
        self,
        session: AsyncSession,
        meal_id: UUID,
        user_id: UUID
    ) -> Meal | None: ...

    @abstractmethod
    async def get_meals_by_date(
        self,
        session: AsyncSession,
        user_id: UUID,
        target_date: date
    ) -> list[Meal]: ...

    @abstractmethod
    async def get_meals_last_days(
        self,
        session: AsyncSession,
        user_id: UUID,
        days: int = 7
    ) -> list[Meal]: ...

    @abstractmethod
    async def create_meal(
        self,
        session: AsyncSession,
        meal_data: dict
    ) -> Meal: ...

    @abstractmethod
    async def delete_meal_products(
        self,
        session: AsyncSession,
        meal_id: UUID
    ) -> None: ...

    @abstractmethod
    async def get_by_id(self, session: AsyncSession, meal_id: UUID) -> Meal | None: ...

    @abstractmethod
    async def delete(self, session: AsyncSession, meal_id: UUID) -> None: ...
