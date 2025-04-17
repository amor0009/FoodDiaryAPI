from datetime import timedelta, datetime
import jwt as pyjwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_AUTH, ALGORITHM
from src.database.database import get_async_session
from src.logging_config import logger
from src.services.user_service import find_user_by_login_and_email

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Получение токена
async def get_token(request: Request):
    token = request.cookies.get("fooddiary_access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="There is no access token."
        )
    return token


# Получение текущего пользователя из токена
async def get_current_user(token: str = Depends(get_token), db: AsyncSession = Depends(get_async_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = pyjwt.decode(token, SECRET_AUTH, algorithms=[ALGORITHM])
    except Exception:
        raise credentials_exception
    expire: str = payload.get("exp")
    if (not expire) or (int(expire) < datetime.utcnow().timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired."
        )
    login: str = payload.get("sub")
    if not login:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not ...."
        )

    user = await find_user_by_login_and_email(db, login)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=""
        )

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
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return pyjwt.encode(to_encode, SECRET_AUTH, algorithm=ALGORITHM)
