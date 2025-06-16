import re
from datetime import timedelta, datetime
import jwt as pyjwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import Configuration
from src.daos.staff_dao import StaffDAO
from src.database.database import get_async_session
from src.exceptions import TokenDoesntExist, CredentialsException, TokenHasExpired, InvalidToken, UserDoesntExist, \
    CustomExceptions, StaffDoesntExist
from src.services.user_service import UserService
from src.logging_config import logger


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class Security:
    # Получение токена
    @staticmethod
    def get_token(token_name: str):
        def _get_token(request: Request):
            token = request.cookies.get(token_name)
            if not token:
                raise TokenDoesntExist
            return token
        return _get_token

    # Получение текущего пользователя из токена
    @staticmethod
    async def get_required_user(token: str = Depends(get_token("fooddiary_access_token")), db: AsyncSession = Depends(get_async_session)):
        try:
            payload = pyjwt.decode(token, Configuration.USER_SECRET_AUTH, algorithms=[Configuration.ALGORITHM])
        except Exception:
            raise CredentialsException
        expire: str = payload.get("exp")
        if (not expire) or (int(expire) < datetime.utcnow().timestamp()):
            raise TokenHasExpired
        login: str = payload.get("sub")
        if not login:
            raise InvalidToken

        user = await UserService.find_user_by_login_and_email(db, login)
        if user is None:
            raise UserDoesntExist

        return user

    @staticmethod
    async def get_possible_user(token: str = Depends(get_token), db: AsyncSession = Depends(get_async_session)):
        try:
            payload = pyjwt.decode(token, Configuration.USER_SECRET_AUTH, algorithms=[Configuration.ALGORITHM])
        except Exception:
            return None
        expire: str = payload.get("exp")
        if (not expire) or (int(expire) < datetime.utcnow().timestamp()):
            return None
        login: str = payload.get("sub")
        if not login:
            return None

        user = await UserService.find_user_by_login_and_email(db, login)
        if user is None:
            return None

        return user

    @staticmethod
    async def get_staff_from_request(request: Request):
        db = request.state.db
        token = request.cookies.get("staff_access_token")
        return await Security.get_required_staff(token=token, db=db)

    @staticmethod
    async def get_required_staff(token: str = Depends(get_token("staff_access_token")), db: AsyncSession = Depends(get_async_session)):
        try:
            payload = pyjwt.decode(token, Configuration.STAFF_SECRET_AUTH, algorithms=[Configuration.ALGORITHM])
        except Exception:
            raise CredentialsException
        expire: str = payload.get("exp")
        if (not expire) or (int(expire) < datetime.utcnow().timestamp()):
            raise TokenHasExpired
        login: str = payload.get("sub")
        if not login:
            raise InvalidToken

        staff = await StaffDAO.find_one_or_none(db, login=login)
        if staff is None:
            raise StaffDoesntExist

        return staff

    # Проверка пароля
    @classmethod
    def verify_password(cls, plain_password, hashed_password):
        if pwd_context.verify(plain_password, hashed_password):
            return True
        return False

    # Хэширование пароля
    @classmethod
    def get_password_hash(cls, password):
        return pwd_context.hash(password)

    # Проверка сложности пароля с настраиваемыми параметрами
    @classmethod
    def validate_password_strength(
            cls,
            password: str,
            min_length: int = 8,
            require_upper: bool = True,
            require_lower: bool = True,
            require_digit: bool = True,
            require_special: bool = True,
            special_chars: str = Configuration.SPECIAL_CHARS
    ):
        errors = []
        checks = [
            (lambda: len(password) >= min_length,
             f"Password must be at least {min_length} characters long"),
            (lambda: not require_upper or re.search(r'[A-Z]', password),
             "Password must contain at least one uppercase letter"),
            (lambda: not require_lower or re.search(r'[a-z]', password),
             "Password must contain at least one lowercase letter"),
            (lambda: not require_digit or re.search(r'[0-9]', password),
             "Password must contain at least one digit"),
            (lambda: not require_special or re.search(f'[{re.escape(special_chars)}]', password),
             f"Password must contain at least one special character ({special_chars})")
        ]

        for condition, error_msg in checks:
            if not condition():
                errors.append(error_msg)

        if errors:
            CustomExceptions.raise_password_validation_error(
                errors=errors,
                min_length=min_length,
                require_upper=require_upper,
                require_lower=require_lower,
                require_digit=require_digit,
                require_special=require_special,
                special_chars=special_chars
            )

    # Создание токена доступа с временем жизни
    @classmethod
    def create_access_token(cls, data: dict, secret_key: str):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=int(Configuration.ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        return pyjwt.encode(to_encode, secret_key, algorithm=Configuration.ALGORITHM)
