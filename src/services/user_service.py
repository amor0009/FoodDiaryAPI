import datetime

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.cache import cache
from src.logging_config import logger
from src.models.user import User
from src.schemas.user import UserUpdate, UserRead
from src.schemas.user_weight import UserWeightUpdate
from src.services.user_weight_service import save_or_update_weight


async def find_user_by_login_and_email(db: AsyncSession, email_login: str):
    cache_key = f"user:{email_login}"
    await cache.delete(cache_key)
    cached_user = await cache.get(cache_key)

    if cached_user:
        logger.info(f"Cache hit for user: {email_login}")
        return UserRead.model_validate(cached_user)

    logger.info(f"Cache miss for user: {email_login}. Fetching from database.")
    query = select(User).where(or_(User.login == email_login, User.email == email_login))
    result = await db.execute(query)
    user = result.scalars().first()

    if user:
        # Сериализация пользователя в JSON-совместимый формат для кэша
        user_data = UserRead.model_validate(user).model_dump(mode="json")
        await cache.set(cache_key, user_data, expire=3600)

    return user


async def delete_user(db: AsyncSession, user: User):
    cache_key = f"user:{user.login}"
    try:
        logger.info(f"Deleting user from database: {user.login}")
        await db.delete(user)
        await db.commit()

        # Удаляем пользователя из кэша
        await cache.delete(cache_key)
        logger.info(f"User deleted from cache: {user.login}")

        return user
    except Exception as e:
        logger.error(f"Error deleting user {user.login}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def update_user(user_update: UserUpdate, db: AsyncSession, current_user: User):
    cache_key = f"user:{current_user.login}"
    try:
        user = await find_user_by_login_and_email(db, current_user.login)

        if not user:
            logger.error(f"User not found: {current_user.login}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Обновление данных пользователя
        logger.info(f"Updating user: {current_user.login}")
        if user_update.firstname is not None:
            user.firstname = user_update.firstname
        if user_update.lastname is not None:
            user.lastname = user_update.lastname
        if user_update.age is not None:
            user.age = user_update.age
        if user_update.height is not None:
            user.height = user_update.height
        if user_update.weight is not None:
            user.weight = user_update.weight
        if user_update.gender is not None:
            user.gender = user_update.gender
        if user_update.aim is not None:
            user.aim = user_update.aim
        if user_update.recommended_calories is not None:
            user.recommended_calories = user_update.recommended_calories
        if user_update.profile_image is not None:
            user.profile_image = user_update.profile_image

        # Обновление веса пользователя
        if user.weight:
            user_weight = UserWeightUpdate(
                user_id=user.id,
                weight=user.weight,
            )
            await save_or_update_weight(user_weight, db, current_user)

        await db.commit()
        await db.refresh(user)

        await cache.delete(cache_key)
        logger.info(f"User deleted from cache: {current_user.login}")

        return user
    except Exception as e:
        logger.error(f"Error updating user {current_user.login}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
