import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.cache.cache import cache
from src.schemas.user import UserCreate
from src.services.auth_service import authenticate_user, create_user

@pytest.mark.asyncio
async def test_auth_service(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser14",
        email="test14@example.com",
        hashed_password="$2b$12$Eeb6UAVLG9v.25hXBB/f5.HLuy7rRPjY3xkZQGqIEgIhSgi957ac6"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    await cache.delete(f"user_auth:{test_user.login}")

    user = await authenticate_user(test_db, test_user.login, "testpassword")
    assert user is not None
    assert user.login == test_user.login

    cached_user = await cache.get(f"user_auth:{test_user.login}")
    assert cached_user is not None
    assert cached_user["login"] == test_user.login

    user_from_cache = await authenticate_user(test_db, test_user.login, "testpassword")
    assert user_from_cache is not None
    assert user_from_cache.login == test_user.login

@pytest.mark.asyncio
async def test_create_user_service(test_db: AsyncSession, test_rabbitmq):
    test_user = UserCreate(
        login="testuser14",
        email="test14@example.com",
        password="testpassword"
    )

    user = await create_user(test_db, test_user)
    assert user is not None
    assert user.email == "test14@example.com"
