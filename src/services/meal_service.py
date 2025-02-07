from datetime import date, timedelta, datetime
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


async def recalculate_meal_nutrients(meal: Meal):
    """Пересчитывает характеристики приёма пищи на основе продуктов."""
    logger.info(f"Recalculating nutrients for meal {meal.id} ({meal.name})")
    total_weight = 0
    total_calories = 0
    total_proteins = 0
    total_fats = 0
    total_carbohydrates = 0
    products = []

    for meal_product in meal.meal_products:
        db_product = meal_product.product
        logger.info(f"PRODUCT - {db_product}")
        if not db_product:
            continue

        logger.info(f"Processing product: {db_product.name}, weight: {meal_product.product_weight}")

        # Получаем перерасчитанные характеристики продукта
        product_data = await recalculate_product_nutrients(db_product, meal_product.product_weight)

        total_weight += product_data.weight
        total_calories += product_data.calories
        total_proteins += product_data.proteins
        total_fats += product_data.fats
        total_carbohydrates += product_data.carbohydrates

        products.append(product_data)

    # Логируем итоговые результаты
    logger.info(
        f"Total - Weight: {total_weight}, Calories: {total_calories}, Proteins: {total_proteins}, Fats: {total_fats}, Carbohydrates: {total_carbohydrates}")

    # Обновляем характеристики приёма пищи
    meal.weight = total_weight
    meal.calories = total_calories
    meal.proteins = total_proteins
    meal.fats = total_fats
    meal.carbohydrates = total_carbohydrates

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


async def add_meal(db: AsyncSession, meal: MealCreate, user_id: int):
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

        for product in meal.products:
            db_product = await db.get(Product, product.product_id)
            if not db_product:
                raise ValueError(f"Product with id {product.product_id} not found.")
            meal_product = MealProducts(
                meal_id=db_meal.id,
                product_id=product.product_id,
                product_weight=product.product_weight
            )
            # Убедитесь, что объект добавлен в сессию
            meal_product.product = db_product
            db_meal.meal_products.append(meal_product)
            db.add(meal_product)

        await db.commit()

        meal_pydantic = await recalculate_meal_nutrients(db_meal)
        return meal_pydantic

    except IntegrityError:
        await db.rollback()
        raise ValueError("Failed to create meal or associated meal products.")


async def get_user_meals(db: AsyncSession, user_id: int):
    cache_key = f"user_meals:{user_id}"
    cached_data = await cache.get(cache_key)

    if cached_data:
        return [MealRead.model_validate(meal) for meal in cached_data]

    query = select(Meal).where(Meal.user_id == user_id)
    result = await db.execute(query)
    meals = result.scalars().all()
    meal_list = [MealRead.model_validate(meal) for meal in meals]
    await cache.set(cache_key, [meal.model_dump(mode="json") for meal in meal_list], expire=3600)
    return meal_list


async def get_user_meals_with_products_by_date(db: AsyncSession, user_id: int, target_date: str):
    cache_key = f"user_meals_products:{user_id}:{target_date}"
    cached_data = await cache.get(cache_key)

    if cached_data:
        return [MealRead.model_validate(meal) for meal in cached_data]

    current_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
    query = (
        select(Meal)
        .options(joinedload(Meal.meal_products).joinedload(MealProducts.product))
        .where(and_(Meal.user_id == user_id, Meal.recorded_at == current_date_obj))
    )

    result = await db.execute(query)
    meals = result.scalars().unique().all()

    # 🔹 Пересчитываем характеристики каждого приёма пищи
    formatted_meals = [await recalculate_meal_nutrients(meal) for meal in meals]

    await cache.set(cache_key, [meal.model_dump(mode="json") for meal in formatted_meals], expire=3600)
    return formatted_meals


async def get_meal_by_id(db: AsyncSession, meal_id: int, user_id: int):
    cache_key = f"user_meal:{user_id}:{meal_id}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return MealRead.model_validate(cached_data)

    query = select(Meal).where(and_(Meal.id == meal_id, Meal.user_id == user_id))
    result = await db.execute(query)
    meal = result.scalar_one_or_none()
    if meal is None:
        return None

    meal_dict = MealRead.model_validate(meal).model_dump(mode="json")
    await cache.set(cache_key, meal_dict, expire=3600)
    return MealRead.model_validate(meal)


async def get_meals_by_date(db: AsyncSession, user_id: int, target_date: str):
    cache_key = f"user_meals:{user_id}:{target_date}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return [MealRead.model_validate(meal) for meal in cached_data]

    current_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
    query = select(Meal).where(and_(
        Meal.user_id == user_id,
        Meal.recorded_at == current_date_obj
    ))
    result = await db.execute(query)
    meals = result.scalars().all()
    meals_list = [MealRead.model_validate(meal) for meal in meals]
    await cache.set(cache_key, [meal.model_dump(mode="json") for meal in meals_list], expire=3600)
    return meals_list


async def get_meals_last_7_days(db: AsyncSession, user_id: int):
    cache_key= f"user_meals_history:{user_id}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return [MealRead.model_validate(meal) for meal in cached_data]

    seven_days_ago = date.today() - timedelta(days=7)
    query = select(Meal).where(and_(
        Meal.user_id == user_id,
        Meal.recorded_at >= seven_days_ago)
    ).order_by(Meal.recorded_at.desc())
    result = await db.execute(query)
    meals = result.scalars().all()
    meals_list = [MealRead.model_validate(meal) for meal in meals]
    await cache.set(cache_key, [meal.model_dump(mode="json") for meal in meals_list], expire=3600)
    return meals_list


async def update_meal(db: AsyncSession, meal_update: MealUpdate, meal_id: int, user_id: int):
    # Получаем блюдо с продуктами
    db_meal = await db.execute(
        select(Meal)
        .options(joinedload(Meal.meal_products).joinedload(MealProducts.product))
        .where(Meal.id == meal_id, Meal.user_id == user_id)
    )
    db_meal = db_meal.unique().scalar_one_or_none()
    print(MealRead.model_validate(db_meal))
    if not db_meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )

    # Обновление основных данных блюда
    if meal_update.name is not None:
        db_meal.name = meal_update.name

    # Обновление продуктов
    if meal_update.products is not None:
        existing_products = {mp.product_id: mp for mp in db_meal.meal_products}
        update_products = {p.product_id: p for p in meal_update.products}
        print(update_products, existing_products)
        # Удаление старых продуктов
        for product_id in existing_products.keys() - update_products.keys():
            await delete_meal_product(db, meal_id, product_id)

        # Обновление существующих или добавление новых продуктов
        for product_id, product_data in update_products.items():
            if product_id in existing_products:
                print(product_id)
                await update_meal_product(db, meal_id, product_data)
            else:
                db_product = await db.get(Product, product_id)
                if not db_product:
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

    # Обновляем характеристики блюда после внесения изменений
    db_meal = await db.execute(
        select(Meal)
        .options(joinedload(Meal.meal_products).joinedload(MealProducts.product))
        .where(Meal.id == meal_id)
    )
    db_meal = db_meal.unique().scalar_one_or_none()
    print(MealRead.model_validate(db_meal))
    if not db_meal:
        raise HTTPException(status_code=500, detail="Meal not found after update")

    updated_meal = await recalculate_meal_nutrients(db_meal)
    await db.commit()

    # Очистка кэша
    await cache.delete(f"user_meals:{user_id}")
    if db_meal.recorded_at:
        await cache.delete(f"user_meals:{user_id}:{db_meal.recorded_at}")

    return updated_meal


async def delete_meal(db: AsyncSession, meal_id: int, user_id: int):
    meal = await get_meal_by_id(db, meal_id, user_id)
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )

    db_meal = await db.get(Meal, meal_id)

    # Массовое удаление продуктов, связанных с приёмом пищи
    await db.execute(delete(MealProducts).where(MealProducts.meal_id == meal_id))

    # Удаление самого приёма пищи
    await db.delete(db_meal)
    await db.commit()
    await cache.delete(f"user_meals:{user_id}")
    if db_meal.recorded_at:
        await cache.delete(f"user_meals:{user_id}:{db_meal.recorded_at}")
    return {"message": "Meal and its products deleted successfully"}
