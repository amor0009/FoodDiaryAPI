from datetime import date, datetime
import asyncio
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.cache.cache import cache
from src.logging_config import logger
from src.models.meal import Meal
from src.models.meal_products import MealProducts
from src.models.product import Product
from src.schemas.meal import MealCreate, MealUpdate, MealRead
from src.services.meal_products_service import MealProductsService
from src.services.product_service import ProductService
from src.daos.meal_dao import MealDAO


class MealService:

    # Пересчитывает нутриенты для блюда на основе продуктов
    @classmethod
    async def recalculate_meal_nutrients(cls, db: AsyncSession, meal: Meal):
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

            product_data = await ProductService.recalculate_product_nutrients(db_product, meal_product.product_weight)

            total_weight += product_data.weight
            total_calories += product_data.calories
            total_proteins += product_data.proteins
            total_fats += product_data.fats
            total_carbohydrates += product_data.carbohydrates

            products.append(product_data)

        logger.info(
            f"Total - Weight: {total_weight}, Calories: {total_calories}, Proteins: {total_proteins}, "
            f"Fats: {total_fats}, Carbohydrates: {total_carbohydrates}")

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
    @classmethod
    async def add_meal(cls, db: AsyncSession, meal: MealCreate, user_id: int):
        logger.info(f"Adding new meal for user {user_id}: {meal.name}")
        try:
            # Создаем базовую запись блюда
            meal_data = {
                "name": meal.name,
                "user_id": user_id,
                "calories": 0,  # Будет пересчитано
                "weight": 0,  # Будет пересчитано
                "proteins": 0,
                "fats": 0,
                "carbohydrates": 0
            }

            # Подготавливаем данные о продуктах
            products_data = [
                {
                    "product_id": p.product_id,
                    "product_weight": p.product_weight
                } for p in meal.products
            ]

            # Создаем блюдо через DAO
            db_meal = await MealDAO.create_with_products(db, meal_data, products_data)

            # Очищаем кеш
            await cls._clear_meal_cache(user_id, db_meal.id, db_meal.recorded_at)
            logger.info(f"Meal {meal.name} with products successfully saved to the database.")

            # Пересчитываем нутриенты и возвращаем результат
            return await cls.recalculate_meal_nutrients(db, db_meal)

        except IntegrityError as e:
            logger.error(f"Error adding meal {meal.name}. Rolling back. Error: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create meal or associated meal products"
            )

    # Получает все блюда пользователя и кеширует их
    @classmethod
    async def get_user_meals(cls, db: AsyncSession, user_id: int):
        cache_key = f"user_meals:{user_id}"
        logger.info(f"Checking cache for user {user_id}'s meals.")
        cached_data = await cache.get(cache_key)

        if cached_data:
            logger.info(f"Cache hit for user {user_id}'s meals.")
            return [MealRead.model_validate(meal) for meal in cached_data]

        logger.info(f"Cache miss for user {user_id}'s meals. Fetching from database.")
        meals = await MealDAO.get_user_meals(db, user_id)
        meal_list = [MealRead.model_validate(meal) for meal in meals]

        await cache.set(cache_key, [meal.model_dump(mode="json") for meal in meal_list], expire=3600)
        logger.info(f"Meals for user {user_id} cached successfully.")
        return meal_list

    # Получает блюда пользователя с продуктами для указанной даты и кеширует их
    @classmethod
    async def get_user_meals_with_products_by_date(cls, db: AsyncSession, user_id: int, target_date: str):
        cache_key = f"user_meals_products:{user_id}:{target_date}"
        logger.info(f"Checking cache for user {user_id}'s meals on {target_date}.")
        cached_data = await cache.get(cache_key)

        if cached_data:
            logger.info(f"Cache hit for user {user_id}'s meals on {target_date}.")
            return [MealRead.model_validate(meal) for meal in cached_data]

        logger.info(f"Cache miss for user {user_id}'s meals on {target_date}. Fetching from database.")
        current_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        meals = await MealDAO.get_meals_with_products_by_date(db, user_id, current_date_obj)

        formatted_meals = [await cls.recalculate_meal_nutrients(db, meal) for meal in meals]

        await cache.set(cache_key, [meal.model_dump(mode="json") for meal in formatted_meals], expire=3600)
        logger.info(f"Meals for user {user_id} on {target_date} cached successfully.")
        return formatted_meals

    # Получает конкретное блюдо по id и кеширует его
    @classmethod
    async def get_meal_by_id(cls, db: AsyncSession, meal_id: int, user_id: int):
        cache_key = f"user_meal:{user_id}:{meal_id}"
        logger.info(f"Checking cache for meal {meal_id} of user {user_id}.")
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for meal {meal_id} of user {user_id}.")
            return MealRead.model_validate(cached_data)

        logger.info(f"Cache miss for meal {meal_id} of user {user_id}. Fetching from database.")
        meal = await MealDAO.get_meal_by_id_with_products(db, meal_id, user_id)
        if meal is None:
            logger.warning(f"Meal with id {meal_id} not found for user {user_id}.")
            return None

        meal_dict = MealRead.model_validate(meal).model_dump(mode="json")
        await cache.set(cache_key, meal_dict, expire=3600)
        logger.info(f"Meal {meal_id} of user {user_id} cached successfully.")
        return MealRead.model_validate(meal)

    # Получает все блюда пользователя для определённой даты и кеширует их
    @classmethod
    async def get_meals_by_date(cls, db: AsyncSession, user_id: int, target_date: str):
        cache_key = f"user_meals:{user_id}:{target_date}"
        logger.info(f"Checking cache for meals on {target_date} of user {user_id}.")
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for meals on {target_date} of user {user_id}.")
            return [MealRead.model_validate(meal) for meal in cached_data]

        logger.info(f"Cache miss for meals on {target_date} of user {user_id}. Fetching from database.")
        current_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        meals = await MealDAO.get_meals_by_date(db, user_id, current_date_obj)
        meals_list = [MealRead.model_validate(meal) for meal in meals]

        await cache.set(cache_key, [meal.model_dump(mode="json") for meal in meals_list], expire=3600)
        logger.info(f"Meals on {target_date} for user {user_id} cached successfully.")
        return meals_list

    # Получает блюда пользователя за последние 7 дней и кеширует их
    @classmethod
    async def get_meals_last_7_days(cls, db: AsyncSession, user_id: int):
        cache_key = f"user_meals_history:{user_id}"
        logger.info(f"Checking cache for last 7 days meals for user {user_id}.")
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for last 7 days meals for user {user_id}.")
            return [MealRead.model_validate(meal) for meal in cached_data]

        logger.info(f"Cache miss for last 7 days meals for user {user_id}. Fetching from database.")
        meals = await MealDAO.get_meals_last_days(db, user_id, days=7)
        meals_list = [MealRead.model_validate(meal) for meal in meals]

        await cache.set(cache_key, [meal.model_dump(mode="json") for meal in meals_list], expire=3600)
        logger.info(f"Last 7 days meals for user {user_id} cached successfully.")
        return meals_list

    # Обновляет данные о блюде и его продуктах
    @classmethod
    async def update_meal(cls, db: AsyncSession, meal_update: MealUpdate, meal_id: int, user_id: int):
        logger.info(f"Updating meal {meal_id} for user {user_id}.")

        # Получаем блюдо с продуктами
        db_meal = await MealDAO.get_meal_by_id_with_products(db, meal_id, user_id)
        if not db_meal:
            logger.warning(f"Meal {meal_id} not found for user {user_id}.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meal not found"
            )

        # Обновляем название если нужно
        if meal_update.name is not None:
            db_meal.name = meal_update.name

        # Обновляем продукты если нужно
        if meal_update.products is not None:
            existing_products = {mp.product_id: mp for mp in db_meal.meal_products}
            update_products = {p.product_id: p for p in meal_update.products}

            # Удаляем отсутствующие продукты
            for product_id in existing_products.keys() - update_products.keys():
                await MealProductsService.delete_meal_product(db, meal_id, product_id)

            # Добавляем/обновляем продукты
            for product_id, product_data in update_products.items():
                if product_id in existing_products:
                    await MealProductsService.update_meal_product(db, meal_id, product_data)
                else:
                    db_product = await db.get(Product, product_id)
                    if not db_product:
                        logger.error(f"Product with id {product_id} not found.")
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Product with id {product_id} not found"
                        )
                    new_meal_product = MealProducts(
                        meal_id=meal_id,
                        product_id=product_id,
                        product_weight=product_data.product_weight
                    )
                    db.add(new_meal_product)

        await db.commit()
        logger.info(f"Meal {meal_id} for user {user_id} updated successfully.")

        # Пересчитываем нутриенты
        updated_meal = await cls.recalculate_meal_nutrients(db, db_meal)

        # Очищаем кеш
        await cls._clear_meal_cache(user_id, meal_id, db_meal.recorded_at)
        logger.info(f"Meal {meal_id} for user {user_id} cache deleted.")

        return updated_meal

    # Удаляет блюдо и связанные с ним продукты
    @classmethod
    async def delete_meal(cls, db: AsyncSession, meal_id: int, user_id: int):
        logger.info(f"Deleting meal {meal_id} for user {user_id}.")

        # Проверяем существование блюда
        meal = await MealDAO.find_by_id(db, meal_id)
        if not meal or meal.user_id != user_id:
            logger.warning(f"Meal {meal_id} not found for user {user_id}.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meal not found"
            )

        # Удаляем продукты блюда
        await MealDAO.delete_meal_products(db, meal_id)

        # Удаляем само блюдо
        await db.delete(meal)
        await db.commit()

        # Очищаем кеш
        await cls._clear_meal_cache(user_id, meal_id, meal.recorded_at)
        logger.info(f"Meal {meal_id} for user {user_id} deleted successfully.")

        return {"message": "Meal and its products deleted successfully"}

    # Внутренний метод для очистки кеша
    @classmethod
    async def _clear_meal_cache(cls, user_id: int, meal_id: int = None, recorded_at: date = None):
        keys = [
            f"user_meals:{user_id}",
            f"user_meals_history:{user_id}",
            f"personal_products:{user_id}"
        ]
        if meal_id:
            keys.append(f"user_meal:{user_id}:{meal_id}")
        if recorded_at:
            recorded_date_str = recorded_at.strftime('%Y-%m-%d')
            keys.extend([
                f"user_meals_products:{user_id}:{recorded_date_str}",
                f"user_meals:{user_id}:{recorded_date_str}"
            ])

        await asyncio.gather(*(cache.delete(k) for k in keys))
        logger.info(f"Cleared cache for keys: {keys}")
