from tempfile import SpooledTemporaryFile
from src.cache.cache import cache
import pytest
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.services.profile_picture_service import upload_profile_picture, get_profile_picture


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Создание тестового пользователя"""
    user = User(login="testuser", email="test@example.com", hashed_password="hashedpassword")
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_upload_profile_picture(test_db: AsyncSession, test_user: User, test_cache):
    test_image = b"\x89PNG\r\n\x1a\n"  # Заголовок PNG

    temp_file = SpooledTemporaryFile()
    temp_file.write(test_image)
    temp_file.seek(0)

    dummy_file = UploadFile(
        filename="test.png",
        file=temp_file,
        headers={"content-type": "image/png"}
    )

    response = await upload_profile_picture(dummy_file, test_user, test_db)
    assert response == {"message": "Profile picture updated"}

    # Проверяем, что фото записано в БД
    updated_user = await test_db.get(User, test_user.id)
    assert updated_user.profile_picture == test_image

    # Проверяем, что кэш очищен
    cache_key1 = f"user:{updated_user.login}"
    cache_key2 = f"user:{updated_user.email}"

    cached_value1 = await cache.get(cache_key1)
    cached_value2 = await cache.get(cache_key2)

    assert cached_value1 is None
    assert cached_value2 is None


async def test_upload_invalid_file_type(test_db: AsyncSession, test_user: User):
    """Тест загрузки некорректного формата файла"""
    file = UploadFile(filename="test.txt", file=SpooledTemporaryFile(), headers={"content-type": "text/plain"})

    with pytest.raises(HTTPException) as excinfo:
        await upload_profile_picture(file, test_user, test_db)

    assert excinfo.value.status_code == 400
    assert "Only images" in str(excinfo.value.detail)


async def test_get_profile_picture(test_db: AsyncSession, test_user: User):
    """Тест получения фото профиля"""
    # Записываем фото в БД
    test_user.profile_picture = b"testimagecontent"
    await test_db.commit()

    # Запрос к сервису
    image = await get_profile_picture(test_user, test_db)

    # Убедитесь, что данные правильно извлекаются
    assert image == b"testimagecontent"


async def test_get_profile_picture_not_found(test_db: AsyncSession, test_user: User):
    """Тест получения фото профиля, если оно не загружено"""
    with pytest.raises(HTTPException) as excinfo:
        await get_profile_picture(test_user, test_db)

    assert excinfo.value.status_code == 404
    assert "No profile picture found" in str(excinfo.value.detail)
