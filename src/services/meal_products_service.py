from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound
from src.cache.cache import cache
from src.logging_config import logger
from src.models.meal_products import MealProducts
from src.schemas.meal_products import MealProductsCreate, MealProductsUpdate, MealProductsRead

# Получение продуктов для блюда
async def get_meal_products(db: AsyncSession, meal_id: int):
    cache_key = f"meal_products:{meal_id}"
    try:
        cached_meal_products = await cache.get(cache_key)
        if cached_meal_products:
            logger.info(f"Cache hit for meal_products: {meal_id}")
            return [MealProductsRead.model_validate(mp) for mp in cached_meal_products]

        logger.info(f"Cache miss for meal_products: {meal_id}. Fetching from database.")

        query = select(MealProducts).where(MealProducts.meal_id == meal_id)
        result = await db.execute(query)
        meal_products = result.scalars().all()

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
async def add_meal_product(db: AsyncSession, meal_id: int, data: MealProductsCreate) -> MealProductsRead:
    try:
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

        meal_product = MealProducts(
            meal_id=meal_id,
            product_id=data.product_id,
            product_weight=data.product_weight
        )
        db.add(meal_product)
        await db.commit()
        await db.refresh(meal_product)

        cache_key = f"meal_products:{meal_id}"
        await cache.delete(cache_key)
        logger.info(f"Cache invalidated for meal_products: {meal_id}")

        return MealProductsRead.model_validate(meal_product)

    except Exception as e:
        logger.error(f"Error adding product to meal {meal_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Обновление продукта в блюде
async def update_meal_product(db: AsyncSession, meal_id: int, data: MealProductsUpdate):
    try:
        query = select(MealProducts).where(
            MealProducts.meal_id == meal_id,
            MealProducts.product_id == data.product_id
        )
        result = await db.execute(query)
        meal_product = result.scalars().one()

        meal_product.product_weight = data.product_weight
        await db.commit()
        await db.refresh(meal_product)

        cache_key = f"meal_products:{meal_id}"
        await cache.delete(cache_key)
        logger.info(f"Meal product {data.product_id} updated in meal {meal_id}")

        return MealProductsRead.model_validate(meal_product)

    except NoResultFound:
        logger.warning(f"Product {data.product_id} not found in meal {meal_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Product with ID {data.product_id} in meal {meal_id} not found"
        )
    except Exception as e:
        logger.error(f"Error updating meal product for meal_id {meal_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Удаление продукта из блюда
async def delete_meal_product(db: AsyncSession, meal_id: int, product_id: int):
    try:
        query = select(MealProducts).where(
            and_(MealProducts.meal_id == meal_id, MealProducts.product_id == product_id)
        )
        result = await db.execute(query)
        meal_product = result.scalars().one()

        await db.delete(meal_product)
        await db.commit()

        cache_key = f"meal_products:{meal_id}"
        await cache.delete(cache_key)
        logger.info(f"Product {product_id} removed from meal {meal_id}")

        return {"message": f"Product with ID {product_id} removed from meal {meal_id}"}

    except NoResultFound:
        logger.warning(f"Product {product_id} not found in meal {meal_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Product with ID {product_id} in meal {meal_id} not found"
        )
    except Exception as e:
        logger.error(f"Error deleting product {product_id} from meal {meal_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
