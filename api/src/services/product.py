from dataclasses import dataclass
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.cache.cache import cache
from api.logging_config import logger
from api.src.schemas.base import Pagination
from api.src.schemas.product import ProductRead, ProductCreate, ProductUpdate, ProductAdd
from api.src.repositories.product.base import BaseProductRepository
from api.src.services.converters.product import convert_product_model_to_schema


@dataclass(slots=True)
class ProductService:
    _product_repository: BaseProductRepository

    async def get_user_products(
        self,
        session: AsyncSession,
        user_id: UUID,
        pagination: Pagination
    ) -> list[ProductRead]:
        cache_key = f"user_products:{user_id}"
        logger.info(f"Checking cache for user {user_id}'s products.")

        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for user {user_id}'s products.")
            return [ProductRead.model_validate(product) for product in cached_data]

        logger.info(f"Cache miss for user {user_id}'s products. Fetching from database.")
        products = await self._product_repository.get_user_products(session, user_id=user_id, limit=pagination.limit, offset=pagination.offset)
        product_list = [convert_product_model_to_schema(product) for product in products]

        await cache.set(cache_key, [product.model_dump(mode="json") for product in product_list], expire=3600)
        logger.info(f"Products for user {user_id} cached successfully.")
        return product_list

    async def get_personal_products(self, session: AsyncSession, user_id: UUID, pagination: Pagination) -> list[ProductRead]:
        cache_key = f"personal_products:{user_id}"
        logger.info(f"Checking cache for personal products of user {user_id}.")

        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for personal products of user {user_id}.")
            return [ProductRead.model_validate(product) for product in cached_data]

        logger.info(f"Cache miss for personal products of user {user_id}. Fetching from database.")
        products = await self._product_repository.get_personal_products(session, user_id, limit=pagination.limit, offset=pagination.offset)
        product_list = [convert_product_model_to_schema(product) for product in products]

        await cache.set(cache_key, [product.model_dump(mode="json") for product in product_list], expire=3600)
        logger.info(f"Personal products for user {user_id} cached successfully.")
        return product_list

    async def search_products(self, session: AsyncSession, user_id: UUID, query: str, pagination: Pagination) -> list[ProductRead]:
        cache_key = f"product_search:{user_id}:{query.lower()}"
        logger.info(f"Searching products for user {user_id} with query: {query}")

        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for product search: {query}")
            return [ProductRead.model_validate(product) for product in cached_data]

        products = await self._product_repository.search_products(session, user_id, query, limit=pagination.limit, offset=pagination.offset)
        product_list = [convert_product_model_to_schema(product) for product in products]

        await cache.set(cache_key, [product.model_dump(mode="json") for product in product_list], expire=1800)
        logger.info(f"Search results for '{query}' cached successfully.")
        return product_list

    async def get_product_by_id(self, session: AsyncSession, product_id: UUID, user_id: UUID) -> ProductRead | None:
        cache_key = f"product:{user_id}:{product_id}"
        logger.info(f"Checking cache for product {product_id} of user {user_id}.")

        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for product {product_id} of user {user_id}.")
            return ProductRead.model_validate(cached_data)

        logger.info(f"Cache miss for product {product_id} of user {user_id}. Fetching from database.")
        product = await self._product_repository.get_by_id(session, product_id, user_id)
        if not product:
            logger.warning(f"Product with id {product_id} not found for user {user_id}.")
            return None

        product_schema = convert_product_model_to_schema(product)
        await cache.set(cache_key, product_schema.model_dump(mode="json"), expire=3600)
        logger.info(f"Product {product_id} of user {user_id} cached successfully.")
        return product_schema

    async def get_product_by_name(self, session: AsyncSession, product_name: str, user_id: UUID) -> ProductRead | None:
        product = await self._product_repository.get_by_name(session, product_name, user_id)
        if not product:
            logger.warning(f"Product with name {product_name} not found for user {user_id}.")
            return None

        return convert_product_model_to_schema(product)

    async def create_product(self, session: AsyncSession, product_data: ProductCreate, user_id: UUID) -> ProductRead:
        logger.info(f"Creating new product for user {user_id}: {product_data.name}")

        existing_product = await self._product_repository.get_editable_by_name(session, product_data.name, user_id)
        if existing_product:
            logger.warning(f"Product with name {product_data.name} already exists for user {user_id}.")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product with this name already exists"
            )

        try:
            slug = product_data.name.lower().replace(' ', '-')

            product_dict = product_data.model_dump()
            product_dict.update({
                "slug": slug,
                "user_id": user_id,
                "is_public": False
            })

            product = await self._product_repository.create_product(session, product_dict)
            await session.commit()
            await session.refresh(product)

            await self._clear_product_cache(user_id, product.id)
            logger.info(f"Product {product_data.name} created successfully for user {user_id}.")

            return convert_product_model_to_schema(product)

        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating product {product_data.name}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create product"
            )

    async def update_product(self, session: AsyncSession, product_id: UUID, product_update: ProductUpdate,
                             user_id: UUID) -> ProductRead:
        logger.info(f"Updating product {product_id} for user {user_id}")

        product = await self._product_repository.get_editable_by_id(session, product_id, user_id)
        if not product:
            logger.warning(f"Product {product_id} not found or not editable for user {user_id}.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found or not editable"
            )

        try:
            update_data = product_update.model_dump(exclude_unset=True)

            if "name" in update_data:
                update_data["slug"] = update_data["name"].lower().replace(' ', '-')

            updated_product = await self._product_repository.update_product(session, product, update_data)

            await self._clear_product_cache(user_id, product_id)
            logger.info(f"Product {product_id} updated successfully for user {user_id}.")

            return convert_product_model_to_schema(updated_product)

        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating product {product_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update product"
            )

    async def delete_product(self, session: AsyncSession, product_id: UUID, user_id: UUID) -> dict:
        logger.info(f"Deleting product {product_id} for user {user_id}")

        product = await self._product_repository.get_editable_by_id(session, product_id, user_id)
        if not product:
            logger.warning(f"Product {product_id} not found or not editable for user {user_id}.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found or not editable"
            )

        try:
            await self._product_repository.delete_product(session, product)

            await self._clear_product_cache(user_id, product_id)
            logger.info(f"Product {product_id} deleted successfully for user {user_id}.")

            return {"message": "Product deleted successfully"}

        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting product {product_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete product"
            )

    async def add_quick_product(self, session: AsyncSession, product_data: ProductAdd, user_id: UUID) -> ProductRead:
        logger.info(f"Quick adding product for user {user_id}: {product_data.name}")

        product_create = ProductCreate(
            name=product_data.name,
            weight=product_data.weight,
            calories=0.0,
            proteins=0.0,
            fats=0.0,
            carbohydrates=0.0,
            description=f"Быстро добавленный продукт: {product_data.name}"
        )

        return await self.create_product(session, product_create, user_id)

    async def _clear_product_cache(self, user_id: UUID, product_id: UUID | None = None):
        keys = [
            f"user_products:{user_id}",
            f"personal_products:{user_id}",
        ]

        if product_id:
            keys.append(f"product:{user_id}:{product_id}")
            keys.append(f"product_search:{user_id}:*")

        for key in keys:
            await cache.delete(key)
        logger.info(f"Cleared product cache for user {user_id}")
