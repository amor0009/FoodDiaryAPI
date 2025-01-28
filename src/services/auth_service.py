from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.cache.cache import cache
from src.core.security import verify_password, get_password_hash
from src.logging_config import logger
from src.models.user import User
from src.rabbitmq.producer import publish_message
from src.schemas.user import *
from src.services.user_service import find_user_by_login_and_email


# Аутентификация пользователя
async def authenticate_user(db: AsyncSession, email_login: str, password: str):
    cache_key = f"user_auth:{email_login}"
    try:
        # Проверка кэша
        cached_user = await cache.get(cache_key)
        if cached_user:
            logger.info(f"Cache hit for user authentication: {email_login}")
            # Возвращаем объект UserRead, используя данные из кэша
            return cached_user

        logger.info(f"Cache miss for user authentication: {email_login}. Fetching from database.")
        user = await find_user_by_login_and_email(db, email_login)

        # Проверка пароля
        if user and verify_password(password, user.hashed_password):
            # Преобразование пользователя в Pydantic-модель и сериализация для кэша
            user_pydantic = UserRead.model_validate(user).model_dump(mode="json")
            await cache.set(cache_key, user_pydantic)  # Сохранение в кэш
            return UserRead.model_validate(user_pydantic)  # Возвращаем объект UserRead

        return None
    except Exception as e:
        logger.error(f"Error authenticating user {email_login}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Создание нового пользователя
async def create_user(db: AsyncSession, user: UserCreate):
    try:
        # Проверяем существование пользователя по логину
        existing_login_user = await find_user_by_login_and_email(db, user.login)
        if existing_login_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with login '{user.login}' already exists."
            )

        # Проверяем существование пользователя по email
        existing_email_user = await find_user_by_login_and_email(db, user.email)
        if existing_email_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email '{user.email}' already exists."
            )

        # Хэшируем пароль и создаем пользователя
        hashed_password = get_password_hash(user.password)
        new_user = User(
            login=user.login,
            email=user.email,
            hashed_password=hashed_password,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # Публикация сообщения в очередь RabbitMQ
        message_data = {
            "email": new_user.email,
            "login": new_user.login,
        }
        await publish_message(message_data, "registration_queue")

        logger.info(f"User created successfully: {new_user.login}")
        return new_user
    except Exception as e:
        logger.error(f"Error creating user {user.login}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Проверка токена
async def validate_token_logic(user):
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"message": "Token is valid", "user_id": user.id, "username": user.login}
