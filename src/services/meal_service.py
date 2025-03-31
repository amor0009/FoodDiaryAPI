from datetime import date, timedelta, datetime
import asyncio
from fastapi import HTTPException, status
from sqlalchemy import select, and_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from src.cache.cache import cache
from src.logging_config import logger
from src.models.meal import Meal
from src.models.meal_products import MealProducts
from src.models.product import Product
from src.schemas.meal import MealCreate, MealUpdate, MealRead
from src.services.meal_products_service import update_meal_product, delete_meal_product
from src.services.product_service import recalculate_product_nutrients

# Пересчитывает нутриенты для блюда на основе продуктов
async def recalculate_meal_nutrients(db: AsyncSession, meal: Meal):
    logger.info(f"Recalculating nutrients for meal {meal.id} ({meal.name})")
    total_weight = 0
    total_calories = 0
    total_proteins = 0
    total_fats = 0
    total_carbohydrates = 0
    products = []

    await db.refresh(meal, attribute_names=["meal_products"])

    for meal_product in meal.meal_products:
        db_product = await db.get(Product, meal_product.product_id)
        logger.info(f"PRODUCT - {db_product}")
        if not db_product:
            logger.warning(f"Product with id {meal_product.product_id} not found in the database.")
            continue

        logger.info(f"Processing product: {db_product.name}, weight: {meal_product.product_weight}")

        product_data = await recalculate_product_nutrients(db_product, meal_product.product_weight)

        total_weight += product_data.weight
        total_calories += product_data.calories
        total_proteins += product_data.proteins
        total_fats += product_data.fats
        total_carbohydrates += product_data.carbohydrates

        products.append(product_data)

    logger.info(
        f"Total - Weight: {total_weight}, Calories: {total_calories}, Proteins: {total_proteins}, Fats: {total_fats}, Carbohydrates: {total_carbohydrates}")

    meal.weight = total_weight
    meal.calories = total_calories
    meal.proteins = total_proteins
    meal.fats = total_fats
    meal.carbohydrates = total_carbohydrates

    logger.info(f"Meal {meal.id} nutrient recalculation completed.")
    return MealRead(
        id=meal.id,
        name=meal.name,
        weight=meal.weight,
        calories=meal.calories,
        proteins=meal.proteins,
        fats=meal.fats,
        carbohydrates=meal.carbohydrates,
        recorded_at=meal.recorded_at,
        user_id=meal.user_id,
        products=products
    )

# Добавляет новое блюдо и связанные с ним продукты
async def add_meal(db: AsyncSession, meal: MealCreate, user_id: int):
    logger.info(f"Adding new meal for user {user_id}: {meal.name}")
    try:
        db_meal = Meal(
            name=meal.name,
            calories=meal.calories,
            weight=meal.weight,
            proteins=meal.proteins,
            fats=meal.fats,
            carbohydrates=meal.carbohydrates,
            user_id=user_id
        )
        db.add(db_meal)
        logger.info(f"Meal {meal.name} added to the database. Adding associated products.")

        for product in meal.products:
            db_product = await db.get(Product, product.product_id)
            if not db_product:
                logger.error(f"Product with id {product.product_id} not found.")
                raise ValueError(f"Product with id {product.product_id} not found.")
            meal_product = MealProducts(
                meal_id=db_meal.id,
                product_id=product.product_id,
                product_weight=product.product_weight
            )
            db.add(meal_product)

        await db.commit()
        await db.refresh(db_meal)
        await asyncio.gather(
            cache.delete(f"user_meals:{user_id}"),
            cache.delete(f"user_meals_products:{user_id}:{db_meal.recorded_at}"),
            cache.delete(f"user_meal:{user_id}:{db_meal.id}"),
            cache.delete(f"user_meals:{user_id}:{db_meal.recorded_at}"),
            cache.delete(f"personal_products:{user_id}"),
            cache.delete(f"user_meals_history:{user_id}")
        )

        logger.info(f"Meal {meal.name} with products successfully saved to the database.")

        meal_pydantic = await recalculate_meal_nutrients(db, db_meal)
        return meal_pydantic

    except IntegrityError:
        logger.error(f"Error adding meal {meal.name}. Rolling back.")
        await db.rollback()
        raise ValueError("Failed to create meal or associated meal products.")

# Получает все блюда пользователя и кеширует их
async def get_user_meals(db: AsyncSession, user_id: int):
    cache_key = f"user_meals:{user_id}"
    logger.info(f"Checking cache for user {user_id}'s meals.")
    cached_data = await cache.get(cache_key)

    if cached_data:
        logger.info(f"Cache hit for user {user_id}'s meals.")
        return [MealRead.model_validate(meal) for meal in cached_data]

    logger.info(f"Cache miss for user {user_id}'s meals. Fetching from database.")
    query = select(Meal).where(Meal.user_id == user_id)
    result = await db.execute(query)
    meals = result.scalars().all()
    meal_list = [MealRead.model_validate(meal) for meal in meals]
    await cache.set(cache_key, [meal.model_dump(mode="json") for meal in meal_list], expire=3600)
    logger.info(f"Meals for user {user_id} cached successfully.")
    return meal_list

# Получает блюда пользователя с продуктами для указанной даты и кеширует их
async def get_user_meals_with_products_by_date(db: AsyncSession, user_id: int, target_date: str):
    cache_key = f"user_meals_products:{user_id}:{target_date}"
    logger.info(f"Checking cache for user {user_id}'s meals on {target_date}.")
    cached_data = await cache.get(cache_key)

    if cached_data:
        logger.info(f"Cache hit for user {user_id}'s meals on {target_date}.")
        return [MealRead.model_validate(meal) for meal in cached_data]

    logger.info(f"Cache miss for user {user_id}'s meals on {target_date}. Fetching from database.")
    current_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
    query = (
        select(Meal)
        .options(joinedload(Meal.meal_products).joinedload(MealProducts.product))
        .where(and_(Meal.user_id == user_id, Meal.recorded_at == current_date_obj))
    )

    result = await db.execute(query)
    meals = result.scalars().unique().all()

    formatted_meals = [await recalculate_meal_nutrients(db, meal) for meal in meals]

    await cache.set(cache_key, [meal.model_dump(mode="json") for meal in formatted_meals], expire=3600)
    logger.info(f"Meals for user {user_id} on {target_date} cached successfully.")
    return formatted_meals

# Получает конкретное блюдо по id и кеширует его
async def get_meal_by_id(db: AsyncSession, meal_id: int, user_id: int):
    cache_key = f"user_meal:{user_id}:{meal_id}"
    logger.info(f"Checking cache for meal {meal_id} of user {user_id}.")
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for meal {meal_id} of user {user_id}.")
        return MealRead.model_validate(cached_data)

    logger.info(f"Cache miss for meal {meal_id} of user {user_id}. Fetching from database.")
    query = select(Meal).where(and_(Meal.id == meal_id, Meal.user_id == user_id))
    result = await db.execute(query)
    meal = result.scalar_one_or_none()
    if meal is None:
        logger.warning(f"Meal with id {meal_id} not found for user {user_id}.")
        return None

    meal_dict = MealRead.model_validate(meal).model_dump(mode="json")
    await cache.set(cache_key, meal_dict, expire=3600)
    logger.info(f"Meal {meal_id} of user {user_id} cached successfully.")
    return MealRead.model_validate(meal)

# Получает все блюда пользователя для определённой даты и кеширует их
async def get_meals_by_date(db: AsyncSession, user_id: int, target_date: str):
    cache_key = f"user_meals:{user_id}:{target_date}"
    logger.info(f"Checking cache for meals on {target_date} of user {user_id}.")
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for meals on {target_date} of user {user_id}.")
        return [MealRead.model_validate(meal) for meal in cached_data]

    logger.info(f"Cache miss for meals on {target_date} of user {user_id}. Fetching from database.")
    current_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
    query = select(Meal).where(and_(
        Meal.user_id == user_id,
        Meal.recorded_at == current_date_obj
    ))
    result = await db.execute(query)
    meals = result.scalars().all()
    meals_list = [MealRead.model_validate(meal) for meal in meals]
    await cache.set(cache_key, [meal.model_dump(mode="json") for meal in meals_list], expire=3600)
    logger.info(f"Meals on {target_date} for user {user_id} cached successfully.")
    return meals_list

# Получает блюда пользователя за последние 7 дней и кеширует их
async def get_meals_last_7_days(db: AsyncSession, user_id: int):
    cache_key = f"user_meals_history:{user_id}"
    logger.info(f"Checking cache for last 7 days meals for user {user_id}.")
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for last 7 days meals for user {user_id}.")
        return [MealRead.model_validate(meal) for meal in cached_data]

    logger.info(f"Cache miss for last 7 days meals for user {user_id}. Fetching from database.")
    seven_days_ago = date.today() - timedelta(days=7)
    query = select(Meal).where(and_(
        Meal.user_id == user_id,
        Meal.recorded_at >= seven_days_ago)
    ).order_by(Meal.recorded_at.desc())
    result = await db.execute(query)
    meals = result.scalars().all()
    meals_list = [MealRead.model_validate(meal) for meal in meals]
    await cache.set(cache_key, [meal.model_dump(mode="json") for meal in meals_list], expire=3600)
    logger.info(f"Last 7 days meals for user {user_id} cached successfully.")
    return meals_list

# Обновляет данные о блюде и его продуктах
async def update_meal(db: AsyncSession, meal_update: MealUpdate, meal_id: int, user_id: int):
    logger.info(f"Updating meal {meal_id} for user {user_id}.")
    db_meal = await db.execute(
        select(Meal)
        .options(joinedload(Meal.meal_products).joinedload(MealProducts.product))
        .where(Meal.id == meal_id, Meal.user_id == user_id)
    )
    db_meal = db_meal.unique().scalar_one_or_none()
    if not db_meal:
        logger.warning(f"Meal {meal_id} not found for user {user_id}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )

    if meal_update.name is not None:
        db_meal.name = meal_update.name

    if meal_update.products is not None:
        existing_products = {mp.product_id: mp for mp in db_meal.meal_products}
        update_products = {p.product_id: p for p in meal_update.products}
        for product_id in existing_products.keys() - update_products.keys():
            await delete_meal_product(db, meal_id, product_id)

        for product_id, product_data in update_products.items():
            if product_id in existing_products:
                await update_meal_product(db, meal_id, product_data)
            else:
                db_product = await db.get(Product, product_id)
                if not db_product:
                    logger.error(f"Product with id {product_id} not found.")
                    raise ValueError(f"Product with id {product_id} not found.")
                new_meal_product = MealProducts(
                    meal_id=meal_id,
                    product_id=product_id,
                    product_weight=product_data.product_weight
                )
                new_meal_product.product = db_product
                db_meal.meal_products.append(new_meal_product)
                db.add(new_meal_product)

    await db.commit()
    logger.info(f"Meal {meal_id} for user {user_id} updated successfully.")

    db_meal = await db.execute(
        select(Meal)
        .options(joinedload(Meal.meal_products).joinedload(MealProducts.product))
        .where(Meal.id == meal_id)
    )
    db_meal = db_meal.unique().scalar_one_or_none()
    if not db_meal:
        logger.error(f"Meal {meal_id} not found after update.")
        raise HTTPException(status_code=500, detail="Meal not found after update")

    updated_meal = await recalculate_meal_nutrients(db, db_meal)
    await db.commit()

    await asyncio.gather(
        cache.delete(f"user_meals:{user_id}"),
        cache.delete(f"user_meals_products:{user_id}:{db_meal.recorded_at}"),
        cache.delete(f"user_meal:{user_id}:{db_meal.id}"),
        cache.delete(f"user_meals:{user_id}:{db_meal.recorded_at}"),
        cache.delete(f"personal_products:{user_id}"),
        cache.delete(f"user_meals_history:{user_id}")
    )

    logger.info(f"Meal {meal_id} for user {user_id} cache deleted.")
    return updated_meal

# Удаляет блюдо и связанные с ним продукты
async def delete_meal(db: AsyncSession, meal_id: int, user_id: int):
    logger.info(f"Deleting meal {meal_id} for user {user_id}.")
    meal = await get_meal_by_id(db, meal_id, user_id)
    if not meal:
        logger.warning(f"Meal {meal_id} not found for user {user_id}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )

    db_meal = await db.get(Meal, meal_id)

    await db.execute(delete(MealProducts).where(MealProducts.meal_id == meal_id))

    await db.delete(db_meal)
    await db.commit()
    logger.info(f"Meal {meal_id} for user {user_id} deleted successfully.")
    await asyncio.gather(
        cache.delete(f"user_meals:{user_id}"),
        cache.delete(f"user_meals_products:{user_id}:{db_meal.recorded_at}"),
        cache.delete(f"user_meal:{user_id}:{db_meal.id}"),
        cache.delete(f"user_meals:{user_id}:{db_meal.recorded_at}"),
        cache.delete(f"personal_products:{user_id}"),
        cache.delete(f"user_meals_history:{user_id}")
    )
    return {"message": "Meal and its products deleted successfully"}
