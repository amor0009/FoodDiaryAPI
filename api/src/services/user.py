from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status, UploadFile, Response
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.cache.cache import cache
from api.src.core.config import config, Configuration
from api.src.core.security import Security
from api.logging_config import logger
from api.src.exceptions import UserExists, CodeIsNotValidException, PasswordsAreNotTheSameException, \
    WrongOldPasswordException
from api.src.models.user import User, AimEnum, ActivityLevelEnum, GenderEnum
from api.src.repositories.objects.base import BaseObjectRepository
from api.src.schemas.user import UserUpdate, UserRead, UserCalculateNutrients, CheckRegistrationUser, CreateUser, \
    EmailChangeConfirm, StartForgotPassword, CheckForgotPassword, UpdateForgotPassword, UpdatePassword
from api.src.schemas.user_weight import UserWeightCreate
from api.src.repositories.user.base import BaseUserRepository
from api.src.repositories.user_weight.base import BaseUserWeightRepository
from api.src.services.converters.user import convert_user_model_to_schema
from api.src.fone_tasks.verification import verify_code, create_6_digits, get_code_data, delete_code
from api.src.fone_tasks.task import send_code
from api.src.services.user_weight import UserWeightService


@dataclass(slots=True)
class UserService:
    _user_repository: BaseUserRepository
    _user_weight_repository: BaseUserWeightRepository
    _user_weight_service: UserWeightService
    _object_repository: BaseObjectRepository

    async def authenticate_user(self, session: AsyncSession, email_login: str, password: str) -> UserRead:
        try:
            logger.info(f"Fetching user {email_login} from database.")

            user = await self._user_repository.find_by_login_or_email(session, email_login)

            if user and Security.verify_password(password, user.hashed_password):
                return convert_user_model_to_schema(user)

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid login credentials"
            )
        except Exception as e:
            logger.error(f"Error authenticating user {email_login}: {str(e)}")
            raise

    async def get_user_by_email(self, session: AsyncSession, email: str) -> User | None:
        return await self._user_repository.find_by_email(session, email)

    def validate_english_only(self, field_name: str, value: str):
        if not config.ENGLISH_PATTERN.match(value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} should contain only English letters, numbers, and valid special characters."
            )

    async def check_registration_code(self, user_data: CheckRegistrationUser, code: str) -> None:
        if not await verify_code("register", code, user_data.email):
            if not config.DEBUG:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный или просроченный код подтверждения"
                )
            else:
                logger.info(f"DEBUG MODE: Skipping code verification for {user_data.email}")

    async def start_register_user(self, session: AsyncSession, email: str) -> None:
        normalized_email = email.strip().lower()

        existing_user = await self._user_repository.find_by_email(session, normalized_email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким email уже существует"
            )

        code = await create_6_digits("register", normalized_email, expired_at=1800)

        send_code.delay(
            code=code,
            send_type="email",
            recipient=normalized_email,
        )
        logger.info(f"Registration process started for {normalized_email}")

    async def create_user(self, session: AsyncSession, user_data: CreateUser) -> UserRead:
        try:
            self.validate_english_only("Login", user_data.login)
            self.validate_english_only("Email", user_data.email)
            self.validate_english_only("Password", user_data.password)

            if await self._user_repository.email_exists(session, user_data.email):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists."
                )

            hashed_password = Security.get_password_hash(user_data.password)
            user = await self._user_repository.create_user(
                session,
                login=user_data.login,
                email=user_data.email,
                hashed_password=hashed_password
            )
            await session.commit()
            return convert_user_model_to_schema(user)

        except HTTPException as http_exc:
            await session.rollback()
            raise http_exc
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating user {user_data.login}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def logout_user(self, response: Response):
        response.delete_cookie("fooddiary_access_token")
        logger.info("User logged out successfully")

    async def change_password(
            self,
            session: AsyncSession,
            user_id: int,
            current_password: str,
            new_password: str
    ) -> User:
        try:
            logger.info(f"Attempting password change for user ID: {user_id}")

            user = await self._user_repository.get_by_id(session, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            if not Security.verify_password(current_password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Current password is incorrect"
                )

            self.validate_english_only("New password", new_password)
            Security.validate_password_strength(new_password)

            new_hashed_password = Security.get_password_hash(new_password)
            updated_user = await self._user_repository.update_password(
                session,
                user_id=user_id,
                new_hashed_password=new_hashed_password
            )

            if not updated_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update password"
                )

            await session.commit()
            logger.info(f"Password successfully changed for user ID: {user_id}")
            return updated_user

        except HTTPException:
            await session.rollback()
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Error changing password for user ID {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during password change"
            )

    async def find_user_by_login_and_email(self, session: AsyncSession, email_login: str) -> UserRead | None:
        cache_key = f"user:{email_login}"
        try:
            cached_user = await cache.get(cache_key)
            if cached_user:
                logger.info(f"Cache hit for user: {email_login}")
                return UserRead.model_validate(cached_user)
            logger.info(f"Cache miss for user: {email_login}. Fetching from database.")
            user = await self._user_repository.find_by_login_or_email(session, email_login)

            if user:
                user_schema = convert_user_model_to_schema(user)
                await cache.set(cache_key, user_schema.model_dump(mode="json"), expire=3600)
                logger.info(f"User {email_login} fetched from DB and cached")
                return user_schema

            logger.warning(f"User {email_login} not found in database")
            return None
        except Exception as e:
            logger.error(f"Error finding user by login or email ({email_login}): {str(e)}")
            return None

    async def delete_user(self, session: AsyncSession, user: User) -> UserRead:
        cache_key = f"user:{user.login}"
        try:
            logger.info(f"Deleting user from database: {user.login}")
            await self._user_repository.delete(session, user.id)
            await session.commit()

            await cache.delete(cache_key)
            logger.info(f"User deleted from cache: {user.login}")

            return convert_user_model_to_schema(user)
        except Exception as e:
            logger.error(f"Error deleting user {user.login}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def update_user(self, session: AsyncSession, user_update: UserUpdate, current_user: User) -> UserRead:
        cache_key = f"user:{current_user.login}"
        try:
            user = await self._user_repository.get_by_id(session, current_user.id)
            if not user:
                logger.error(f"User not found in database: {current_user.login}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            update_data = user_update.model_dump(exclude_unset=True)

            updated_user = await self._user_repository.update_user(session, user, update_data)

            if user_update.weight:
                user_weight = UserWeightCreate(
                    user_id=user.id,
                    weight=user_update.weight,
                )
                await self._user_weight_service.create_or_update(session, current_user.id, user_weight)
                logger.info(f"User weight updated for user {current_user.login}")

            if all([user.weight, user.height, user.age, user.gender, user.aim, user.activity_level]):
                result = await self.calculate_nutrients(session, UserCalculateNutrients.model_validate(user), current_user)
                user.recommended_calories = result["calories"]
                await self._user_repository.update_user(session, user, {"recommended_calories": result["calories"]})
                logger.warning(f"Расчет нутриентов у пользователя: {user.id} - прошёл успешно")
            else:
                logger.warning(f"Недостаточно данных для расчета нутриентов у пользователя {user.id}")

            await cache.delete(cache_key)
            logger.info(f"User {current_user.login} deleted from cache")

            return convert_user_model_to_schema(updated_user)
        except Exception as e:
            logger.error(f"Error updating user {current_user.login}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def calculate_nutrients_basic(self, user: UserCalculateNutrients,
                                        current_user: Optional[User] = None) -> dict:
        logger.info(
            f"Calculating basic nutrients for user {'anonymous' if not current_user else f'ID {current_user.id}'}")

        if not all([user.weight, user.height, user.age, user.gender, user.aim, user.activity_level]):
            logger.warning("Insufficient data for calculation")
            raise ValueError("Weight, height, age, gender, goal and activity level are required for calculation.")

        if user.gender == GenderEnum.MALE:
            bmr = 10 * user.weight + 6.25 * user.height - 5 * user.age + 5
        elif user.gender == GenderEnum.FEMALE:
            bmr = 10 * user.weight + 6.25 * user.height - 5 * user.age - 161
        else:
            logger.error(f"Invalid gender value '{user.gender}'")
            raise ValueError("Invalid gender value.")

        activity_factors = {
            ActivityLevelEnum.SEDENTARY: 1.2,
            ActivityLevelEnum.LIGHT: 1.375,
            ActivityLevelEnum.MODERATE: 1.55,
            ActivityLevelEnum.ACTIVE: 1.725,
            ActivityLevelEnum.VERY_ACTIVE: 1.9
        }

        if user.activity_level not in activity_factors:
            logger.error(f"Invalid activity level '{user.activity_level}'")
            raise ValueError("Invalid activity level.")

        daily_calories = bmr * activity_factors[user.activity_level]

        aim_factors = {
            AimEnum.LOSS: 0.8,
            AimEnum.MAINTAIN: 1.0,
            AimEnum.GAIN: 1.2
        }

        if user.aim not in aim_factors:
            logger.error(f"Invalid goal '{user.aim}'")
            raise ValueError("Invalid goal.")

        daily_calories *= aim_factors[user.aim]
        daily_calories = round(daily_calories, 2)

        macro_ratios = {
            AimEnum.LOSS: {"protein": 0.4, "fat": 0.3, "carbohydrates": 0.3},
            AimEnum.MAINTAIN: {"protein": 0.3, "fat": 0.3, "carbohydrates": 0.4},
            AimEnum.GAIN: {"protein": 0.25, "fat": 0.25, "carbohydrates": 0.5}
        }

        macros = macro_ratios[user.aim]
        protein = round((daily_calories * macros["protein"]) / 4, 2)
        fat = round((daily_calories * macros["fat"]) / 9, 2)
        carbs = round((daily_calories * macros["carbohydrates"]) / 4, 2)

        result = {
            "calories": daily_calories,
            "proteins": protein,
            "fats": fat,
            "carbohydrates": carbs
        }

        logger.info(
            f"Basic nutrients calculation completed for user {'anonymous' if not current_user else f'ID {current_user.id}'}")
        return result

    async def calculate_nutrients(
        self,
        session: AsyncSession,
        user: UserCalculateNutrients,
        current_user: User,
        target_weight: float | None = None,
        target_days: int | None = None,
    ) -> dict:
        if not current_user:
            logger.warning(f"Premium feature access attempt by user with id: {current_user.id}.")
            raise PermissionError("Available only for users with premium subscription")

        logger.info(f"Starting premium nutrients calculation for user ID {current_user.id}")

        basic_result = await self.calculate_nutrients_basic(user, current_user)

        height_m = user.height / 100
        bmi = round(user.weight / (height_m ** 2), 2)
        min_normal_weight = round(18.5 * (height_m ** 2), 2)
        max_normal_weight = round(24.9 * (height_m ** 2), 2)

        weight_change_info = {}
        adjusted_calories = basic_result["calories"]

        if target_weight and target_days:
            weight_diff = target_weight - user.weight
            weekly_weight_change = weight_diff / (target_days / 7)

            weekly_goal = min(max(abs(weekly_weight_change), 0.1), 1.0)
            weekly_goal *= 1 if weight_diff > 0 else -1

            calorie_adjustment = (weekly_goal * 7700) / 7
            adjusted_calories = round(basic_result["calories"] + calorie_adjustment, 2)

            weight_change_info = {
                "target_weight": target_weight,
                "weekly_goal": round(weekly_goal, 2),
                "estimated_weeks": round(abs(weight_diff) / abs(weekly_goal)),
                "daily_calorie_adjustment": round(calorie_adjustment, 2)
            }

        macro_ratios = {
            AimEnum.LOSS: {"protein": 0.4, "fat": 0.3, "carbohydrates": 0.3},
            AimEnum.MAINTAIN: {"protein": 0.3, "fat": 0.3, "carbohydrates": 0.4},
            AimEnum.GAIN: {"protein": 0.25, "fat": 0.25, "carbohydrates": 0.5}
        }

        macros = macro_ratios[user.aim]
        protein = round((adjusted_calories * macros["protein"]) / 4, 2)
        fat = round((adjusted_calories * macros["fat"]) / 9, 2)
        carbs = round((adjusted_calories * macros["carbohydrates"]) / 4, 2)

        premium_result = {
            "calories": adjusted_calories,
            "proteins": protein,
            "fats": fat,
            "carbohydrates": carbs,
            "bmi": bmi,
            "bmi_interpretation": self.get_bmi_interpretation(bmi),
            "recommended_weight_range": {
                "min": min_normal_weight,
                "max": max_normal_weight
            },
            "weight_plan": weight_change_info or None
        }

        current_user.recommended_calories = adjusted_calories
        await self._user_repository.update_user(session, current_user,
                                                {"recommended_calories": adjusted_calories})
        logger.info(f"Premium nutrients calculation completed for user ID {current_user.id}")
        return premium_result

    def get_bmi_interpretation(self, bmi: float) -> str:
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

    async def upload_avatar(self, session: AsyncSession, file: UploadFile, current_user: User) -> dict:
        logger.info(f"Uploading avatar for user {current_user.id}")

        if not file.content_type or not file.content_type.startswith('image/'):
            logger.error(f"Invalid file type: {file.content_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image files are allowed"
            )

        try:
            filename = await self._object_repository.add(file)

            if current_user.avatar:
                await self._object_repository.delete(current_user.avatar)

            current_user.avatar = filename
            await self._user_repository.update_user(session, current_user, {"avatar": filename})

            logger.info(f"Avatar uploaded successfully for user {current_user.id}")

            return {
                "message": "Avatar uploaded successfully",
                "avatar_url": filename
            }

        except Exception as e:
            logger.error(f"Error uploading avatar for user {current_user.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload avatar"
            )

    async def get_avatar(self, current_user: User) -> dict:
        logger.info(f"Getting avatar for user {current_user.id}")

        if not current_user.avatar:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avatar not found"
            )

        return {
            "avatar_url": current_user.avatar,
            "has_avatar": True
        }

    async def check_user_not_exists_by_email(
        self, session: AsyncSession, email: str
    ) -> None:
        user = await self._user_repository.email_exists(session, email)
        if user:
            raise UserExists

    async def start_email_change(self, session: AsyncSession, email: str) -> None:
        await self.check_user_not_exists_by_email(session, email)
        send_code.delay(
            await create_6_digits("change_email", email, expired_at=1800),
            "email",
            email,
            "/email_notifications/email_change.html",
            "Смена email адреса"
        )

    async def final_email_change(self, session: AsyncSession, response: Response, user_id: UUID, user_data: EmailChangeConfirm) -> UserRead:
        code_data = await get_code_data("change email", user_data.code)
        if code_data != user_data.email:
            raise CodeIsNotValidException

        user = await self._user_repository.update_email(session, user_id, user_data.email)

        await session.commit()
        await session.refresh(user)

        await delete_code("change email", user_data.code)

        await self.logout_user(response)
        access_token = Security.create_access_token(data={"sub": user.login},
                                                    secret_key=Configuration.USER_SECRET_AUTH)
        logger.info(f"User {user.login} successfully logged in")
        response.set_cookie("fooddiary_access_token", access_token, httponly=True)

        return convert_user_model_to_schema(user)

    async def forgot_my_password(self, email: str) -> None:
        send_code.delay(
            await create_6_digits("change_password", email, expired_at=1800),
            "email",
            email,
            "/email_notifications/password_reset.html",
            "Сброс пароля"
        )

    async def forgot_my_password_check(
        self, user_data: CheckForgotPassword, current_user: User
    ) -> str:
        code_data = await get_code_data("change_password", user_data.code)

        if code_data != current_user.email:
            raise CodeIsNotValidException

        return "OK"

    async def forgot_my_password_final(
        self,
        response: Response,
        user_data: UpdateForgotPassword,
        current_user: User,
        session: AsyncSession
    ) -> UserRead:
        code_data = await get_code_data("change_password", user_data.code)

        if code_data != current_user.email:
            raise CodeIsNotValidException

        if user_data.new_password != user_data.password_confirm:
            raise PasswordsAreNotTheSameException

        existed_user = await self.get_user_by_email(session, current_user.email)

        await delete_code("change_password", user_data.code)

        hashed_password = Security.get_password_hash(user_data.new_password)
        updated_user = await self._user_repository.update_password(
            session, existed_user.id, hashed_password
        )
        await session.commit()
        await self.logout_user(response)
        return convert_user_model_to_schema(updated_user)

    async def update_password(
        self,
        session: AsyncSession,
        response: Response,
        passwords: UpdatePassword,
        current_user: User
    ) -> None:
        if passwords.new_password != passwords.password_confirm:
            raise PasswordsAreNotTheSameException

        user_with_password = await self._user_repository.get_by_id(session, current_user.id)
        if not Security.verify_password(passwords.old_password, user_with_password.hashed_password):
            raise WrongOldPasswordException

        hashed_password = Security.get_password_hash(passwords.new_password)
        await self._user_repository.update_password(
            session, current_user.id, hashed_password
        )
        await session.commit()

        await self.logout_user(response)
