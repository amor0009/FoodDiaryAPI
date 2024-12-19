from datetime import date, timedelta, datetime
from fastapi import HTTPException, status
from sqlalchemy import select, and_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from src.models.meal import Meal
from src.models.meal_products import MealProducts
from src.schemas.meal import MealCreate, MealUpdate
from src.services.meal_products_service import add_meal_product, update_meal_product, delete_meal_product


async def add_meal(db: AsyncSession, meal: MealCreate, user_id: int):
    # Открываем транзакцию для добавления данных
    try:
        # Создаем запись о приёме пищи
        db_meal = Meal(
            name=meal.name,
            weight=meal.weight,
            calories=meal.calories,
            proteins=meal.proteins,
            fats=meal.fats,
            carbohydrates=meal.carbohydrates,
            user_id=user_id
        )
        db.add(db_meal)
        await db.flush()  # Промежуточный коммит, чтобы получить id блюда

        # Создание записей в meal_products для каждого продукта в meal.products
        if meal.products:
            for product in meal.products:
                meal_product = MealProducts(
                    meal_id=db_meal.id,
                    product_id=product.product_id,  # Предположим, что у вас есть product_id в MealProductsCreate
                    product_weight=product.product_weight  # Предположим, что у вас есть product_weight в MealProductsCreate
                )
                db.add(meal_product)

        # Завершаем транзакцию
        await db.commit()
        await db.refresh(db_meal)
        return db_meal

    except IntegrityError:
        # Откатываем изменения в случае ошибки
        await db.rollback()
        raise ValueError("Failed to create meal or associated meal products.")


async def get_user_meals(db: AsyncSession, user_id: int):
    query = select(Meal).where(Meal.user_id == user_id)
    result = await db.execute(query)
    meals = result.scalars().all()
    return meals


async def get_meal_products(db: AsyncSession, meal_id: int):
    return await get_meal_products(db, meal_id)


async def get_user_meals_with_products_by_date(db: AsyncSession, user_id: int, target_date: str):
    current_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
    query = (
        select(Meal)
        .options(joinedload(Meal.meal_products).joinedload(MealProducts.product))  # Указываем атрибут класса
        .where(and_(Meal.user_id == user_id, Meal.recorded_at == current_date_obj))
    )

    result = await db.execute(query)
    meals = result.scalars().unique().all()  # Используем unique() для устранения дублирующихся записей
    formatted_meals = []
    for meal in meals:
        products = [
            {
                "id": meal_product.product.id,
                "name": meal_product.product.name,
                "weight": meal_product.product_weight,
                "calories": (meal_product.product.calories * meal_product.product_weight) / 100,
                "proteins": (meal_product.product.proteins * meal_product.product_weight) / 100,
                "fats": (meal_product.product.fats * meal_product.product_weight) / 100,
                "carbohydrates": (meal_product.product.carbohydrates * meal_product.product_weight) / 100,
                "description": meal_product.product.description,
                "picture_path": meal_product.product.picture_path
            }
            for meal_product in meal.meal_products
            if meal_product.product is not None
        ]
        formatted_meals.append({
            "id": meal.id,
            "name": meal.name,
            "weight": meal.weight,
            "calories": meal.calories,
            "proteins": meal.proteins,
            "fats": meal.fats,
            "carbohydrates": meal.carbohydrates,
            "date": meal.recorded_at,
            "user_id": meal.user_id,
            "products": products,
        })

    return formatted_meals


async def get_meal_by_id(db: AsyncSession, meal_id: int, user_id: int):
    query = select(Meal).where(and_(Meal.id == meal_id, Meal.user_id == user_id))
    result = await db.execute(query)
    meal = result.scalar_one_or_none()
    return meal


async def get_meals_by_date(db: AsyncSession, user_id: int, target_date: str):
    current_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
    query = select(Meal).where(and_(
        Meal.user_id == user_id,
        Meal.recorded_at == current_date_obj
    ))
    result = await db.execute(query)
    meals = result.scalars().all()
    return meals


async def get_meals_last_7_days(db: AsyncSession, user_id: int):
    seven_days_ago = date.today() - timedelta(days=7)
    query = select(Meal).where(and_(
        Meal.user_id == user_id,
        Meal.recorded_at >= seven_days_ago)
    ).order_by(Meal.recorded_at.desc())
    result = await db.execute(query)
    meals = result.scalars().all()
    return meals


async def update_meal(db: AsyncSession, meal_update: MealUpdate, meal_id: int, user_id: int):
    db_meal = await db.execute(
        select(Meal).options(joinedload(Meal.meal_products)).where(and_(Meal.id == meal_id, Meal.user_id == user_id))
    )
    db_meal = db_meal.unique().scalar_one_or_none()
    if not db_meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )

    # Обновление основных данных блюда
    if meal_update.name is not None:
        db_meal.name = meal_update.name
    if meal_update.weight is not None:
        db_meal.weight = meal_update.weight
    if meal_update.calories is not None:
        db_meal.calories = meal_update.calories
    if meal_update.proteins is not None:
        db_meal.proteins = meal_update.proteins
    if meal_update.fats is not None:
        db_meal.fats = meal_update.fats
    if meal_update.carbohydrates is not None:
        db_meal.carbohydrates = meal_update.carbohydrates

    # Обновление продуктов
    if meal_update.products is not None:
        existing_products = {mp.product_id: mp for mp in db_meal.meal_products}
        update_products = {p.product_id: p for p in meal_update.products}

        # Удаление старых продуктов
        for product_id in existing_products.keys() - update_products.keys():
            await delete_meal_product(db, meal_id, product_id)

        # Обновление или добавление новых продуктов
        for product_id, product_data in update_products.items():
            if product_id in existing_products:
                await update_meal_product(db, meal_id, product_data)
            else:
                new_meal_product = MealProducts(
                    meal_id=meal_id,
                    product_id=product_id,
                    product_weight=product_data.product_weight,
                )
                db.add(new_meal_product)

    await db.commit()
    await db.refresh(db_meal)
    return db_meal


async def delete_meal(db: AsyncSession, meal_id: int, user_id: int):
    db_meal = await get_meal_by_id(db, meal_id, user_id)
    if not db_meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )

    # Массовое удаление продуктов, связанных с приёмом пищи
    await db.execute(delete(MealProducts).where(MealProducts.meal_id == meal_id))

    # Удаление самого приёма пищи
    await db.delete(db_meal)
    await db.commit()
    return {"message": "Meal and its products deleted successfully"}

