from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.cache.cache import cache
from src.logging_config import logger
from src.schemas.meal_products import MealProductsCreate, MealProductsUpdate, MealProductsRead
from src.daos.meal_products_dao import MealProductsDAO


class MealProductsService:

    # Получение продуктов для блюда
    @classmethod
    async def get_meal_products(cls, db: AsyncSession, meal_id: int):
        cache_key = f"meal_products:{meal_id}"
        try:
            cached_meal_products = await cache.get(cache_key)
            if cached_meal_products:
                logger.info(f"Cache hit for meal_products: {meal_id}")
                return [MealProductsRead.model_validate(mp) for mp in cached_meal_products]

            logger.info(f"Cache miss for meal_products: {meal_id}. Fetching from database.")

            meal_products = await MealProductsDAO.get_meal_products(db, meal_id)

            if not meal_products:
                return []

            meal_products_list = [MealProductsRead.model_validate(mp) for mp in meal_products]
            await cache.set(cache_key, [mp.model_dump(mode="json") for mp in meal_products_list])
            logger.info(f"Meal products for meal {meal_id} cached.")

            return meal_products_list

        except Exception as e:
            logger.error(f"Error fetching meal products for meal {meal_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # Добавление продукта в блюдо
    @classmethod
    async def add_meal_product(
            cls,
            db: AsyncSession,
            meal_id: int,
            data: MealProductsCreate
    ) -> MealProductsRead:
        try:
            # Проверяем существование продукта в блюде
            existing_product = await MealProductsDAO.get_meal_product(
                db, meal_id, data.product_id
            )

            if existing_product:
                logger.warning(f"Product {data.product_id} already exists in meal {meal_id}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Product {data.product_id} is already in the meal {meal_id}"
                )

            # Создаем новую связь продукта с блюдом
            meal_product = await MealProductsDAO.create_meal_product(
                db,
                meal_id=meal_id,
                product_id=data.product_id,
                product_weight=data.product_weight
            )

            # Инвалидируем кеш
            cache_key = f"meal_products:{meal_id}"
            await cache.delete(cache_key)
            logger.info(f"Cache invalidated for meal_products: {meal_id}")

            return MealProductsRead.model_validate(meal_product)

        except Exception as e:
            logger.error(f"Error adding product to meal {meal_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # Обновление продукта в блюде
    @classmethod
    async def update_meal_product(
            cls,
            db: AsyncSession,
            meal_id: int,
            data: MealProductsUpdate
    ):
        try:
            # Получаем существующую связь продукта с блюдом
            meal_product = await MealProductsDAO.get_meal_product(
                db, meal_id, data.product_id
            )

            if not meal_product:
                logger.warning(f"Product {data.product_id} not found in meal {meal_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Product with ID {data.product_id} in meal {meal_id} not found"
                )

            # Обновляем вес продукта
            updated_meal_product = await MealProductsDAO.update_meal_product(
                db,
                meal_product=meal_product,
                new_weight=data.product_weight
            )

            # Инвалидируем кеш
            cache_key = f"meal_products:{meal_id}"
            await cache.delete(cache_key)
            logger.info(f"Meal product {data.product_id} updated in meal {meal_id}")

            return MealProductsRead.model_validate(updated_meal_product)

        except Exception as e:
            logger.error(f"Error updating meal product for meal_id {meal_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # Удаление продукта из блюда
    @classmethod
    async def delete_meal_product(
            cls,
            db: AsyncSession,
            meal_id: int,
            product_id: int
    ):
        try:
            # Получаем связь продукта с блюдом
            meal_product = await MealProductsDAO.get_meal_product(
                db, meal_id, product_id
            )

            if not meal_product:
                logger.warning(f"Product {product_id} not found in meal {meal_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Product with ID {product_id} in meal {meal_id} not found"
                )

            # Удаляем связь
            await MealProductsDAO.delete_meal_product(db, meal_product)

            # Инвалидируем кеш
            cache_key = f"meal_products:{meal_id}"
            await cache.delete(cache_key)
            logger.info(f"Product {product_id} removed from meal {meal_id}")

            return {"message": f"Product with ID {product_id} removed from meal {meal_id}"}

        except Exception as e:
            logger.error(f"Error deleting product {product_id} from meal {meal_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
