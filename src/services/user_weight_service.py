from datetime import datetime, timedelta, date
from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.cache.cache import cache
from src.logging_config import logger
from src.models.user_weight import UserWeight
from src.schemas.user_weight import UserWeightUpdate, UserWeightRead

# Функция для сохранения или обновления веса пользователя в базе данных
async def save_or_update_weight(user_weight: UserWeightUpdate, db: AsyncSession, user_id: int):
    cache_key = f"user_weight:{user_id}:{date.today()}"
    try:
        current_date = date.today()

        # Проверяем, существует ли запись о весе за текущую дату
        query = select(UserWeight).where(and_(
            UserWeight.user_id == user_id,
            UserWeight.recorded_at == current_date
        ))
        result = await db.execute(query)
        user_weight_db = result.scalar_one_or_none()

        if user_weight_db:
            # Если запись существует, обновляем вес
            logger.info(f"Updating weight for user {user_id} on {current_date}")
            user_weight_db.weight = user_weight.weight
        else:
            # Иначе создаем новую запись о весе
            logger.info(f"Creating new weight record for user {user_id}")
            user_weight_db = UserWeight(
                user_id=user_id,
                weight=user_weight.weight,
                recorded_at=current_date
            )
            db.add(user_weight_db)

        # Сохраняем изменения в БД
        await db.commit()
        # Очищаем кэш для текущего веса
        await cache.delete(cache_key)
        logger.info(f"Weight deleted from cache for user {user_id} on {current_date}")

        return UserWeightRead.model_validate(user_weight_db)
    except Exception as e:
        logger.error(f"Error saving or updating weight for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Функция для получения текущего веса пользователя на указанную дату.
async def get_current_weight(current_date: str, db: AsyncSession, user_id: int):
    cache_key = f"user_weight:{user_id}:{current_date}"
    try:
        # Проверяем, есть ли данные в кэше
        cached_weight = await cache.get(cache_key)
        if cached_weight:
            logger.info(f"Cache hit for current weight of user {user_id} on {current_date}")
            return UserWeightRead.model_validate(cached_weight)

        logger.info(f"Cache miss for current weight of user {user_id} on {current_date}")
        # Преобразуем строку в объект datetime
        current_date_obj = datetime.strptime(current_date, '%Y-%m-%d').date()

        # Запрашиваем вес пользователя за указанную дату
        query = select(UserWeight).where(and_(
            (UserWeight.user_id == user_id),
            (UserWeight.recorded_at == current_date_obj)
        ))
        result = await db.execute(query)
        user_weight = result.scalar_one_or_none()

        if user_weight:
            # Сохраняем найденный вес в кэш
            weight_pydantic = UserWeightRead.model_validate(user_weight)
            await cache.set(cache_key, weight_pydantic.model_dump(mode="json"), expire=3600)
            logger.info(f"Current weight cached for user {user_id} on {current_date}")
            return weight_pydantic

        return None
    except Exception as e:
        logger.error(f"Error retrieving current weight for user {user_id} on {current_date}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Функция для получения истории веса пользователя за последние 30 дней.
async def get_weights(db: AsyncSession, user_id: int):
    try:
        # Получаем данные о весе за последние 30 дней
        thirty_days_ago = datetime.today() - timedelta(days=30)
        result = await db.execute(
            select(UserWeight).where(
                UserWeight.user_id == user_id and
                UserWeight.recorded_at >= thirty_days_ago
            ).order_by(UserWeight.recorded_at)
        )
        weight_history = result.scalars().all()

        weight_history_list = [UserWeightRead.model_validate(weight) for weight in weight_history]
        return weight_history_list
    except Exception as e:
        logger.error(f"Error retrieving weight history for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")