from tempfile import SpooledTemporaryFile
import pytest
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.schemas.user import UserUpdate, UserCalculateNutrients
from src.services.user_service import delete_user, update_user, find_user_by_login_and_email, \
    calculate_recommended_nutrients, upload_profile_picture, get_profile_picture
from src.cache.cache import cache

@pytest.mark.asyncio
async def test_delete_user(test_db: AsyncSession):
    user = User(
        id=1,
        login="testuser",
        email="test@example.com",
        hashed_password="hashed_test_password",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    await delete_user(test_db, user)

    deleted_user = await test_db.get(User, user.id)
    assert deleted_user is None

@pytest.mark.asyncio
async def test_update_user(test_cache, test_db: AsyncSession):
    user = User(
        login="test_user",
        email="test@example.com",
        hashed_password="hashed_test_password",
        weight=69,
        firstname="test",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    user_update = UserUpdate(
        login="testuser",
        email="test@example.com",
        firstname="new_test_name",
        weight=75,
    )

    updated_user = await update_user(user_update, test_db, user)

    assert updated_user.firstname == "new_test_name"
    assert updated_user.weight == 75

@pytest.mark.asyncio
async def test_find_user_with_login_and_email(test_db: AsyncSession, test_cache):
    test_user = User(
        id=2,
        login="testuser1",
        email="test1@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    await cache.delete(f"user:{test_user.login}")
    await cache.delete(f"user:{test_user.email}")

    user_from_db = await find_user_by_login_and_email(test_db, "test1@example.com")
    assert user_from_db is not None
    assert user_from_db.email == "test1@example.com"
    assert user_from_db.login == "testuser1"

    cached_user = await cache.get(f"user:{test_user.email}")
    assert cached_user is not None
    assert cached_user["login"] == "testuser1"
    assert cached_user["email"] == "test1@example.com"

    user_from_cache = await find_user_by_login_and_email(test_db, "test1@example.com")
    assert user_from_cache is not None
    assert user_from_cache.login == "testuser1"
    assert user_from_cache.email == "test1@example.com"

@pytest.mark.asyncio
async def test_calculate_recommended_nutrients_for_auth_user(test_cache):
    user = UserCalculateNutrients(
        id=1,
        login="testuser",
        email="test@example.com",
        firstname="Иван",
        lastname="Иванов",
        age=30,
        height=175,
        weight=70,
        gender="male",
        aim="gain",
        activity_level="moderate"
    )

    await cache.delete(f"user_nutrients:{user.id}")

    result = await calculate_recommended_nutrients(user)
    assert result is not None
    assert len(result) == 4
    assert result["calories"] == 3066.67
    assert result["fat"] == 85.19
    assert result["protein"] == 191.67
    assert result["carbohydrates"] == 383.33

    cached_result = await cache.get(f"user_nutrients:{user.id}")
    assert cached_result is None

@pytest.mark.asyncio
async def test_calculate_recommended_nutrients_for_no_auth_user(test_cache):
    user = UserCalculateNutrients(
        age=30,
        height=175,
        weight=70,
        gender="male",
        aim="gain",
        activity_level="moderate"
    )

    await cache.delete(f"user_nutrients:None")

    result = await calculate_recommended_nutrients(user)
    assert result is not None
    assert len(result) == 4
    assert result["calories"] == 3066.67
    assert result["fat"] == 85.19
    assert result["protein"] == 191.67
    assert result["carbohydrates"] == 383.33

    cached_result = await cache.get(f"user_nutrients:{user.id}")
    assert cached_result is None

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

@pytest.mark.asyncio
async def test_upload_invalid_file_type(test_db: AsyncSession, test_user: User):
    """Тест загрузки некорректного формата файла"""
    file = UploadFile(filename="test.txt", file=SpooledTemporaryFile(), headers={"content-type": "text/plain"})

    with pytest.raises(HTTPException) as excinfo:
        await upload_profile_picture(file, test_user, test_db)

    assert excinfo.value.status_code == 400
    assert "Only images" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_get_profile_picture(test_db: AsyncSession, test_user: User):
    """Тест получения фото профиля"""
    # Записываем фото в БД
    test_user.profile_picture = b"testimagecontent"
    await test_db.commit()

    # Запрос к сервису
    image = await get_profile_picture(test_user, test_db)

    # Убедитесь, что данные правильно извлекаются
    assert image == b"testimagecontent"

@pytest.mark.asyncio
async def test_get_profile_picture_not_found(test_db: AsyncSession, test_user: User):
    """Тест получения фото профиля, если оно не загружено"""
    with pytest.raises(HTTPException) as excinfo:
        await get_profile_picture(test_user, test_db)

    assert excinfo.value.status_code == 404
    assert "No profile picture found" in str(excinfo.value.detail)
