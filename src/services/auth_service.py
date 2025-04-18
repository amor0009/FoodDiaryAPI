from fastapi import HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import config
from src.core.security import Security
from src.logging_config import logger
from src.models.user import User
from src.rabbitmq.producer import publish_message
from src.schemas.user import *
from src.daos.auth_dao import AuthDAO


class AuthService:
    # Аутентификация пользователя
    @classmethod
    async def authenticate_user(cls, db: AsyncSession, email_login: str, password: str):
        try:
            logger.info(f"Fetching user {email_login} from database.")

            # Поиск пользователя в БД через AuthDAO
            user = await AuthDAO.find_by_login_or_email(db, email_login)

            # Проверяем пароль
            if user and Security.verify_password(password, user.hashed_password):
                user_pydantic = UserRead.model_validate(user)
                return user_pydantic

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid login credentials"
            )
        except Exception as e:
            logger.error(f"Error authenticating user {email_login}: {str(e)}")
            raise

    # Проверка, содержит ли поле только английские символы, цифры и допустимые спецсимволы
    @classmethod
    def validate_english_only(cls, field_name: str, value: str):
        if not config.ENGLISH_PATTERN.match(value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} should contain only English letters, numbers, and valid special characters."
            )

    # Создание нового пользователя
    @classmethod
    async def create_user(cls, db: AsyncSession, user: UserCreate):
        try:
            # Проверяем, что логин, email и пароль содержат только английские символы
            cls.validate_english_only("Login", user.login)
            cls.validate_english_only("Email", user.email)
            cls.validate_english_only("Password", user.password)

            # Проверяем существование пользователя по email через AuthDAO
            if await AuthDAO.email_exists(db, user.email):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists."
                )

            # Проверяем существование пользователя по логину через AuthDAO
            if await AuthDAO.login_exists(db, user.login):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this login already exists."
                )

            # Хэшируем пароль и создаем пользователя через AuthDAO
            hashed_password = Security.get_password_hash(user.password)
            new_user = await AuthDAO.create_with_hashed_password(
                db,
                login=user.login,
                email=user.email,
                hashed_password=hashed_password
            )

            # Публикация сообщения в очередь RabbitMQ
            message_data = {
                "email": new_user.email,
                "login": new_user.login,
            }
            await publish_message(message_data, "registration_queue")

            logger.info(f"User created successfully: {new_user.login}")
            return new_user
        except HTTPException as http_exc:
            await db.rollback()
            raise http_exc
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating user {user.login}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    # Деактивация токена (выход из аккаунта)
    @classmethod
    async def logout_user(cls, response: Response):
        response.delete_cookie("fooddiary_access_token")
        logger.info("User logged out successfully")

    # Изменение пароля пользователя
    @classmethod
    async def change_password(
            cls,
            db: AsyncSession,
            user_id: int,
            current_password: str,
            new_password: str
    ) -> User:
        try:
            logger.info(f"Attempting password change for user ID: {user_id}")

            # Получаем пользователя
            user = await AuthDAO.find_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Проверяем текущий пароль
            if not Security.verify_password(current_password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Current password is incorrect"
                )

            # Валидация нового пароля
            cls.validate_english_only("New password", new_password)
            Security.validate_password_strength(new_password)

            # Хэшируем и обновляем пароль через AuthDAO
            new_hashed_password = Security.get_password_hash(new_password)
            updated_user = await AuthDAO.update_password(
                db,
                user_id=user_id,
                new_hashed_password=new_hashed_password
            )

            if not updated_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update password"
                )

            logger.info(f"Password successfully changed for user ID: {user_id}")
            return updated_user

        except HTTPException:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error changing password for user ID {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during password change"
            )
