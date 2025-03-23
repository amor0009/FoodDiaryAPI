import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.meal import Meal
from src.models.product import Product
from src.models.user import User
from src.schemas.product import ProductCreate, ProductAdd, ProductUpdate, ProductRead
from src.services.product_service import get_products, add_product, change_product_info_for_weight, add_product_to_meal, \
    get_products_by_name, get_product_by_id, update_product, get_product_by_exact_name, \
    get_product_available_to_change_by_id, get_product_available_to_change_by_name, delete_product, searching_products, \
    recalculate_product_nutrients, get_personal_products
from src.cache.cache import cache

@pytest.mark.asyncio
async def test_recalculate_product_nutrients():
    # Исходные данные продукта (на 100 г)
    db_product = Product(
        id=1,
        name="Test Product",
        weight=100,
        calories=200,       # 200 ккал на 100 г
        proteins=10,        # 10 г белка на 100 г
        fats=5,             # 5 г жиров на 100 г
        carbohydrates=30,   # 30 г углеводов на 100 г
        description="Test description",
        picture=b"/images/test.png"
    )

    # Тестируем пересчет для 50 г продукта
    product_50g = await recalculate_product_nutrients(db_product, 50)
    assert product_50g == ProductRead(
        id=1,
        name="Test Product",
        weight=50,
        calories=100.0,     # (200 * 50 / 100) = 100
        proteins=5.0,       # (10 * 50 / 100) = 5
        fats=2.5,           # (5 * 50 / 100) = 2.5
        carbohydrates=15.0, # (30 * 50 / 100) = 15
        description="Test description",
        picture_path="/images/test.png"
    )

    # Тестируем пересчет для 200 г продукта
    product_200g = await recalculate_product_nutrients(db_product, 200)
    assert product_200g == ProductRead(
        id=1,
        name="Test Product",
        weight=200,
        calories=400.0,     # (200 * 200 / 100) = 400
        proteins=20.0,      # (10 * 200 / 100) = 20
        fats=10.0,          # (5 * 200 / 100) = 10
        carbohydrates=60.0, # (30 * 200 / 100) = 60
        description="Test description",
        picture_path="/images/test.png"
    )

    # Тестируем пересчет для 0 г продукта (должны быть нули)
    product_0g = await recalculate_product_nutrients(db_product, 0)
    assert product_0g == ProductRead(
        id=1,
        name="Test Product",
        weight=0,
        calories=0.0,
        proteins=0.0,
        fats=0.0,
        carbohydrates=0.0,
        description="Test description",
        picture_path="/images/test.png"
    )

@pytest.mark.asyncio
async def test_get_products(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser5",
        email="test5@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    product = Product(
        name="Apple",
        weight=100,
        calories=52,
        proteins=0.3,
        fats=0.2,
        carbohydrates=14,
        user_id=test_user.id,
        is_public=False
    )
    test_db.add(product)
    await test_db.commit()
    await test_db.refresh(product)

    # Удаляем возможный кеш перед тестом
    await cache.delete(f"products:{test_user.id}")

    products = await get_products(test_db, test_user.id)
    assert len(products) == 1
    assert products[0].name == "Apple"

    # Проверяем, что данные попали в кэш
    cached_products = await cache.get(f"products:{test_user.id}")
    assert cached_products is not None
    assert len(cached_products) == 1
    assert cached_products[0]["name"] == "Apple"

@pytest.mark.asyncio
async def test_add_product(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser6",
        email="test6@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    product_data = ProductCreate(
        name="Test Product",
        weight=100,
        calories=96,
        proteins=1.3,
        fats=0.3,
        carbohydrates=27,
        description="yellow banana"
    )

    # Удаляем кеш перед тестом
    await cache.delete(f"products:{test_user.id}")

    product = await add_product(test_db, product_data, test_user.id)
    assert product.name == "Test Product"
    assert product.calories == 96

    # Проверяем, что кеш сбросился
    cached_products = await cache.get(f"products:{test_user.id}")
    assert cached_products is None

@pytest.mark.asyncio
async def test_change_product_info_for_weight(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser7",
        email="test7@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    base_product = Product(name="Rice", weight=100, calories=130, proteins=2.7, fats=0.3, carbohydrates=28,
                           user_id=test_user.id)
    test_db.add(base_product)
    await test_db.commit()
    await test_db.refresh(base_product)

    product_add = ProductAdd(name="Rice", weight=50)

    await cache.delete(f"product:{test_user.id}:{product_add.name}")

    updated_product = await change_product_info_for_weight(test_db, product_add, test_user.id)
    assert updated_product.weight == 50
    assert updated_product.calories == 65
    assert updated_product.proteins == 1.35

@pytest.mark.asyncio
async def test_add_product_to_meal(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser8",
        email="test8@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    meal = Meal(name="Lunch", weight=0, calories=0, proteins=0, fats=0, carbohydrates=0, user_id=test_user.id)
    product = Product(name="Chicken", weight=100, calories=165, proteins=31, fats=3.6, carbohydrates=0,
                      user_id=test_user.id)

    test_db.add_all([meal, product])
    await test_db.commit()
    await test_db.refresh(meal)
    await test_db.refresh(product)

    product_add = ProductAdd(name="Chicken", weight=50)
    updated_meal = await add_product_to_meal(test_db, meal.id, product_add, test_user.id)

    assert updated_meal.weight == 50
    assert updated_meal.calories == 82.5

@pytest.mark.asyncio
async def test_get_personal_products(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser9",
        email="test9@example.com",
        hashed_password="testpassword"
    )
    other_test_user = User(
        login="testuser10",
        email="test10@example.com",
        hashed_password="testpassword"
    )
    test_db.add_all([test_user, other_test_user])
    await test_db.commit()
    await test_db.refresh(test_user)
    await test_db.refresh(other_test_user)

    public_product = Product(
        name="Orange",
        weight=100,
        calories=43,
        proteins=0.9,
        fats=0.1,
        carbohydrates=10,
        is_public=True
    )
    private_product = Product(
        name="Milk",
        weight=100,
        calories=42,
        proteins=3.4,
        fats=1,
        carbohydrates=5,
        user_id=test_user.id,
        is_public=False
    )
    other_user_product = Product(
        name="pop",
        weight=100,
        calories=33,
        proteins=2.1,
        fats=1,
        carbohydrates=6,
        user_id=other_test_user.id,
        is_public=False
    )

    test_db.add_all([public_product, private_product, other_user_product])
    await test_db.commit()

    await cache.delete(f"personal_products:{test_user.id}")
    products = await get_personal_products(test_db, test_user.id)
    assert products is not None
    assert len(products) == 1
    assert products[0].name == "Milk"

    cached_products = await cache.get(f"personal_products:{test_user.id}")
    assert cached_products is not None
    assert len(cached_products) == 1
    assert cached_products[0]["name"] == "Milk"

    products_from_cache = await get_personal_products(test_db, test_user.id)
    assert products_from_cache is not None
    assert products_from_cache[0].name == cached_products[0]["name"]

@pytest.mark.asyncio
async def test_get_products_by_name(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser14",
        email="test14@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    product1 = Product(
        name="Tomator",
        weight=100,
        calories=18,
        proteins=0.9,
        fats=0.2,
        carbohydrates=3.9,
        is_public=True
    )
    product2 = Product(
        name="Tomato salat",
        weight=100,
        calories=18,
        proteins=0.9,
        fats=0.2,
        carbohydrates=3.9,
        is_public=True
    )

    test_db.add_all([product1, product2])
    await test_db.commit()
    await test_db.refresh(product1)
    await test_db.refresh(product2)

    await cache.delete(f"products:{test_user.id}:Tomato")

    products = await get_products_by_name(test_db, "Tomato", test_user.id)
    assert products is not None
    assert len(products) == 2
    assert products[0].name == product1.name
    assert products[1].name == product2.name

    cached_products = await cache.get(f"products:{test_user.id}:Tomato")
    assert cached_products is not None
    assert len(cached_products) == 2
    assert cached_products[0]["name"] == product1.name
    assert cached_products[1]["name"] == product2.name

    products_from_cache = await get_products_by_name(test_db, "Tomato", test_user.id)
    assert products_from_cache is not None
    assert len(products_from_cache) == 2
    assert products_from_cache[0].name == cached_products[0]["name"]
    assert products_from_cache[1].name == cached_products[1]["name"]

@pytest.mark.asyncio
async def test_get_product_by_exact_name(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser11",
        email="test11@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    product = Product(
        name="Tomato3",
        weight=100,
        calories=18,
        proteins=0.9,
        fats=0.2,
        carbohydrates=3.9,
        user_id=test_user.id
    )

    test_db.add(product)
    await test_db.commit()
    await test_db.refresh(product)

    await cache.delete(f"product_exact:{test_user.id}:{product.name}")

    product = await get_product_by_exact_name(test_db, "Tomato3", test_user.id)
    assert product is not None
    assert product.name == product.name

    cached_product = await cache.get(f"product_exact:{test_user.id}:{product.name}")
    assert cached_product is not None
    assert cached_product["name"] == product.name

    product_from_cache = await get_product_by_exact_name(test_db, "Tomato3", test_user.id)
    assert product_from_cache is not None
    assert product_from_cache.name == cached_product["name"]

@pytest.mark.asyncio
async def test_get_product_by_id(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser12",
        email="test12@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    product = Product(
        name="Cheese",
        weight=100,
        calories=402,
        proteins=25,
        fats=33,
        carbohydrates=1.3,
        user_id=test_user.id)
    test_db.add(product)
    await test_db.commit()
    await test_db.refresh(product)

    await cache.delete(f"product:{test_user.id}:{product.id}")

    product_from_db = await get_product_by_id(test_db, product.id, test_user.id)
    assert product_from_db is not None
    assert product_from_db.name == product.name

    cached_product = await cache.get(f"product:{test_user.id}:{product.id}")
    assert cached_product is not None
    assert cached_product["name"] == "Cheese"

    product_from_cache = await get_product_by_id(test_db, product.id, test_user.id)
    assert product_from_cache is not None
    assert product_from_cache.name == cached_product["name"]

@pytest.mark.asyncio
async def test_update_product(test_db: AsyncSession, test_cache):
    test_user = User(
        id=14,
        login="testuser13",
        email="test13@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    product = Product(
        name="Yogurt",
        weight=100,
        calories=59,
        proteins=10,
        fats=0.4,
        carbohydrates=4.7,
        user_id=test_user.id,
        is_public=False
    )
    test_db.add(product)
    await test_db.commit()
    await test_db.refresh(product)

    update_data = ProductUpdate(id=product.id, name="Greek Yogurt", calories=61)

    await cache.delete(f"personal_product:{test_user.id}:{product.id}")

    updated_product = await update_product(test_db, update_data, test_user.id)
    assert updated_product.name == "Greek Yogurt"
    assert updated_product.calories == 61

@pytest.mark.asyncio
async def test_get_product_available_to_change_by_id(test_db: AsyncSession, test_cache):
    test_user = User(
        id=16,
        login="testuser15",
        email="test15@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    product = Product(
        id=11,
        name="Cesar",
        weight=100,
        calories=402,
        proteins=25,
        fats=33,
        carbohydrates=1.3,
        user_id=test_user.id,
        is_public=False
    )
    test_db.add(product)
    await test_db.commit()
    await test_db.refresh(product)

    product = await get_product_available_to_change_by_id(test_db, product.id, test_user.id)
    assert product is not None
    assert product.name == "Cesar"
    assert product.is_public is False

@pytest.mark.asyncio
async def test_get_product_available_to_change_by_name(test_db: AsyncSession, test_cache):
    test_user = User(
        id=17,
        login="testuser16",
        email="test16@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    product = Product(
        id=12,
        name="Apple1",
        weight=100,
        calories=402,
        proteins=25,
        fats=33,
        carbohydrates=1.3,
        user_id=test_user.id,
        is_public=False
    )
    test_db.add(product)
    await test_db.commit()
    await test_db.refresh(product)

    await cache.delete(f"personal_product:{test_user.id}:{product.name}")

    product = await get_product_available_to_change_by_name(test_db, product.name, test_user.id)
    assert product is not None
    assert product.name == "Apple1"

    cached_product = await cache.get(f"personal_product:{test_user.id}:{product.name}")
    assert cached_product is not None
    assert cached_product["name"] == "Apple1"

    product_from_cache = await get_product_available_to_change_by_name(test_db, product.name, test_user.id)
    assert product_from_cache is not None
    assert product_from_cache.name == cached_product["name"]

@pytest.mark.asyncio
async def test_delete_product(test_db: AsyncSession, test_cache):
    test_user = User(
        id=18,
        login="testuser17",
        email="test17@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    product = Product(
        id=13,
        name="Banana",
        weight=100,
        calories=402,
        proteins=25,
        fats=33,
        carbohydrates=1.3,
        user_id=test_user.id,
        is_public=False
    )
    test_db.add(product)
    await test_db.commit()
    await test_db.refresh(product)

    deleted_product = await delete_product(test_db, test_user.id, product.id)
    assert deleted_product is not None
    assert deleted_product.name == product.name

    deleted = await test_db.get(Product, product.id)
    assert deleted is None

@pytest.mark.asyncio
async def test_searching_products(test_db: AsyncSession, test_cache):
    test_user = User(
        id=15,
        login="testuser14",
        email="test14@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    product1 = Product(
        id=14,
        name="Tomato",
        weight=100,
        calories=18,
        proteins=0.9,
        fats=0.2,
        carbohydrates=3.9,
        is_public=True
    )
    product2 = Product(
        id=12,
        name="Tomato salat",
        weight=100,
        calories=18,
        proteins=0.9,
        fats=0.2,
        carbohydrates=3.9,
        is_public=True
    )

    test_db.add_all([product1, product2])
    await test_db.commit()
    await test_db.refresh(product1)
    await test_db.refresh(product2)

    products = await searching_products(test_db, test_user.id, "Tom")
    assert products is not None
    assert len(products) == 2
    assert products[0].name == "Tomato"
    assert products[1].name == "Tomato salat"
