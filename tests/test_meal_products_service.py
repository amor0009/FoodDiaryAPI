import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.meal import Meal
from src.models.meal_products import MealProducts
from src.models.product import Product
from src.models.user import User
from src.schemas.meal_products import MealProductsCreate, MealProductsUpdate
from src.services.meal_products_service import get_meal_products, add_meal_product, update_meal_product, \
    delete_meal_product
from src.cache.cache import cache

@pytest.mark.asyncio
async def test_get_meal_products(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser14",
        email="test14@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    meal = Meal(
        name="breakfast",
        weight=100,
        calories=100,
        proteins=100,
        fats=100,
        carbohydrates=100,
        user_id=test_user.id,
    )
    test_db.add(meal)
    await test_db.commit()
    await test_db.refresh(meal)

    product = Product(
        name="Orange",
        weight=100,
        calories=43,
        proteins=0.9,
        fats=0.1,
        carbohydrates=10,
        is_public=True
    )

    test_db.add(product)
    await test_db.commit()
    await test_db.refresh(product)

    meal_products = MealProducts(
        product_id=product.id,
        meal_id=meal.id,
        product_weight=50
    )

    test_db.add(meal_products)
    await test_db.commit()
    await test_db.refresh(meal_products)

    await cache.delete(f"meal_products:{meal_products.meal_id}")

    meal_products_from_db = await get_meal_products(test_db, meal.id)
    assert meal_products_from_db is not None
    assert len(meal_products_from_db) == 1
    assert meal_products_from_db[0].product_id == meal_products.product_id
    assert meal_products_from_db[0].meal_id == meal_products.meal_id
    assert meal_products_from_db[0].product_weight == meal_products.product_weight

    cached_meal_products = await cache.get(f"meal_products:{meal_products.meal_id}")
    assert cached_meal_products is not None
    assert len(cached_meal_products) == 1
    assert cached_meal_products[0]["product_id"] == meal_products.product_id
    assert cached_meal_products[0]["meal_id"] == meal_products.meal_id
    assert cached_meal_products[0]["product_weight"] == meal_products.product_weight

    meal_products_from_cache = await get_meal_products(test_db, meal.id)
    assert meal_products_from_cache is not None
    assert len(meal_products_from_cache) == 1
    assert meal_products_from_cache[0].product_id == cached_meal_products[0]["product_id"]
    assert meal_products_from_cache[0].meal_id == cached_meal_products[0]["meal_id"]
    assert meal_products_from_cache[0].product_weight == cached_meal_products[0]["product_weight"]

@pytest.mark.asyncio
async def test_add_meal_product(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser14",
        email="test14@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    meal = Meal(
        name="breakfast",
        weight=100,
        calories=100,
        proteins=100,
        fats=100,
        carbohydrates=100,
        user_id=test_user.id,
    )
    test_db.add(meal)
    await test_db.commit()
    await test_db.refresh(meal)

    product = Product(
        name="Orange",
        weight=100,
        calories=43,
        proteins=0.9,
        fats=0.1,
        carbohydrates=10,
        is_public=True
    )

    test_db.add(product)
    await test_db.commit()
    await test_db.refresh(product)

    meal_products_create = MealProductsCreate(
        product_id=product.id,
        product_weight=50
    )

    meal_products = await add_meal_product(test_db, meal.id, meal_products_create)
    assert meal_products is not None
    assert meal_products.product_id == meal_products_create.product_id
    assert meal_products.meal_id == meal.id
    assert meal_products.product_weight == meal_products_create.product_weight

@pytest.mark.asyncio
async def test_update_meal_product(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser14",
        email="test14@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    meal = Meal(
        name="breakfast",
        weight=100,
        calories=100,
        proteins=100,
        fats=100,
        carbohydrates=100,
        user_id=test_user.id,
    )
    test_db.add(meal)
    await test_db.commit()
    await test_db.refresh(meal)

    product = Product(
        name="Orange",
        weight=100,
        calories=43,
        proteins=0.9,
        fats=0.1,
        carbohydrates=10,
        is_public=True
    )

    test_db.add(product)
    await test_db.commit()
    await test_db.refresh(product)

    meal_products_db = MealProducts(
        product_id=product.id,
        meal_id=meal.id,
        product_weight=50
    )

    test_db.add(meal_products_db)
    await test_db.commit()
    await test_db.refresh(meal_products_db)

    meal_products_update = MealProductsUpdate(
        product_id=product.id,
        product_weight=100
    )

    meal_products = await update_meal_product(test_db, meal.id, meal_products_update)
    assert meal_products is not None
    assert meal_products.product_id == meal_products_update.product_id
    assert meal_products.meal_id == meal.id
    assert meal_products.product_weight == meal_products_update.product_weight

@pytest.mark.asyncio
async def test_delete_meal_product(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser14",
        email="test14@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    meal = Meal(
        name="breakfast",
        weight=100,
        calories=100,
        proteins=100,
        fats=100,
        carbohydrates=100,
        user_id=test_user.id,
    )
    test_db.add(meal)
    await test_db.commit()
    await test_db.refresh(meal)

    product = Product(
        name="Orange",
        weight=100,
        calories=43,
        proteins=0.9,
        fats=0.1,
        carbohydrates=10,
        is_public=True
    )

    test_db.add(product)
    await test_db.commit()
    await test_db.refresh(product)

    meal_products_db = MealProducts(
        product_id=product.id,
        meal_id=meal.id,
        product_weight=50
    )

    test_db.add(meal_products_db)
    await test_db.commit()
    await test_db.refresh(meal_products_db)

    result = await delete_meal_product(test_db, meal.id, product.id)
    assert result is not None
    assert result["message"] == f"Product with ID {product.id} removed from meal {meal.id}"
