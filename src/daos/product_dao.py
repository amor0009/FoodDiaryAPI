from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.daos.base_dao import BaseDAO
from src.models.product import Product


class ProductDAO(BaseDAO):
    model = Product

    @classmethod
    async def get_user_products(cls, session: AsyncSession, user_id: int):
        query = select(cls.model).where(
            or_(cls.model.is_public, (cls.model.user_id == user_id))
        )
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_personal_products(cls, session: AsyncSession, user_id: int):
        query = select(cls.model).where(cls.model.user_id == user_id)
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def search_products(cls, session: AsyncSession, user_id: int, query: str):
        if not query:
            return await cls.get_user_products(session, user_id)

        formatted_query = query.capitalize()
        query = select(cls.model).where(
            or_((cls.model.is_public == True), (cls.model.user_id == user_id)),
            cls.model.name.ilike(f"{formatted_query}%")
        )
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_by_name(cls, session: AsyncSession, product_name: str, user_id: int):
        query = select(cls.model).where(
            and_(
                or_((cls.model.is_public == True), (cls.model.user_id == user_id)),
                (cls.model.name == product_name)
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_id(cls, session: AsyncSession, product_id: int, user_id: int):
        query = select(cls.model).where(
            and_(
                (cls.model.id == product_id),
                or_((cls.model.is_public == True), (cls.model.user_id == user_id))
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_editable_by_id(cls, session: AsyncSession, product_id: int, user_id: int):
        query = select(cls.model).where(
            and_(
                cls.model.id == product_id,
                or_(
                    cls.model.is_public == False,
                    cls.model.user_id == user_id
                )
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_editable_by_name(cls, session: AsyncSession, product_name: str, user_id: int):
        query = select(cls.model).where(
            and_(
                (cls.model.name == product_name),
                and_(
                    (cls.model.is_public == False),
                    (cls.model.user_id == user_id)
                )
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def create_product(cls, session: AsyncSession, product_data: dict):
        product = cls.model(**product_data)
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product

    @classmethod
    async def update_product(cls, session: AsyncSession, product: Product, update_data: dict):
        for key, value in update_data.items():
            setattr(product, key, value)
        await session.commit()
        await session.refresh(product)
        return product

    @classmethod
    async def delete_product(cls, session: AsyncSession, product: Product):
        await session.delete(product)
        await session.commit()
        return product

    @classmethod
    async def update_product_picture(cls, session: AsyncSession, product: Product, picture_data: bytes):
        product.picture = picture_data
        await session.commit()
        await session.refresh(product)
        return product
