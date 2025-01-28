from datetime import timedelta, datetime
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import PyJWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_AUTH, ALGORITHM
from src.database.database import get_async_session
from src.logging_config import logger
from src.services.user_service import find_user_by_login_and_email


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_async_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_AUTH, algorithms=[ALGORITHM])
        login: str = payload.get("sub")
        if login is None:
            logger.warning(f"Token isn't successfully decoded for user: {login}")
            raise credentials_exception
        logger.info(f"Token is successfully decoded for user: {login}")
    except PyJWTError:
        logger.error("Token decoding error")
        raise credentials_exception

    user = await find_user_by_login_and_email(db, login)
    if user is None:
        logger.warning(f"User with login {login} not found")
        raise credentials_exception
    return user


def verify_password(plain_password, hashed_password):
    if pwd_context.verify(plain_password, hashed_password):
        return True
    return False


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES)))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_AUTH, algorithm=ALGORITHM)
