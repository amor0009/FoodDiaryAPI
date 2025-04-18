from datetime import datetime, date
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.cache.cache import cache
from src.logging_config import logger
from src.schemas.user_weight import UserWeightUpdate, UserWeightRead
from src.daos.user_weight_dao import UserWeightDAO


class UserWeightService:

    # Функция для сохранения или обновления веса пользователя в базе данных
    @classmethod
    async def save_or_update_weight(
            cls,
            user_weight: UserWeightUpdate,
            db: AsyncSession,
            user_id: int
    ):
        cache_key = f"user_weight:{user_id}:{date.today()}"
        try:
            current_date = date.today()

            logger.info(f"Saving/updating weight for user {user_id} on {current_date}")
            weight_record = await UserWeightDAO.create_or_update(
                db,
                user_id=user_id,
                weight=user_weight.weight,
                target_date=current_date
            )

            # Очищаем кэш для текущего веса
            await cache.delete(cache_key)
            logger.info(f"Weight deleted from cache for user {user_id} on {current_date}")

            return UserWeightRead.model_validate(weight_record)
        except Exception as e:
            logger.error(f"Error saving or updating weight for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # Функция для получения текущего веса пользователя на указанную дату
    @classmethod
    async def get_current_weight(
            cls,
            current_date: str,
            db: AsyncSession,
            user_id: int
    ):
        cache_key = f"user_weight:{user_id}:{current_date}"
        try:
            # Проверяем, есть ли данные в кэше
            cached_weight = await cache.get(cache_key)
            if cached_weight:
                logger.info(f"Cache hit for current weight of user {user_id} on {current_date}")
                return UserWeightRead.model_validate(cached_weight)

            logger.info(f"Cache miss for current weight of user {user_id} on {current_date}")
            current_date_obj = datetime.strptime(current_date, '%Y-%m-%d').date()

            # Получаем вес из базы данных
            weight_record = await UserWeightDAO.get_by_date(db, user_id, current_date_obj)

            if weight_record:
                # Сохраняем найденный вес в кэш
                weight_pydantic = UserWeightRead.model_validate(weight_record)
                await cache.set(cache_key, weight_pydantic.model_dump(mode="json"), expire=3600)
                logger.info(f"Current weight cached for user {user_id} on {current_date}")
                return weight_pydantic

            return None
        except Exception as e:
            logger.error(f"Error retrieving current weight for user {user_id} on {current_date}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # Функция для получения истории веса пользователя за последние 30 дней
    @classmethod
    async def get_weights(cls, db: AsyncSession, user_id: int):
        try:
            logger.info(f"Retrieving weight history for user {user_id} (last 30 days)")
            weight_history = await UserWeightDAO.get_last_30_days(db, user_id)
            return [UserWeightRead.model_validate(weight) for weight in weight_history]
        except Exception as e:
            logger.error(f"Error retrieving weight history for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
