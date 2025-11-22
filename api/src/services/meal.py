from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID
import asyncio
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.cache.cache import cache
from api.logging_config import logger
from api.src.models.meal import Meal
from api.src.models.product import Product
from api.src.schemas.meal import MealCreate, MealUpdate, MealRead
from api.src.repositories.meal.base import BaseMealRepository
from api.src.repositories.meal_products.base import BaseMealProductsRepository
from api.src.services.converters.meal import convert_meal_model_to_schema


@dataclass(slots=True)
class MealService:
    _meal_repository: BaseMealRepository
    _meal_products_repository: BaseMealProductsRepository

    async def recalculate_meal_nutrients(self, session: AsyncSession, meal: Meal) -> Meal:
        logger.info(f"Recalculating nutrients for meal {meal.id} ({meal.name})")
        total_weight = 0.0
        total_calories = 0.0
        total_proteins = 0.0
        total_fats = 0.0
        total_carbohydrates = 0.0

        await session.refresh(meal, attribute_names=["meal_products"])

        for meal_product in meal.meal_products:
            db_product = await session.get(Product, meal_product.product_id)
            if not db_product:
                logger.warning(f"Product with id {meal_product.product_id} not found in the database.")
                continue

            ratio = meal_product.product_weight / 100.0
            product_calories = db_product.calories * ratio
            product_proteins = db_product.proteins * ratio
            product_fats = db_product.fats * ratio
            product_carbohydrates = db_product.carbohydrates * ratio

            total_weight += meal_product.product_weight
            total_calories += product_calories
            total_proteins += product_proteins
            total_fats += product_fats
            total_carbohydrates += product_carbohydrates

        logger.info(
            f"Total - Weight: {total_weight}, Calories: {total_calories}, Proteins: {total_proteins}, "
            f"Fats: {total_fats}, Carbohydrates: {total_carbohydrates}")

        meal.weight = total_weight
        meal.calories = total_calories
        meal.proteins = total_proteins
        meal.fats = total_fats
        meal.carbohydrates = total_carbohydrates

        session.add(meal)
        await session.commit()

        refreshed_meal = await self._meal_repository.get_meal_by_id_with_products(session, meal.id, meal.user_id)

        logger.info(f"Meal {meal.id} nutrient recalculation completed.")
        return refreshed_meal

    async def add_meal(self, session: AsyncSession, meal: MealCreate, user_id: UUID) -> MealRead:
        logger.info(f"Adding new meal for user {user_id}: {meal.name}")
        try:
            meal_data = {
                "name": meal.name,
                "user_id": user_id,
                "calories": 0,
                "weight": 0,
                "proteins": 0,
                "fats": 0,
                "carbohydrates": 0
            }

            db_meal = await self._meal_repository.create_meal(session, meal_data)
            await session.flush()

            for product in meal.products:
                await self._meal_products_repository.create_meal_product(
                    session,
                    db_meal.id,
                    product.product_id,
                    product.product_weight
                )

            recalculated_meal = await self.recalculate_meal_nutrients(session, db_meal)
            await self._clear_meal_cache(user_id, recalculated_meal.id, recalculated_meal.created_at)
            logger.info(f"Meal {meal.name} with products successfully saved to the database.")

            return convert_meal_model_to_schema(recalculated_meal)

        except IntegrityError as e:
            logger.error(f"Error adding meal {meal.name}. Rolling back. Error: {str(e)}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create meal or associated meal products"
            )

    async def update_meal(self, session: AsyncSession, meal_update: MealUpdate, meal_id: UUID,
                          user_id: UUID) -> MealRead:
        logger.info(f"Updating meal {meal_id} for user {user_id}.")

        db_meal = await self._meal_repository.get_meal_by_id_with_products(session, meal_id, user_id)
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
                meal_product = await self._meal_products_repository.get_meal_product(session, meal_id, product_id)
                if meal_product:
                    await self._meal_products_repository.delete_meal_product(session, meal_product)

            for product_id, product_data in update_products.items():
                if product_id in existing_products:
                    meal_product = existing_products[product_id]
                    await self._meal_products_repository.update_meal_product(
                        session, meal_product, product_data.product_weight
                    )
                else:
                    db_product = await session.get(Product, product_id)
                    if not db_product:
                        logger.error(f"Product with id {product_id} not found.")
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Product with id {product_id} not found"
                        )
                    await self._meal_products_repository.create_meal_product(
                        session, meal_id, product_id, product_data.product_weight
                    )

        recalculated_meal = await self.recalculate_meal_nutrients(session, db_meal)
        await self._clear_meal_cache(user_id, meal_id, recalculated_meal.created_at)
        logger.info(f"Meal {meal_id} for user {user_id} updated successfully.")

        return convert_meal_model_to_schema(recalculated_meal)

    async def get_user_meals(self, session: AsyncSession, user_id: UUID) -> list[MealRead]:
        cache_key = f"user_meals:{user_id}"
        logger.info(f"Checking cache for user {user_id}'s meals.")
        cached_data = await cache.get(cache_key)

        if cached_data:
            logger.info(f"Cache hit for user {user_id}'s meals.")
            return [MealRead.model_validate(meal) for meal in cached_data]

        logger.info(f"Cache miss for user {user_id}'s meals. Fetching from database.")
        meals = await self._meal_repository.get_user_meals(session, user_id)
        meal_list = [convert_meal_model_to_schema(meal) for meal in meals]
        await cache.set(cache_key, [meal.model_dump(mode="json") for meal in meal_list], expire=3600)
        logger.info(f"Meals for user {user_id} cached successfully.")
        return meal_list

    async def get_user_meals_with_products_by_date(self, session: AsyncSession, user_id: UUID, target_date: str) -> list[MealRead]:
        cache_key = f"user_meals_products:{user_id}:{target_date}"
        logger.info(f"Checking cache for user {user_id}'s meals on {target_date}.")
        cached_data = await cache.get(cache_key)

        if cached_data:
            logger.info(f"Cache hit for user {user_id}'s meals on {target_date}.")
            return [MealRead.model_validate(meal) for meal in cached_data]

        logger.info(f"Cache miss for user {user_id}'s meals on {target_date}. Fetching from database.")
        current_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        meals = await self._meal_repository.get_meals_with_products_by_date(session, user_id, current_date_obj)
        meal_list = [convert_meal_model_to_schema(meal) for meal in meals]

        await cache.set(cache_key, [meal.model_dump(mode="json") for meal in meal_list], expire=3600)
        logger.info(f"Meals for user {user_id} on {target_date} cached successfully.")
        return meal_list

    async def get_meal_by_id(self, session: AsyncSession, meal_id: UUID, user_id: UUID) -> MealRead | None:
        cache_key = f"user_meal:{user_id}:{meal_id}"
        logger.info(f"Checking cache for meal {meal_id} of user {user_id}.")
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for meal {meal_id} of user {user_id}.")
            return MealRead.model_validate(cached_data)

        logger.info(f"Cache miss for meal {meal_id} of user {user_id}. Fetching from database.")
        meal = await self._meal_repository.get_meal_by_id_with_products(session, meal_id, user_id)
        if meal is None:
            logger.warning(f"Meal with id {meal_id} not found for user {user_id}.")
            return None

        meal_schema = convert_meal_model_to_schema(meal)
        await cache.set(cache_key, meal_schema.model_dump(mode="json"), expire=3600)
        logger.info(f"Meal {meal_id} of user {user_id} cached successfully.")
        return meal_schema

    async def get_meals_by_date(self, session: AsyncSession, user_id: UUID, target_date: str) -> list[MealRead]:
        cache_key = f"user_meals:{user_id}:{target_date}"
        logger.info(f"Checking cache for meals on {target_date} of user {user_id}.")
        cached_data = await cache.get(cache_key)

        if cached_data:
            logger.info(f"Cache hit for user {user_id}'s meals on {target_date}.")
            return [MealRead.model_validate(meal) for meal in cached_data]

        logger.info(f"Cache miss for meals on {target_date} of user {user_id}. Fetching from database.")
        current_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        meals = await self._meal_repository.get_meals_by_date(session, user_id, current_date_obj)
        meals_list = [convert_meal_model_to_schema(meal) for meal in meals]

        await cache.set(cache_key, [meal.model_dump(mode="json") for meal in meals_list], expire=3600)
        logger.info(f"Meals on {target_date} for user {user_id} cached successfully.")
        return meals_list

    async def get_meals_last_7_days(self, session: AsyncSession, user_id: UUID) -> list[MealRead]:
        cache_key = f"user_meals_history:{user_id}"
        logger.info(f"Checking cache for last 7 days meals for user {user_id}.")
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for last 7 days meals for user {user_id}.")
            return [MealRead.model_validate(meal) for meal in cached_data]

        logger.info(f"Cache miss for last 7 days meals for user {user_id}. Fetching from database.")
        meals = await self._meal_repository.get_meals_last_days(session, user_id, days=7)
        meals_list = [convert_meal_model_to_schema(meal) for meal in meals]

        await cache.set(cache_key, [meal.model_dump(mode="json") for meal in meals_list], expire=3600)
        logger.info(f"Last 7 days meals for user {user_id} cached successfully.")
        return meals_list

    async def delete_meal(self, session: AsyncSession, meal_id: UUID, user_id: UUID) -> dict:
        logger.info(f"Deleting meal {meal_id} for user {user_id}.")

        meal = await self._meal_repository.get_by_id(session, meal_id)
        if not meal or meal.user_id != user_id:
            logger.warning(f"Meal {meal_id} not found for user {user_id}.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meal not found"
            )

        await self._meal_repository.delete_meal_products(session, meal_id)
        await self._meal_repository.delete(session, meal_id)
        await session.commit()

        await self._clear_meal_cache(user_id, meal_id, meal.created_at)
        logger.info(f"Meal {meal_id} for user {user_id} deleted successfully.")

        return {"message": "Meal and its products deleted successfully"}

    async def _clear_meal_cache(self, user_id: UUID, meal_id: UUID = None, recorded_at: date = None):
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
