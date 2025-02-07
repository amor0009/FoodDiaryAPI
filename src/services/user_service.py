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
    cached_user = await cache.get(cache_key)

    if cached_user:
        logger.info(f"Cache hit for user: {email_login}")
        return UserRead.model_validate(cached_user)

    logger.info(f"Cache miss for user: {email_login}. Fetching from database.")
    query = select(User).where(or_(User.login == email_login, User.email == email_login))
    result = await db.execute(query)  # Вернёт mock_result
    user = result.scalar_one_or_none()  # Вызываем scalar_one_or_none()

    if user:
        # Сериализация пользователя в JSON-совместимый формат для кэша
        user_pydantic = UserRead.model_validate(user)
        await cache.set(cache_key, user_pydantic.model_dump(mode="json"), expire=3600)
        return user_pydantic

    return None


async def delete_user(db: AsyncSession, user: User):
    cache_key = f"user:{user.login}"
    try:
        logger.info(f"Deleting user from database: {user.login}")
        await db.delete(user)
        await db.commit()

        # Удаляем пользователя из кэша
        await cache.delete(cache_key)
        logger.info(f"User deleted from cache: {user.login}")

        return UserRead.model_validate(user)
    except Exception as e:
        logger.error(f"Error deleting user {user.login}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def update_user(user_update: UserUpdate, db: AsyncSession, current_user: User):
    cache_key = f"user:{current_user.login}"
    try:

        query = select(User).where(or_(User.login == current_user.login, User.email == current_user.email))
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        print(user, type(user))
        if not user:
            logger.error(f"User not found in database: {current_user.login}")
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
            await save_or_update_weight(user_weight, db, current_user.id)

        await db.commit()
        await db.refresh(user)

        await cache.delete(cache_key)
        logger.info(f"User deleted from cache: {current_user.login}")

        return UserRead.model_validate(user)
    except Exception as e:
        logger.error(f"Error updating user {current_user.login}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def calculate_recommended_nutrients(user: UserRead):
    """
    Рассчитывает рекомендуемое количество калорий, белков, жиров и углеводов в день
    на основе пола, роста, возраста, веса, цели и уровня активности пользователя.
    """
    cache_key = f"user_nutrients:{user.id}"

    # Проверяем кэш
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info(f"Данные о нутриентах загружены из кэша для пользователя {user.id}")
        return cached_data

    logger.info(f"Расчет нутриентов для пользователя {user.id}")

    if not all([user.weight, user.height, user.age, user.gender, user.aim, user.activity_level]):
        logger.warning(f"Недостаточно данных для расчета нутриентов у пользователя {user.id}")
        raise ValueError("Для расчета необходимо указать вес, рост, возраст, пол, цель и уровень активности.")

    # Расчет BMR
    if user.gender.lower() == "male":
        bmr = 10 * user.weight + 6.25 * user.height - 5 * user.age + 5
    elif user.gender.lower() == "female":
        bmr = 10 * user.weight + 6.25 * user.height - 5 * user.age - 161
    else:
        logger.error(f"Некорректный пол '{user.gender}' у пользователя {user.id}")
        raise ValueError("Некорректное значение пола. Доступны: 'male', 'female'.")

    # Коррекция BMR по уровню активности
    activity_factors = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }

    if user.activity_level.lower() not in activity_factors:
        logger.error(f"Некорректный уровень активности '{user.activity_level}' у пользователя {user.id}")
        raise ValueError("Некорректный уровень активности. Доступны: 'sedentary', 'light', 'moderate', 'active', 'very_active'.")

    daily_calories = bmr * activity_factors[user.activity_level.lower()]

    # Коррекция калорий в зависимости от цели
    aim_factors = {
        "loss": 0.8,     # Похудение (-20%)
        "maintain": 1.0, # Поддержание веса
        "gain": 1.2      # Набор массы (+20%)
    }

    if user.aim.lower() not in aim_factors:
        logger.error(f"Некорректная цель '{user.aim}' у пользователя {user.id}")
        raise ValueError("Некорректная цель. Доступны: 'loss', 'maintain', 'gain'.")

    daily_calories *= aim_factors[user.aim.lower()]
    daily_calories = round(daily_calories, 2)

    # Распределение макронутриентов
    macro_ratios = {
        "loss": {"protein": 0.4, "fat": 0.3, "carbohydrates": 0.3},
        "maintain": {"protein": 0.3, "fat": 0.3, "carbohydrates": 0.4},
        "gain": {"protein": 0.25, "fat": 0.25, "carbohydrates": 0.5}
    }

    macros = macro_ratios[user.aim.lower()]

    protein = round((daily_calories * macros["protein"]) / 4, 2)  # 1 г белка = 4 ккал
    fat = round((daily_calories * macros["fat"]) / 9, 2)          # 1 г жира = 9 ккал
    carbs = round((daily_calories * macros["carbohydrates"]) / 4, 2)      # 1 г углеводов = 4 ккал

    result = {
        "calories": daily_calories,
        "protein": protein,
        "fat": fat,
        "carbohydrates": carbs
    }

    # Запись в кэш на 24 часа
    await cache.set(cache_key, result, expire=86400)
    logger.info(f"Данные о нутриентах закэшированы для пользователя {user.id}")

    return result
