from fastapi import HTTPException, status
from sqlalchemy import or_, select
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
        cached_user = await cache.get(cache_key)
        if cached_user:
            logger.info(f"Cache hit for user authentication: {email_login}")
            return UserRead.model_validate(cached_user)

        logger.info(f"Cache miss for user authentication: {email_login}. Fetching from database.")
        query = select(User).where(or_(User.login == email_login, User.email == email_login))
        result = await db.execute(query)  # Вернёт mock_result
        user = result.scalar_one_or_none()  # Вызываем scalar_one_or_none()

        if user and verify_password(password, user.hashed_password):
            user_pydantic = UserRead.model_validate(user)
            await cache.set(cache_key, user_pydantic.model_dump(mode="json"))
            return user_pydantic

        return None
    except Exception as e:
        logger.error(f"Error authenticating user {email_login}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Создание нового пользователя
async def create_user(db: AsyncSession, user: UserCreate):
    try:
        # Проверяем, существует ли пользователь с таким логином или email
        existing_user = await find_user_by_login_and_email(db, user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists."
            )

        existing_user = await find_user_by_login_and_email(db, user.login)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
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
        await db.rollback()  # Откатываем транзакцию, если возникла ошибка с пользователем
        raise http_exc
    except Exception as e:
        await db.rollback()  # Откатываем транзакцию при любой другой ошибке
        logger.error(f"Error creating user {user.login}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Проверка токена
async def validate_token_logic(user):
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"message": "Token is valid", "user_id": user.id, "username": user.login}
