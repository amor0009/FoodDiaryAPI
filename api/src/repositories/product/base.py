from abc import ABC, abstractmethod
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models.product import Product


class BaseProductRepository(ABC):
    @abstractmethod
    async def get_user_products(self, session: AsyncSession, user_id: UUID, limit: int | None, offset: int | None) -> list[Product]: ...

    @abstractmethod
    async def get_personal_products(self, session: AsyncSession, user_id: UUID, limit: int | None, offset: int | None) -> list[Product]: ...

    @abstractmethod
    async def search_products(self, session: AsyncSession, user_id: UUID, query: str, limit: int | None, offset: int | None) -> list[Product]: ...

    @abstractmethod
    async def get_by_name(self, session: AsyncSession, product_name: str, user_id: UUID) -> Product | None: ...

    @abstractmethod
    async def get_by_id(self, session: AsyncSession, product_id: UUID, user_id: UUID) -> Product | None: ...

    @abstractmethod
    async def get_editable_by_id(self, session: AsyncSession, product_id: UUID, user_id: UUID) -> Product | None: ...

    @abstractmethod
    async def get_editable_by_name(self, session: AsyncSession, product_name: str, user_id: UUID) -> Product | None: ...

    @abstractmethod
    async def create_product(self, session: AsyncSession, product_data: dict) -> Product: ...

    @abstractmethod
    async def update_product(self, session: AsyncSession, product: Product, update_data: dict) -> Product: ...

    @abstractmethod
    async def delete_product(self, session: AsyncSession, product: Product) -> Product: ...
