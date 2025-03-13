from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.cache.cache import cache

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif"}


async def upload_profile_picture(file: UploadFile, current_user: User, db: AsyncSession):
    """Загружает фото профиля пользователя"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only images (JPEG, PNG, GIF) are allowed")

    user = await db.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.profile_picture = await file.read()
    await db.commit()
    await db.refresh(user)

    # Очистка кэша
    cache_key1 = f"user:{user.login}"
    cache_key2 = f"user:{user.email}"
    await cache.delete(cache_key1)
    await cache.delete(cache_key2)

    return {"message": "Profile picture updated"}


async def get_profile_picture(current_user: User, db: AsyncSession):
    """Возвращает фото профиля пользователя"""
    user = await db.get(User, current_user.id)
    if not user or not user.profile_picture:
        raise HTTPException(status_code=404, detail="No profile picture found")

    return user.profile_picture
