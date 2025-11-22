from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.core.config import Configuration
from api.src.core.security import Security
from api.src.database.database import get_async_session
from api.logging_config import logger
from api.src.schemas.user import UserAuth, CheckRegistrationUser, CreateUser, UserRead
from api.src.services.user import UserService
from api.src.dependencies.services import get_user_service


auth_router = APIRouter(prefix="/api/auth", tags=["authentication"])


@auth_router.post("/register/start")
async def start_registration(
    email: str,
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
) -> dict:
    await user_service.start_register_user(session, email)
    return {"message": "Код подтверждения отправлен на email"}


@auth_router.get("/register/check")
async def check_registration_code(
    code: str,
    user_registration_data: CheckRegistrationUser = Depends(),
    user_service: UserService = Depends(get_user_service),
) -> dict:
    await user_service.check_registration_code(user_registration_data, code)
    return {"message": "Код подтвержден успешно"}


@auth_router.post("/register/final", status_code=status.HTTP_201_CREATED)
async def register_user_final(
    user_data: CreateUser,
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    user = await user_service.create_user(session, user_data)
    return user


@auth_router.post("/login")
async def login(
    data: UserAuth,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
) -> dict:
    user = await user_service.authenticate_user(session, data.username, data.password)
    if not user:
        logger.warning(f"Failed login attempt: {data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = Security.create_access_token(data={"sub": data.username}, secret_key=Configuration.USER_SECRET_AUTH)
    logger.info(f"User {data.username} successfully logged in")
    response.set_cookie("fooddiary_access_token", access_token, httponly=True)
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.post("/logout")
async def logout(
    response: Response,
    user_service: UserService = Depends(get_user_service),
) -> dict:
    await user_service.logout_user(response)
    return {"message": "Successfully logged out"}
