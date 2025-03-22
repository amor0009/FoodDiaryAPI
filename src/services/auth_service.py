from datetime import datetime
import jwt
import re
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.cache.cache import cache
from src.core.config import SECRET_AUTH, ALGORITHM
from src.core.security import verify_password, get_password_hash, add_token_to_blacklist
from src.logging_config import logger
from src.models.user import User
from src.rabbitmq.producer import publish_message
from src.schemas.user import *
from src.services.user_service import find_user_by_login_and_email

# Регулярное выражение для проверки только английских символов
ENGLISH_PATTERN = re.compile(r'^[a-zA-Z0-9@._-]+$')

# Проверка, содержит ли поле только английские символы, цифры и допустимые спецсимволы
def validate_english_only(field_name: str, value: str):
    if not ENGLISH_PATTERN.match(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} should contain only English letters, numbers, and valid special characters."
        )

# Аутентификация пользователя
async def authenticate_user(db: AsyncSession, email_login: str, password: str):
    cache_key = f"user_auth:{email_login}"
    try:
        # Проверяем кэш
        cached_user = await cache.get(cache_key)
        if cached_user:
            logger.info(f"Cache hit for user authentication: {email_login}")
            return UserRead.model_validate(cached_user)

        logger.info(f"Cache miss for user authentication: {email_login}. Fetching from database.")

        # Поиск пользователя в БД
        query = select(User).where(or_(User.login == email_login, User.email == email_login))
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        # Проверяем пароль
        if user and verify_password(password, user.hashed_password):
            user_pydantic = UserRead.model_validate(user)
            await cache.set(cache_key, user_pydantic.model_dump(mode="json"))
            return user_pydantic

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login credentials"
        )
    except Exception as e:
        logger.error(f"Error authenticating user {email_login}: {str(e)}")

# Создание нового пользователя
async def create_user(db: AsyncSession, user: UserCreate):
    try:
        # Проверяем, что логин, email и пароль содержат только английские символы
        validate_english_only("Login", user.login)
        validate_english_only("Email", user.email)
        validate_english_only("Password", user.password)

        # Проверяем существование пользователя по email
        existing_user = await find_user_by_login_and_email(db, user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,  # Код 409 - конфликт данных
                detail="User with this email already exists."
            )

        # Проверяем существование пользователя по логину
        existing_user = await find_user_by_login_and_email(db, user.login)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this login already exists."
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
    except HTTPException as http_exc:
        await db.rollback()
        raise http_exc
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating user {user.login}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Проверка токена
async def validate_token_logic(user):
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"message": "Token is valid", "user_id": user.id, "username": user.login}

# Деактивация токена (выход из аккаунта)
async def logout_user(token: str):
    try:
        payload = jwt.decode(token, SECRET_AUTH, algorithms=[ALGORITHM])
        exp = datetime.utcfromtimestamp(payload.get("exp"))

        # Добавляем токен в черный список
        await add_token_to_blacklist(token, exp)
        logger.info("User successfully logged out")
        return {"message": "Successfully logged out"}
    except jwt.PyJWTError:
        logger.error("Invalid token on logout")
        raise HTTPException(status_code=400, detail="Invalid token")