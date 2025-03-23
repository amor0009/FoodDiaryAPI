from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Response
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import get_current_user
from src.database.database import get_async_session
from src.models.user import User
from src.schemas.user import UserUpdate, UserCalculateNutrients, UserRead
from src.services.user_service import delete_user, calculate_recommended_nutrients, get_profile_picture, \
    upload_profile_picture
from src.services.user_service import update_user, find_user_by_login_and_email

user_router = APIRouter()

# Эндпоинт для удаления текущего пользователя
@user_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(current_user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_async_session)):
    # Удаляем текущего пользователя
    deleted_user = await delete_user(db, current_user)
    return {"status": status.HTTP_200_OK, "user": deleted_user}

# Эндпоинт для получения данных о текущем пользователе
@user_router.get("/me", response_model=UserRead)
async def get_current_user_data(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Возвращаем информацию о текущем пользователе
    return UserRead.model_validate(current_user)

# Эндпоинт для поиска пользователя по логину или email
@user_router.get("/find/{login_email}")
async def find_user(login_email: str, db: AsyncSession = Depends(get_async_session)):
    # Ищем пользователя по логину или email
    user = await find_user_by_login_and_email(db, login_email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"status": status.HTTP_200_OK, "user": user}

# Эндпоинт для обновления данных текущего пользователя
@user_router.put("/me")
async def update_current_user(user: UserUpdate, db: AsyncSession = Depends(get_async_session),
                              current_user: User = Depends(get_current_user)):
    updated_user = await update_user(user, db, current_user)
    return {"status": status.HTTP_200_OK, "user": updated_user}

# Эндпоинт для расчета рекомендованных нутриентов для пользователя
@user_router.post("/calculate_nutrients")
async def calculate_nutrients_for_all_users(user: UserCalculateNutrients):
    return await calculate_recommended_nutrients(user)

# Эндпоинт для загрузки нового фото профиля
@user_router.post("/upload-profile-picture")
async def upload_photo(
    file: UploadFile = File(...),  # Получаем файл из запроса
    current_user: User = Depends(get_current_user),  # Получаем текущего пользователя
    db: AsyncSession = Depends(get_async_session),  # Получаем сессию базы данных
):
    # Загружаем фото профиля пользователя
    return await upload_profile_picture(file, current_user, db)


# Эндпоинт для получения фото профиля
@user_router.get("/profile-picture")
async def get_photo(
    current_user: User = Depends(get_current_user),  # Получаем текущего пользователя
    db: AsyncSession = Depends(get_async_session),  # Получаем сессию базы данных
):
    # Получаем фото профиля пользователя
    image = await get_profile_picture(current_user, db)
    return Response(content=image, media_type="image/jpeg")  # Возвращаем изображение в формате JPEG
