from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from select import select
import httpx
from starlette.responses import RedirectResponse
from src.core.config import config
from src.core.security import Security
from src.database.database import get_async_session
from src.logging_config import logger
from src.models.user import User
from src.rabbitmq.consumer import consume_messages
from src.schemas.user import UserCreate, UserAuth
from src.services.auth_service import AuthService
import urllib.parse


auth_router = APIRouter(tags=["Authentication"])


# Эндпоинт для авторизации через Google (перенаправление пользователя)
@auth_router.get('/google')
async def login_with_google():
    scope = "openid email profile"
    response_type = "code"
    state = "random_state"  # Используйте уникальный state для защиты от CSRF

    auth_params = {
        "client_id": config.CLIENT_ID,
        "redirect_uri": config.REDIRECT_URI,
        "response_type": response_type,
        "scope": scope,
        "state": state
    }

    # Строим URL для авторизации
    auth_url = config.GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(auth_params)
    logger.info(f"Redirection to a authorization URL: {auth_url}")
    return RedirectResponse(auth_url)


# Колбэк после авторизации Google (получение токена и данных пользователя)
@auth_router.get('/google/callback')
async def google_callback(request: Request, db: AsyncSession = Depends(get_async_session)):
    # Получаем код из query параметров
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found")

    # Обмен кода на токен
    token_data = await exchange_code_for_token(code)
    access_token = token_data.get("access_token")
    if not access_token:
        logger.error("Failed to fetch access token")
        raise HTTPException(status_code=400, detail="Failed to fetch access token")

    # Получаем информацию о пользователе из Google
    user_info = await get_google_user_info(access_token)
    if not user_info:
        logger.error("Google user info not found")
        raise HTTPException(status_code=400, detail="Google user info not found")

    # Проверяем, существует ли пользователь в базе данных
    query = select(User).where(User.email == user_info.get('email'))
    result = await db.execute(query)
    user = result.scalar()

    if not user:
        new_user = User(
            login=user_info["email"].split('@')[0],
            email=user_info["email"],
            google_id=user_info["sub"]
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        user = new_user
        logger.info(f"Created new user: {user.email}")

    access_token = Security.create_access_token({"sub": user.login})
    logger.info(f"JWT token created for user: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}


# Функция обмена авторизационного кода на access token
async def exchange_code_for_token(code: str):
    data = {
        "code": code,
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "redirect_uri": config.REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(config.GOOGLE_TOKEN_URL, data=data)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")
        return response.json()


# Функция получения данных пользователя из Google API
async def get_google_user_info(access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(config.GOOGLE_USERINFO_URL, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info")
        return response.json()


# Эндпоинт для регистрации нового пользователя
@auth_router.post("/registration")
async def registration(user: UserCreate, db: AsyncSession = Depends(get_async_session)):
    new_user = await AuthService.create_user(db, user)
    access_token = Security.create_access_token(data={"sub": new_user.login})
    await db.commit()
    await db.refresh(new_user)
    await consume_messages("registration_queue")
    logger.info(f"User {user.email} successfully registered")
    return {"access_token": access_token, "token_type": "bearer"}


# Эндпоинт для авторизации пользователя по email и паролю
@auth_router.post("/login")
async def login(
    data: UserAuth,
    response: Response,
    db: AsyncSession = Depends(get_async_session)
):
    user = await AuthService.authenticate_user(db, data.username, data.password)
    if not user:
        logger.warning(f"Failed login attempt: {data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = Security.create_access_token(data={"sub": data.username})
    logger.info(f"User {data.username} successfully logged in")
    response.set_cookie("fooddiary_access_token", access_token, httponly=True)
    return access_token


# Эндпоинт для выхода пользователя (аннулирования токена)
@auth_router.post("/logout")
async def logout(response: Response, user: User = Depends(Security.get_current_user)):
    return await AuthService.logout_user(response)
