from datetime import date, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.meal import Meal
from src.models.meal_products import MealProducts
from src.models.product import Product
from src.models.user import User
from src.schemas.meal_products import MealProductsCreate, MealProductsUpdate
from src.schemas.meal import MealCreate, MealRead, MealUpdate
from src.schemas.product import ProductRead
from src.services.meal_service import add_meal, get_user_meals, get_user_meals_with_products_by_date, \
    recalculate_meal_nutrients, get_meal_by_id, get_meals_by_date, get_meals_last_7_days, update_meal, delete_meal
from src.cache.cache import cache

@pytest.mark.asyncio
async def test_recalculate_meal_nutrients(test_db: AsyncSession) -> None:
    test_user = User(
        login="testuser6",
        email="test6@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    # Продукты, которые входят в прием пищи
    product1 = Product(
        id=1, name="Apple", weight=100, calories=52, proteins=0.3, fats=0.2, carbohydrates=14, description="", picture=b""
    )
    product2 = Product(
        id=2, name="Chicken Breast", weight=100, calories=165, proteins=31, fats=3.6, carbohydrates=0, description="", picture=b""
    )

    # Создаем объект приема пищи без meal_products
    meal = Meal(
        id=1,
        name="Lunch",
        weight=0,
        calories=0,
        proteins=0,
        fats=0,
        carbohydrates=0,
        recorded_at=date(2024, 2, 6),
        user_id=test_user.id
    )

    # Связь между продуктами и приемом пищи (разные веса)
    meal_product1 = MealProducts(meal_id=meal.id, product_id=product1.id, product_weight=150)  # 150 г яблока
    meal_product2 = MealProducts(meal_id=meal.id, product_id=product2.id, product_weight=200)  # 200 г куриной грудки

    # Теперь добавляем meal_products в meal
    meal.meal_products = [meal_product1, meal_product2]
    test_db.add(meal)
    test_db.add_all([meal_product1, meal_product2])
    test_db.add_all([product1, product2])
    await test_db.commit()
    await test_db.refresh(meal)

    # Пересчет характеристик приема пищи
    updated_meal = await recalculate_meal_nutrients(test_db, meal)

    # Проверяем ожидаемые значения
    assert updated_meal == MealRead(
        id=1,
        name="Lunch",
        weight=350,  # 150 + 200
        calories=408,  # (52 * 1.5) + (165 * 2)
        proteins=62.45,  # (0.3 * 1.5) + (31 * 2)
        fats=7.5,  # (0.2 * 1.5) + (3.6 * 2)
        carbohydrates=21.0,  # (14 * 1.5) + (0 * 2)
        recorded_at=date(2024, 2, 6),
        user_id=test_user.id,
        products=[
            ProductRead(
                id=1, name="Apple", weight=150, calories=78.0, proteins=0.45, fats=0.3, carbohydrates=21.0, description="", picture_path=""
            ),
            ProductRead(
                id=2, name="Chicken Breast", weight=200, calories=330.0, proteins=62.0, fats=7.2, carbohydrates=0.0, description="", picture_path=""
            )
        ]
    )

@pytest.mark.asyncio
async def test_recalculate_meal_nutrients_empty_meal(test_db: AsyncSession):
    test_user = User(
        login="testuser6",
        email="test6@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    # Пустой прием пищи (без продуктов)
    meal = Meal(
        id=2,
        name="Empty Meal",
        weight=0,
        calories=0,
        proteins=0,
        fats=0,
        carbohydrates=0,
        recorded_at=date(2024, 2, 6),
        user_id=test_user.id,
        meal_products=[]
    )
    test_db.add(meal)
    await test_db.commit()
    await test_db.refresh(meal)

    # Пересчет характеристик пустого приема пищи
    updated_meal = await recalculate_meal_nutrients(test_db, meal)

    # Проверяем, что все характеристики обнулились
    assert updated_meal == MealRead(
        id=2,
        name="Empty Meal",
        weight=0,
        calories=0.0,
        proteins=0.0,
        fats=0.0,
        carbohydrates=0.0,
        recorded_at=date(2024, 2, 6),
        user_id=test_user.id,
        products=[]
    )

@pytest.mark.asyncio
async def test_add_meal(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser6",
        email="test6@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    product1 = Product(
        name="Orange",
        weight=100,
        calories=43,
        proteins=0.9,
        fats=0.1,
        carbohydrates=10,
        is_public=True
    )
    product2 = Product(
        name="Milk",
        weight=100,
        calories=42,
        proteins=3.4,
        fats=1,
        carbohydrates=5,
        user_id=test_user.id,
        is_public=False
    )

    test_db.add_all([product1, product2])
    await test_db.commit()
    await test_db.refresh(product1)
    await test_db.refresh(product2)

    meal = MealCreate(
        name="Lunch",
        weight=0,
        calories=0,
        proteins=0,
        fats=0,
        carbohydrates=0,
        products=[
            MealProductsCreate(product_id=product1.id, product_weight=50),
            MealProductsCreate(product_id=product2.id, product_weight=30)
        ]
    )

    created_meal = await add_meal(test_db, meal, test_user.id)
    assert created_meal is not None
    assert len(created_meal.products) == 2
    assert created_meal.name == meal.name
    assert created_meal.products[0].weight == meal.products[0].product_weight

@pytest.mark.asyncio
async def test_get_user_meals(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser14",
        email="test14@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    meal1 = Meal(
        name="breakfast",
        weight=100,
        calories=100,
        proteins=100,
        fats=100,
        carbohydrates=100,
        user_id=test_user.id,
    )

    meal2 = Meal(
        name="lunch",
        weight=100,
        calories=100,
        proteins=100,
        fats=100,
        carbohydrates=100,
        user_id=test_user.id,
    )
    test_db.add_all([meal1, meal2])
    await test_db.commit()
    await test_db.refresh(meal1)
    await test_db.refresh(meal2)

    await cache.delete(f"user_meals:{test_user.id}")

    meals = await get_user_meals(test_db, test_user.id)
    assert meals is not None
    assert len(meals) == 2
    assert meals[0].name == meal1.name
    assert meals[0].user_id == test_user.id
    assert meals[1].name == meal2.name
    assert meals[1].user_id == test_user.id

    cached_meals = await cache.get(f"user_meals:{test_user.id}")
    assert cached_meals is not None
    assert len(cached_meals) == 2
    assert cached_meals[0]["name"] == meal1.name
    assert cached_meals[0]["user_id"] == test_user.id
    assert cached_meals[1]["name"] == meal2.name
    assert cached_meals[1]["user_id"] == test_user.id

    meals_from_cache = await get_user_meals(test_db, test_user.id)
    assert meals_from_cache is not None
    assert len(meals_from_cache) == 2
    assert meals_from_cache[0].name == cached_meals[0]["name"]
    assert meals_from_cache[0].user_id == cached_meals[0]["user_id"]
    assert meals_from_cache[1].name == cached_meals[1]["name"]
    assert meals_from_cache[1].user_id == cached_meals[1]["user_id"]

@pytest.mark.asyncio
async def test_get_user_meals_with_products_by_date(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser14",
        email="test14@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    meal1 = Meal(
        name="breakfast",
        weight=100,
        calories=100,
        proteins=100,
        fats=100,
        carbohydrates=100,
        user_id=test_user.id,
    )

    meal2 = Meal(
        name="lunch",
        weight=100,
        calories=100,
        proteins=100,
        fats=100,
        carbohydrates=100,
        user_id=test_user.id,
    )
    test_db.add_all([meal1, meal2])
    await test_db.commit()
    await test_db.refresh(meal1)
    await test_db.refresh(meal2)

    await cache.delete(f"user_meals_products:{test_user.id}:{date.today()}")

    meals = await get_user_meals_with_products_by_date(test_db, test_user.id, str(date.today()))
    assert meals is not None
    assert len(meals) == 2
    assert meals[0].name == meal1.name

@pytest.mark.asyncio
async def test_get_meal_by_id(test_db: AsyncSession, test_cache):
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

    await cache.delete(f"user_meal:{test_user.id}:{meal.id}")

    meal_from_db = await get_meal_by_id(test_db, meal.id, test_user.id)
    assert meal_from_db is not None
    assert meal_from_db.name == meal.name

    cached_meal = await cache.get(f"user_meal:{test_user.id}:{meal.id}")
    assert cached_meal is not None
    assert cached_meal["name"] == meal.name

    meal_from_cache = await get_meal_by_id(test_db, meal.id, test_user.id)
    assert meal_from_cache is not None
    assert meal_from_db.name == meal_from_cache.name

@pytest.mark.asyncio
async def test_get_meals_by_date(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser14",
        email="test14@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    meal1 = Meal(
        name="breakfast",
        weight=100,
        calories=100,
        proteins=100,
        fats=100,
        carbohydrates=100,
        user_id=test_user.id,
    )

    meal2 = Meal(
        name="lunch",
        weight=100,
        calories=100,
        proteins=100,
        fats=100,
        carbohydrates=100,
        user_id=test_user.id,
    )
    test_db.add_all([meal1, meal2])
    await test_db.commit()
    await test_db.refresh(meal1)
    await test_db.refresh(meal2)

    await cache.delete(f"user_meals:{test_user.id}:{date.today()}")

    meals_from_db = await get_meals_by_date(test_db, test_user.id, str(date.today()))
    assert meals_from_db is not None
    assert len(meals_from_db) == 2
    assert meals_from_db[0].name == meal1.name
    assert meals_from_db[0].recorded_at == meal1.recorded_at
    assert meals_from_db[1].name == meal2.name
    assert meals_from_db[1].recorded_at == meal2.recorded_at

    cached_meals = await cache.get(f"user_meals:{test_user.id}:{date.today()}")
    assert cached_meals is not None
    assert len(cached_meals) == 2
    assert cached_meals[0]["name"] == meal1.name
    assert cached_meals[0]["recorded_at"] == meal1.recorded_at
    assert cached_meals[1]["name"] == meal2.name
    assert cached_meals[1]["recorded_at"] == meal2.recorded_at

    meals_from_cache = await get_meals_by_date(test_db, test_user.id, str(date.today()))
    assert meals_from_cache is not None
    assert len(meals_from_cache) == 2
    assert meals_from_cache[0].name == meals_from_db[0].name
    assert meals_from_cache[0].recorded_at == meals_from_db[0].recorded_at
    assert meals_from_cache[1].name == meals_from_db[1].name
    assert meals_from_cache[1].recorded_at == meals_from_db[1].recorded_at

@pytest.mark.asyncio
async def test_get_meals_last_7_days(test_db: AsyncSession, test_cache):
    test_user = User(
        login="testuser14",
        email="test14@example.com",
        hashed_password="testpassword"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)

    meal1 = Meal(
        name="breakfast",
        weight=100,
        calories=100,
        proteins=100,
        fats=100,
        carbohydrates=100,
        user_id=test_user.id,
    )

    meal2 = Meal(
        name="lunch",
        weight=100,
        calories=100,
        proteins=100,
        fats=100,
        carbohydrates=100,
        user_id=test_user.id,
        recorded_at=date.today() - timedelta(days=1)
    )
    test_db.add_all([meal1, meal2])
    await test_db.commit()
    await test_db.refresh(meal1)
    await test_db.refresh(meal2)
    print(meal2.recorded_at)

    await cache.delete(f"user_meals_history:{test_user.id}")

    meals_from_db = await get_meals_last_7_days(test_db, test_user.id)
    assert meals_from_db is not None
    assert len(meals_from_db) == 2
    assert meals_from_db[0].name == meal1.name
    assert meals_from_db[0].recorded_at == meal1.recorded_at
    assert meals_from_db[1].name == meal2.name
    assert meals_from_db[1].recorded_at == meal2.recorded_at

    cached_meals = await cache.get(f"user_meals_history:{test_user.id}")
    assert cached_meals is not None
    assert len(cached_meals) == 2
    assert cached_meals[0]["name"] == meal1.name
    assert cached_meals[0]["recorded_at"] == meal1.recorded_at
    assert cached_meals[1]["name"] == meal2.name
    assert cached_meals[1]["recorded_at"] == meal2.recorded_at

    meals_from_cache = await get_meals_last_7_days(test_db, test_user.id)
    assert meals_from_cache is not None
    assert len(meals_from_cache) == 2
    assert meals_from_cache[0].name == meals_from_db[0].name
    assert meals_from_cache[0].recorded_at == meals_from_db[0].recorded_at
    assert meals_from_cache[1].name == meals_from_db[1].name
    assert meals_from_cache[1].recorded_at == meals_from_db[1].recorded_at

@pytest.mark.asyncio
async def test_update_meal(test_db: AsyncSession, test_cache):
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

    meal_update = MealUpdate(
        name="Lunch",
        weight=0,
        calories=0,
        proteins=0,
        fats=0,
        carbohydrates=0,
        products=[
            MealProductsUpdate(product_id=product.id, product_weight=50),
        ]
    )

    updated_meal = await update_meal(test_db, meal_update, meal.id, test_user.id)
    assert updated_meal is not None
    assert updated_meal.name == meal_update.name
    assert updated_meal.calories == 21.5
    assert updated_meal.proteins == 0.45
    assert updated_meal.fats == 0.05
    assert updated_meal.carbohydrates == 5.0
    assert updated_meal.user_id == test_user.id

@pytest.mark.asyncio
async def test_delete_meal(test_db: AsyncSession, test_cache):
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

    result = await delete_meal(test_db, meal.id, test_user.id)
    assert result["message"] == "Meal and its products deleted successfully"
