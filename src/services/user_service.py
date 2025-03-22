from fastapi import HTTPException, status, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.cache.cache import cache
from src.logging_config import logger
from src.models.user import User
from src.schemas.user import UserUpdate, UserRead, UserCalculateNutrients
from src.schemas.user_weight import UserWeightUpdate
from src.services.user_weight_service import save_or_update_weight

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif"}

# Функция для поиска пользователя по логину или email
async def find_user_by_login_and_email(db: AsyncSession, email_login: str):
    cache_key = f"user:{email_login}"
    try:
        # Проверяем наличие пользователя в кэше
        cached_user = await cache.get(cache_key)
        if cached_user:
            logger.info(f"Cache hit for user: {email_login}")
            return UserRead.model_validate(cached_user)

        # Если в кэше нет, делаем запрос в БД
        logger.info(f"Cache miss for user: {email_login}. Fetching from database.")
        query = select(User).where(or_(User.login == email_login, User.email == email_login))
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if user:
            user_pydantic = UserRead.model_validate(user)
            await cache.set(cache_key, user_pydantic.model_dump(mode="json"), expire=3600)
            logger.info(f"User {email_login} fetched from DB and cached")
            return user_pydantic

        logger.warning(f"User {email_login} not found in database")
        return None
    except Exception as e:
        logger.error(f"Error finding user by login or email ({email_login}): {str(e)}")
        return None

# Функция для удаления пользователя
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

# Функция для обновления данных пользователя
async def update_user(user_update: UserUpdate, db: AsyncSession, current_user: User):
    cache_key = f"user:{current_user.login}"
    try:
        query = select(User).where(or_(User.login == current_user.login, User.email == current_user.email))
        result = await db.execute(query)
        user = result.scalar_one_or_none()

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
        if user_update.activity_level is not None:
            user.activity_level = user_update.activity_level

        # Обновление веса пользователя
        if user.weight:
            user_weight = UserWeightUpdate(
                user_id=user.id,
                weight=user.weight,
            )
            await save_or_update_weight(user_weight, db, current_user.id)
            logger.info(f"User weight updated for user {current_user.login}")

        if all([user.weight, user.height, user.age, user.gender, user.aim, user.activity_level]):
            result = await calculate_recommended_nutrients(UserCalculateNutrients.model_validate(user))
            user.recommended_calories = result["calories"]
            logger.warning(f"Расчет нутриентов у пользователя: {user.id} - прошёл успешно")
        else:
            logger.warning(f"Недостаточно данных для расчета нутриентов у пользователя {user.id}")

        await db.commit()
        await db.refresh(user)

        # Удаляем пользователя из кэша
        await cache.delete(cache_key)
        logger.info(f"User {current_user.login} deleted from cache")

        return UserRead.model_validate(user)
    except Exception as e:
        logger.error(f"Error updating user {current_user.login}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Функция для расчета рекомендуемых нутриентов для пользователя
async def calculate_recommended_nutrients(user: UserCalculateNutrients):
    """
    Рассчитывает рекомендуемое количество калорий, белков, жиров и углеводов в день
    на основе пола, роста, возраста, веса, цели и уровня активности пользователя.
    """
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

    logger.info(f"Calculated recommended nutrients for user {user.id}: {result}")
    return result

# Функция для загрузки фотографии профиля пользователя
async def upload_profile_picture(file: UploadFile, current_user: User, db: AsyncSession):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        logger.warning(f"Attempted to upload an unsupported image type: {file.content_type}")
        raise HTTPException(status_code=400, detail="Only images (JPEG, PNG, GIF) are allowed")

    user = await db.get(User, current_user.id)
    if not user:
        logger.error(f"User with ID {current_user.id} not found")
        raise HTTPException(status_code=404, detail="User not found")

    # Обновление фотографии профиля пользователя
    user.profile_picture = await file.read()
    await db.commit()
    await db.refresh(user)
    logger.info(f"Profile picture updated for user {current_user.id}")

    # Очистка кэша
    cache_key1 = f"user:{user.login}"
    cache_key2 = f"user:{user.email}"
    await cache.delete(cache_key1)
    await cache.delete(cache_key2)
    logger.info(f"Cache cleared for user {current_user.id} (keys: {cache_key1}, {cache_key2})")

    return {"message": "Profile picture updated"}

# Функция для получения фотографии профиля пользователя
async def get_profile_picture(current_user: User, db: AsyncSession):
    user = await db.get(User, current_user.id)
    if not user or not user.profile_picture:
        logger.warning(f"Profile picture not found for user {current_user.id}")
        raise HTTPException(status_code=404, detail="No profile picture found")

    logger.info(f"Profile picture retrieved for user {current_user.id}")
    return user.profile_picture