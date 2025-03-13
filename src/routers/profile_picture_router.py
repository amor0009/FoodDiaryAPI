from fastapi import APIRouter, UploadFile, File, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_current_user
from src.database.database import get_async_session
from src.services.profile_picture_service import upload_profile_picture, get_profile_picture
from src.models.user import User

photo_router = APIRouter()


@photo_router.post("/upload-profile-picture")
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await upload_profile_picture(file, current_user, db)


@photo_router.get("/profile-picture")
async def get_photo(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    image = await get_profile_picture(current_user, db)
    return Response(content=image, media_type="image/jpeg")
