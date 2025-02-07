import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.schemas.user import UserUpdate, UserRead
from src.services.user_service import delete_user, update_user, find_user_by_login_and_email, \
    calculate_recommended_nutrients
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
async def test_calculate_recommended_nutrients(test_cache):
    user = UserRead(
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
    assert cached_result is not None
    assert len(cached_result) == 4
    assert cached_result["calories"] == 3066.67
    assert cached_result["fat"] == 85.19
    assert cached_result["protein"] == 191.67
    assert cached_result["carbohydrates"] == 383.33

    result_from_cache = await calculate_recommended_nutrients(user)
    assert result_from_cache is not None
    assert len(result_from_cache) == 4
    assert result_from_cache["calories"] == result["calories"]
    assert result_from_cache["fat"] == result["fat"]
    assert result_from_cache["protein"] == result["protein"]
    assert result_from_cache["carbohydrates"] == result["carbohydrates"]
