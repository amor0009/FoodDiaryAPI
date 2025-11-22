from dataclasses import dataclass
from uuid import UUID
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models.product import Product
from api.src.repositories.product.base import BaseProductRepository
from api.src.repositories.crud import CrudOperations


@dataclass(slots=True)
class SqlAlchemyProductRepository(BaseProductRepository):
    def __init__(self) -> None:
        self._crud = CrudOperations(Product)

    async def get_user_products(self, session: AsyncSession, user_id: UUID, limit: int | None, offset: int | None) -> list[Product]:
        query = select(Product).where(
            or_(Product.is_public, Product.user_id == user_id)
        ).limit(limit).offset(offset)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_personal_products(self, session: AsyncSession, user_id: UUID, limit: int | None, offset: int | None) -> list[Product]:
        query = select(Product).where(Product.user_id == user_id).limit(limit).offset(offset)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def search_products(self, session: AsyncSession, user_id: UUID, query: str, limit: int | None, offset: int | None) -> list[Product]:
        if not query:
            return await self.get_user_products(session, user_id)

        formatted_query = query.capitalize()
        query = select(Product).where(
            or_(Product.is_public, (Product.user_id == user_id)),
            Product.name.ilike(f"{formatted_query}%")
        ).limit(limit).offset(offset)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_by_name(self, session: AsyncSession, product_name: str, user_id: UUID) -> Product | None:
        query = select(Product).where(
            and_(
                or_(Product.is_public, (Product.user_id == user_id)),
                (Product.name == product_name)
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id(self, session: AsyncSession, product_id: int, user_id: UUID) -> Product | None:
        query = select(Product).where(
            and_(
                (Product.id == product_id),
                or_(Product.is_public, (Product.user_id == user_id))
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_editable_by_id(self, session: AsyncSession, product_id: int, user_id: UUID) -> Product | None:
        query = select(Product).where(
            and_(
                Product.id == product_id,
                or_(
                    Product.is_public.is_(False),
                    Product.user_id == user_id
                )
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_editable_by_name(self, session: AsyncSession, product_name: str, user_id: UUID) -> Product | None:
        query = select(Product).where(
            and_(
                (Product.name == product_name),
                and_(
                    Product.is_public.is_(False),
                    (Product.user_id == user_id)
                )
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create_product(self, session: AsyncSession, product_data: dict) -> Product:
        product = Product(**product_data)
        return await self._crud.insert(session, product)

    async def update_product(self, session: AsyncSession, product: Product, update_data: dict) -> Product:
        for key, value in update_data.items():
            setattr(product, key, value)
        await session.commit()
        await session.refresh(product)
        return product

    async def delete_product(self, session: AsyncSession, product: Product) -> Product:
        await self._crud.delete(session, product.id)
        await session.commit()
        return product
