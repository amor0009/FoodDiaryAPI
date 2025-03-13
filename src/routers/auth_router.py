from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from select import select
import httpx
from starlette.responses import RedirectResponse
from src.core.config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, GOOGLE_AUTH_URL, GOOGLE_TOKEN_URL, \
    GOOGLE_USERINFO_URL
from src.core.security import create_access_token, get_current_user
from src.database.database import get_async_session
from src.logging_config import logger
from src.models.user import User
from src.rabbitmq.consumer import consume_messages
from src.schemas.user import UserCreate
from src.services.auth_service import create_user, authenticate_user, validate_token_logic
import urllib.parse

auth_router = APIRouter()

# Запрос для авторизации (перенаправление пользователя)
@auth_router.get('/google')
async def login_with_google():
    scope = "openid email profile"
    response_type = "code"
    state = "random_state"  # Используйте уникальный state для защиты от CSRF

    auth_params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": response_type,
        "scope": scope,
        "state": state
    }

    # Строим URL для авторизации
    auth_url = GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(auth_params)
    logger.info(f"Redirection to a authorization URL: {auth_url}")
    return RedirectResponse(auth_url)

# Колбэк после авторизации
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
        logger.info(f"Создан новый пользователь: {user.email}")

    access_token = create_access_token({"sub": user.login})
    logger.info(f"JWT токен создан для пользователя: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}

# Функция обмена авторизационного кода на access token
async def exchange_code_for_token(code: str):
    data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=data)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")
        return response.json()

# Функция получения данных пользователя из Google API
async def get_google_user_info(access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info")
        return response.json()

# Регистрация нового пользователя
@auth_router.post("/registration")
async def registration(user: UserCreate, db: AsyncSession = Depends(get_async_session)):
    new_user = await create_user(db, user)
    access_token = create_access_token(data={"sub": new_user.login})
    await db.commit()
    await db.refresh(new_user)
    await consume_messages("registration_queue")
    logger.info(f"Пользователь {user.email} успешно зарегистрирован")
    return {"access_token": access_token, "token_type": "bearer"}

# Авторизация по email и паролю
@auth_router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),  # <-- Заменяем на OAuth2PasswordRequestForm
    db: AsyncSession = Depends(get_async_session)
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Неудачная попытка авторизации: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": form_data.username})
    logger.info(f"Пользователь {form_data.username} успешно авторизован")
    return {"access_token": access_token, "token_type": "bearer"}

# Валидация токена
@auth_router.post("/validate-token")
async def validate_token(current_user: User = Depends(get_current_user)):
    try:
        return validate_token_logic(current_user)
    except HTTPException as e:
        raise e
