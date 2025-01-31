from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound
from src.cache.cache import cache
from src.logging_config import logger
from src.models.meal_products import MealProducts
from src.schemas.meal_products import MealProductsCreate, MealProductsUpdate, MealProductsRead


async def get_meal_products(db: AsyncSession, meal_id: int):
    cache_key = f"meal_products:{meal_id}"
    try:
        # Попытка получить данные из кэша
        cached_meal_products = await cache.get(cache_key)
        if cached_meal_products:
            logger.info(f"Cache hit for meal_products: {meal_id}")
            return cached_meal_products  # Это уже список словарей

        logger.info(f"Cache miss for meal_products: {meal_id}. Fetching from database.")

        # Выполнение запроса к базе данных
        query = select(MealProducts).where(MealProducts.meal_id == meal_id)
        result = await db.execute(query)
        meal_products = result.scalars().all()

        # Преобразование результатов в список словарей
        meal_products_list = [MealProductsRead.model_validate(mp).model_dump(mode="json") for mp in meal_products]

        # Сохранение в кэш в виде JSON
        await cache.set(cache_key, meal_products_list)
        logger.info(f"Meal products for meal {meal_id} cached.")
        return meal_products_list

    except Exception as e:
        logger.error(f"Error fetching meal products for meal {meal_id}: {str(e)}")
        raise e


async def add_meal_product(db: AsyncSession, meal_id: int, data: MealProductsCreate) -> MealProductsRead:
    try:
        # Проверка существования продукта в блюде
        query = select(MealProducts).where(
            MealProducts.meal_id == meal_id,
            MealProducts.product_id == data.product_id
        )
        result = await db.execute(query)
        existing_product = result.scalar_one_or_none()

        if existing_product:
            logger.warning(f"Product {data.product_id} already exists in meal {meal_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Product {data.product_id} is already in the meal {meal_id}"
            )

        # Добавление нового продукта
        meal_product = MealProducts(
            meal_id=meal_id,
            product_id=data.product_id,
            product_weight=data.product_weight
        )
        db.add(meal_product)
        await db.commit()
        await db.refresh(meal_product)

        # Инвалидация кэша
        cache_key = f"meal_products:{meal_id}"
        await cache.delete(cache_key)
        logger.info(f"Cache invalidated for meal_products: {meal_id}")

        # Возврат Pydantic-модели
        return MealProductsRead.model_validate(meal_product)

    except Exception as e:
        logger.error(f"Error adding product to meal {meal_id}: {str(e)}")
        raise e


async def update_meal_product(db: AsyncSession, meal_id: int, data: MealProductsUpdate):
    query = select(MealProducts).where(
        MealProducts.meal_id == meal_id,
        MealProducts.product_id == data.product_id
    )
    result = await db.execute(query)

    try:
        # Получаем продукт из блюда
        meal_product = result.scalars().one()

        # Обновляем вес продукта
        meal_product.product_weight = data.product_weight
        await db.commit()
        await db.refresh(meal_product)

        cache_key = f"meal_products:{meal_id}"
        await cache.delete(cache_key)

        # Возвращаем обновлённый объект
        return MealProductsRead.model_validate(meal_product)

    except NoResultFound:
        # Продукт не найден, выбрасываем исключение
        raise HTTPException(
            status_code=404,
            detail=f"Product with ID {data.product_id} in meal {meal_id} not found"
        )

    except Exception as e:
        # Логирование и возврат ошибки
        logger.error(f"Error updating meal product for meal_id {meal_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


async def delete_meal_product(db: AsyncSession, meal_id: int, product_id: int):
    query = select(MealProducts).where(
        and_(MealProducts.meal_id == meal_id, MealProducts.product_id == product_id)
    )
    result = await db.execute(query)

    try:
        # Пытаемся найти запись
        meal_product = result.scalars().one()

        # Удаляем продукт
        await db.delete(meal_product)
        await db.commit()

        cache_key = f"meal_products:{meal_id}"
        await cache.delete(cache_key)

        return {"message": f"Product with ID {product_id} removed from meal {meal_id}"}

    except NoResultFound:
        # Если запись не найдена, выбрасываем исключение
        raise HTTPException(
            status_code=404,
            detail=f"Product with ID {product_id} in meal {meal_id} not found"
        )

    except Exception as e:
        # Обработка других ошибок
        logger.error(f"Error deleting product {product_id} from meal {meal_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )