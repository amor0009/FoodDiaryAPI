from datetime import datetime, timedelta, date
from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.cache.cache import cache
from src.logging_config import logger
from src.models.user_weight import UserWeight
from src.schemas.user_weight import UserWeightUpdate, UserWeightRead


async def save_or_update_weight(user_weight: UserWeightUpdate, db: AsyncSession, user_id: int):
    cache_key = f"user_weight:{user_id}:{date.today()}"
    try:
        current_date = date.today()
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
            # Иначе создаем новую запись
            logger.info(f"Creating new weight record for user {user_id}")
            user_weight_db = UserWeight(
                user_id=user_id,
                weight=user_weight.weight,
                recorded_at=current_date  # Добавляем дату для новой записи
            )
            db.add(user_weight_db)

        await db.commit()
        await cache.delete(cache_key)
        logger.info(f"Weight deleted from cache for user {user_id} on {current_date}")

        return UserWeightRead.model_validate(user_weight_db)
    except Exception as e:
        logger.error(f"Error saving or updating weight for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_current_weight(current_date: str, db: AsyncSession, user_id: int):
    cache_key = f"user_weight:{user_id}:{current_date}"
    try:
        cached_weight = await cache.get(cache_key)
        if cached_weight:
            logger.info(f"Cache hit for current weight of user {user_id} on {current_date}")
            return UserWeightRead.model_validate(cached_weight)

        logger.info(f"Cache miss for current weight of user {user_id} on {current_date}")
        current_date_obj = datetime.strptime(current_date, '%Y-%m-%d').date()
        query = select(UserWeight).where(and_(
            (UserWeight.user_id == user_id),
            (UserWeight.recorded_at == current_date_obj)
        ))
        result = await db.execute(query)
        user_weight = result.scalar_one_or_none()

        # Сохраняем в кэш, если запись найдена
        if user_weight:
            weight_pydantic = UserWeightRead.model_validate(user_weight)
            await cache.set(cache_key, weight_pydantic.model_dump(mode="json"), expire=3600)
            logger.info(f"Current weight cached for user {user_id} on {current_date}")
            return weight_pydantic

        return None
    except Exception as e:
        logger.error(f"Error retrieving current weight for user {user_id} on {current_date}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_weights(db: AsyncSession, user_id: int):
    cache_key = f"user_weights:{user_id}:last_30_days"
    try:
        cached_weights = await cache.get(cache_key)
        if cached_weights:
            logger.info(f"Cache hit for weight history of user {user_id}")
            return [UserWeightRead.model_validate(weight) for weight in cached_weights]

        logger.info(f"Cache miss for weight history of user {user_id}")
        thirty_days_ago = datetime.today() - timedelta(days=30)
        result = await db.execute(
            select(UserWeight).where(
                UserWeight.user_id == user_id and
                UserWeight.recorded_at >= thirty_days_ago
            ).order_by(UserWeight.recorded_at)
        )
        weight_history = result.scalars().all()
        weight_history_list = [UserWeightRead.model_validate(weight) for weight in weight_history]
        await cache.set(cache_key, [weight.model_dump(mode="json") for weight in weight_history_list], expire=3600)
        logger.info(f"Weight history cached for user {user_id}")

        return weight_history_list
    except Exception as e:
        logger.error(f"Error retrieving weight history for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
