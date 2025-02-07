from datetime import datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.models.user_weight import UserWeight
from src.schemas.user_weight import UserWeightUpdate
from src.services.user_weight_service import get_current_weight, get_weights, save_or_update_weight
from src.cache.cache import cache


@pytest.mark.asyncio
async def test_get_current_weight(test_db: AsyncSession, test_cache):
    test_user = User(
        id=4,
        login="testuser2",
        email="test2@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    user_weight = UserWeight(
        id=2,
        user_id=4,
        weight=70,
        recorded_at=datetime(2024,2,3).date()
    )
    test_db.add(user_weight)
    await test_db.commit()
    await test_db.refresh(user_weight)

    await cache.delete(f"user_weight:{user_weight.user_id}:2024-02-03")

    current_weight_from_db = await get_current_weight("2024-02-03", test_db, user_weight.user_id)
    assert current_weight_from_db is not None
    assert current_weight_from_db.weight == 70
    assert current_weight_from_db.recorded_at == datetime(2024,2,3).date()

    cached_user_weight = await cache.get(f"user_weight:{user_weight.user_id}:2024-02-03")
    assert cached_user_weight is not None
    assert cached_user_weight["weight"] == 70
    assert cached_user_weight["recorded_at"] == datetime(2024,2,3).date()

    user_weight_from_cache = await get_current_weight("2024-02-03", test_cache, user_weight.user_id)
    assert user_weight_from_cache is not None
    assert user_weight_from_cache.weight == cached_user_weight["weight"]


@pytest.mark.asyncio
async def test_get_weights(test_db: AsyncSession, test_cache):
    test_user = User(
        id=3,
        login="testuser3",
        email="test3@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    user_weight = UserWeight(
        id=3,
        user_id=3,
        weight=70,
        recorded_at=datetime.now().date()
    )
    test_db.add(user_weight)
    await test_db.commit()
    await test_db.refresh(user_weight)

    await cache.delete(f"user_weights:{test_user.id}:last_30_days")

    user_weights_from_db = await get_weights(test_db, test_user.id)
    assert user_weights_from_db is not None
    assert user_weights_from_db[0].weight == 70
    assert user_weights_from_db[0].recorded_at == datetime.now().date()

    cached_user_weights = await cache.get(f"user_weights:{test_user.id}:last_30_days")
    assert cached_user_weights is not None
    assert cached_user_weights[0]["weight"] == 70
    assert cached_user_weights[0]["recorded_at"] == datetime.now().date()

    user_weights_from_cache = await get_weights(test_cache, test_user.id)
    assert user_weights_from_cache is not None
    assert user_weights_from_cache[0].weight == cached_user_weights[0]["weight"]


@pytest.mark.asyncio
async def test_save_or_update_weight(test_db: AsyncSession, test_cache):
    test_user = User(
        id=5,
        login="testuser4",
        email="test4@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    user_weight = UserWeight(
        id=5,
        user_id=5,
        weight=70,
        recorded_at=datetime.now().date()
    )
    test_db.add(user_weight)
    await test_db.commit()
    await test_db.refresh(user_weight)

    user_weight_update = UserWeightUpdate(
        weight=75
    )

    updated_user_weight = await save_or_update_weight(user_weight_update, test_db, test_user.id)

    assert updated_user_weight is not None
    assert updated_user_weight.weight == 75
