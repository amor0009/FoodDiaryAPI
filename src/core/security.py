from datetime import timedelta, datetime
import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from src.cache.cache import cache
from src.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_AUTH, ALGORITHM
from src.database.database import get_async_session
from src.logging_config import logger
from src.services.user_service import find_user_by_login_and_email

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Получение текущего пользователя из токена
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_async_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Проверяем, есть ли токен в черном списке
        if await is_token_blacklisted(token):
            logger.warning("Attempt to use blacklisted token")
            raise credentials_exception

        payload = pyjwt.decode(token, SECRET_AUTH, algorithms=[ALGORITHM])
        login: str = payload.get("sub")
        if login is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user = await find_user_by_login_and_email(db, login)
    if user is None:
        raise credentials_exception

    return user

# Проверка пароля
def verify_password(plain_password, hashed_password):
    if pwd_context.verify(plain_password, hashed_password):
        return True
    return False

# Хэширование пароля
def get_password_hash(password):
    return pwd_context.hash(password)

# Создание токена доступа с временем жизни
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES)))
    to_encode.update({"exp": expire})
    return pyjwt.encode(to_encode, SECRET_AUTH, algorithm=ALGORITHM)

# Добавление токена в черный список с TTL, равным времени истечения токена
async def add_token_to_blacklist(token: str, expires_at: datetime):
    ttl = (expires_at - datetime.utcnow()).total_seconds()
    if ttl > 0:
        await cache.set(f"blacklist:{token}", "blacklisted", expire=int(ttl))
        logger.info(f"Token added to blacklist: {token} with TTL {ttl} seconds")

# Проверка, находится ли токен в черном списке
async def is_token_blacklisted(token: str) -> bool:
    result = await cache.get(f"blacklist:{token}")
    if result:
        logger.warning(f"Token {token} is blacklisted")
    return result is not None
