from typing import Optional
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from src.cache.cache import cache
from src.core.config import config
from src.logging_config import logger
from src.models.user import User
from src.schemas.user import UserUpdate, UserRead, UserCalculateNutrients
from src.schemas.user_weight import UserWeightUpdate
from src.services.user_weight_service import UserWeightService
from src.daos.user_dao import UserDAO


class UserService:

    # Функция для поиска пользователя по логину или email
    @classmethod
    async def find_user_by_login_and_email(cls, db: AsyncSession, email_login: str):
        cache_key = f"user:{email_login}"
        try:
            # Проверяем наличие пользователя в кэше
            cached_user = await cache.get(cache_key)
            if cached_user:
                logger.info(f"Cache hit for user: {email_login}")
                return UserRead.model_validate(cached_user)

            # Если в кэше нет, делаем запрос в БД
            logger.info(f"Cache miss for user: {email_login}. Fetching from database.")
            user = await UserDAO.find_by_login_or_email(db, email_login)

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
    @classmethod
    async def delete_user(cls, db: AsyncSession, user: User):
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
    @classmethod
    async def update_user(cls, user_update: UserUpdate, db: AsyncSession, current_user: User):
        cache_key = f"user:{current_user.login}"
        try:
            # Получаем пользователя из БД
            user = await UserDAO.find_by_login_or_email(db, current_user.login)
            if not user:
                logger.error(f"User not found in database: {current_user.login}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Подготавливаем данные для обновления
            update_data = user_update.model_dump(exclude_unset=True)

            # Обновляем данные пользователя
            logger.info(f"Updating user: {current_user.login}")
            updated_user = await UserDAO.update_user(db, user, update_data)

            # Обновление веса пользователя
            if user_update.weight:
                user_weight = UserWeightUpdate(
                    user_id=user.id,
                    weight=user_update.weight,
                )
                await UserWeightService.save_or_update_weight(user_weight, db, current_user.id)
                logger.info(f"User weight updated for user {current_user.login}")

            # Расчет нутриентов
            if all([user.weight, user.height, user.age, user.gender, user.aim, user.activity_level]):
                result = await cls.calculate_nutrients(UserCalculateNutrients.model_validate(user), current_user)
                user.recommended_calories = result["calories"]
                logger.warning(f"Расчет нутриентов у пользователя: {user.id} - прошёл успешно")
            else:
                logger.warning(f"Недостаточно данных для расчета нутриентов у пользователя {user.id}")

            # Удаляем пользователя из кэша
            await cache.delete(cache_key)
            logger.info(f"User {current_user.login} deleted from cache")

            return UserRead.model_validate(updated_user)
        except Exception as e:
            logger.error(f"Error updating user {current_user.login}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # Базовый расчёт нутриентов (доступен всем пользователям)
    @classmethod
    async def calculate_nutrients_basic(cls, user: UserCalculateNutrients, current_user: Optional[User] = None):
        logger.info(
            f"Calculating basic nutrients for user {'anonymous' if not current_user.id else f'ID {current_user.id}'}")

        # Проверка обязательных полей
        if not all([user.weight, user.height, user.age, user.gender, user.aim, user.activity_level]):
            logger.warning("Insufficient data for calculation")
            raise ValueError("Для расчета необходимо указать вес, рост, возраст, пол, цель и уровень активности.")

        # Расчёт базового метаболизма (BMR)
        if user.gender.lower() == "male":
            bmr = 10 * user.weight + 6.25 * user.height - 5 * user.age + 5
        elif user.gender.lower() == "female":
            bmr = 10 * user.weight + 6.25 * user.height - 5 * user.age - 161
        else:
            logger.error(f"Invalid gender value '{user.gender}'")
            raise ValueError("Некорректное значение пола. Доступны: 'male', 'female'.")

        # Коэффициенты активности
        activity_factors = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "active": 1.725,
            "very_active": 1.9
        }

        if user.activity_level.lower() not in activity_factors:
            logger.error(f"Invalid activity level '{user.activity_level}'")
            raise ValueError(
                "Некорректный уровень активности. Доступны: 'sedentary', 'light', 'moderate', 'active', 'very_active'.")

        daily_calories = bmr * activity_factors[user.activity_level.lower()]

        # Коррекция по цели
        aim_factors = {
            "loss": 0.8,  # Похудение (-20%)
            "maintain": 1.0,  # Поддержание веса
            "gain": 1.2  # Набор массы (+20%)
        }

        if user.aim.lower() not in aim_factors:
            logger.error(f"Invalid goal '{user.aim}'")
            raise ValueError("Некорректная цель. Доступны: 'loss', 'maintain', 'gain'.")

        daily_calories *= aim_factors[user.aim.lower()]
        daily_calories = round(daily_calories, 2)

        # Расчёт макронутриентов
        macro_ratios = {
            "loss": {"protein": 0.4, "fat": 0.3, "carbohydrates": 0.3},
            "maintain": {"protein": 0.3, "fat": 0.3, "carbohydrates": 0.4},
            "gain": {"protein": 0.25, "fat": 0.25, "carbohydrates": 0.5}
        }

        macros = macro_ratios[user.aim.lower()]
        protein = round((daily_calories * macros["protein"]) / 4, 2)  # 1 г белка = 4 ккал
        fat = round((daily_calories * macros["fat"]) / 9, 2)  # 1 г жира = 9 ккал
        carbs = round((daily_calories * macros["carbohydrates"]) / 4, 2)  # 1 г углеводов = 4 ккал

        result = {
            "calories": daily_calories,
            "proteins": protein,
            "fats": fat,
            "carbohydrates": carbs
        }

        logger.info(
            f"Basic nutrients calculation completed for user {'anonymous' if not current_user.id else f'ID {current_user.id}'}")
        return result

    # Премиум расчёт нутриентов (только для аутентифицированных пользователей с подпиской)
    @classmethod
    async def calculate_nutrients(cls, user: UserCalculateNutrients, current_user: User):
        if not current_user:
            logger.warning(
                f"Premium feature access attempt by user with id: {current_user.id}.")
            raise PermissionError("Доступно только для пользователей с премиум подпиской")

        logger.info(f"Starting premium nutrients calculation for user ID {current_user.id}")

        # Базовый расчёт
        basic_result = await cls.calculate_nutrients_basic(user, current_user)

        # Дополнительные премиум-расчёты
        height_m = user.height / 100
        bmi = round(user.weight / (height_m ** 2), 2)
        min_normal_weight = round(18.5 * (height_m ** 2), 2)
        max_normal_weight = round(24.9 * (height_m ** 2), 2)

        weight_change_info = {}
        if user.target_weight and user.target_days:
            weight_diff = user.target_weight - user.weight
            weekly_goal = min(max(abs(weight_diff / user.target_days * 7), 1), 0.5)
            weekly_goal *= 1 if weight_diff > 0 else -1
            calorie_adjustment = (weekly_goal * 7700) / 7
            basic_result["calories"] = round(basic_result["calories"] + calorie_adjustment, 2)

            weight_change_info = {
                "target_weight": user.target_weight,
                "weekly_goal": round(weekly_goal, 2),
                "estimated_weeks": round(abs(weight_diff) / abs(weekly_goal)),
                "daily_calorie_adjustment": round(calorie_adjustment, 2)
            }

        premium_result = {
            **basic_result,
            "bmi": bmi,
            "bmi_interpretation": cls.get_bmi_interpretation(bmi),
            "recommended_weight_range": {
                "min": min_normal_weight,
                "max": max_normal_weight
            },
            "weight_plan": weight_change_info or None
        }

        logger.info(f"Premium nutrients calculation completed for user ID {current_user.id}")
        return premium_result

    # Интерпретация показателей ИМТ
    @classmethod
    def get_bmi_interpretation(cls, bmi: float) -> str:
        if bmi < 16:
            return "Severe underweight"
        elif bmi < 18.5:
            return "Underweight"
        elif bmi < 25:
            return "Normal weight"
        elif bmi < 30:
            return "Overweight"
        elif bmi < 35:
            return "Obesity class I"
        elif bmi < 40:
            return "Obesity class II"
        return "Obesity class III"

    # Функция для загрузки фотографии профиля пользователя
    @classmethod
    async def upload_profile_picture(cls, file: UploadFile, current_user: User, db: AsyncSession):
        if file.content_type not in config.ALLOWED_IMAGE_TYPES:
            logger.warning(f"Attempted to upload an unsupported image type: {file.content_type}")
            raise HTTPException(status_code=400, detail="Only images (JPEG, PNG, GIF) are allowed")

        user = await db.get(User, current_user.id)
        if not user:
            logger.error(f"User with ID {current_user.id} not found")
            raise HTTPException(status_code=404, detail="User not found")

        # Обновление фотографии профиля пользователя
        user = await UserDAO.update_profile_picture(db, user, await file.read())
        logger.info(f"Profile picture updated for user {current_user.id}")

        # Очистка кэша
        cache_key1 = f"user:{user.login}"
        cache_key2 = f"user:{user.email}"
        await cache.delete(cache_key1)
        await cache.delete(cache_key2)
        logger.info(f"Cache cleared for user {current_user.id} (keys: {cache_key1}, {cache_key2})")

        return {"message": "Profile picture updated"}

    # Функция для получения фотографии профиля пользователя
    @classmethod
    async def get_profile_picture(cls, current_user: User, db: AsyncSession):
        user = await db.get(User, current_user.id)
        if not user or not user.profile_picture:
            logger.warning(f"Profile picture not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="No profile picture found")

        logger.info(f"Profile picture retrieved for user {current_user.id}")
        return user.profile_picture
