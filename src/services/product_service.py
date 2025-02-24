from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.meal import Meal
from src.models.meal_products import MealProducts
from src.models.product import Product
from src.schemas.meal import MealRead
from src.schemas.product import ProductCreate, ProductUpdate, ProductAdd, ProductRead
from src.cache.cache import cache

async def recalculate_product_nutrients(db_product: Product, product_weight: float) -> ProductRead:
    """Пересчитывает характеристики продукта по заданному весу."""
    factor = product_weight / 100
    return ProductRead(
        id=db_product.id,
        name=db_product.name,
        weight=product_weight,
        calories=round(db_product.calories * factor, 2),
        proteins=round(db_product.proteins * factor, 2),
        fats=round(db_product.fats * factor, 2),
        carbohydrates=round(db_product.carbohydrates * factor, 2),
        description=db_product.description,
        picture_path=db_product.picture_path
    )

async def get_products(db: AsyncSession, user_id: int):
    cache_key = f"products:{user_id}"
    cached_products = await cache.get(cache_key)
    if cached_products:
        return [ProductRead.model_validate(product) for product in cached_products]

    query = select(Product).where(
        or_((Product.is_public == True), (Product.user_id == user_id))
    )
    result = await db.execute(query)
    products = result.scalars().all()
    products_list = [ProductRead.model_validate(product) for product in products]
    await cache.set(cache_key, [product.model_dump(mode="json") for product in products_list], expire=3600)
    return products_list

async def add_product(db: AsyncSession, product: ProductCreate, user_id: int):
    db_product = await get_product_by_exact_name(db, product.name, user_id)
    if db_product:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product {product.name} already exists",
        )

    new_product = Product(
        name=product.name,
        weight=product.weight,
        calories=product.calories,
        proteins=product.proteins,
        fats=product.fats,
        carbohydrates=product.carbohydrates,
        is_public=False,
        user_id=user_id
    )
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    cache_key = f"products:{user_id}"
    await cache.delete(cache_key)
    return ProductRead.model_validate(new_product)

async def change_product_info_for_weight(db: AsyncSession, product: ProductAdd, user_id: int):
    db_product = await get_product_by_exact_name(db, product.name, user_id)
    if not db_product:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    changed_product = Product(
        id=db_product.id,
        name=product.name,
        weight=product.weight,
        calories=(product.weight * db_product.calories) / db_product.weight,
        proteins=(product.weight * db_product.proteins) / db_product.weight,
        fats=(product.weight * db_product.fats) / db_product.weight,
        carbohydrates=(product.weight * db_product.carbohydrates) / db_product.weight,
        description=db_product.description,
        picture_path=db_product.picture_path,
        user_id=user_id
    )
    return ProductRead.model_validate(changed_product)

async def add_product_to_meal(db:AsyncSession, meal_id: int, product: ProductAdd, user_id: int):
    query = select(Meal).where(Meal.id == meal_id)
    result = await db.execute(query)
    meal = result.scalar_one_or_none()
    if not meal:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )
    added_product = await change_product_info_for_weight(db, product, user_id)
    meal.weight += added_product.weight
    meal.calories += added_product.calories
    meal.proteins += added_product.proteins
    meal.fats += added_product.fats
    meal.carbohydrates += added_product.carbohydrates

    meal_product = MealProducts(
        meal_id=meal_id,
        product_id=added_product.id,
        product_weight=added_product.weight
    )

    db.add(meal_product)
    await db.commit()
    await db.refresh(meal)
    return MealRead.model_validate(meal)

async def get_available_products(db: AsyncSession, user_id: int):
    cache_key = f"products:{user_id}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return [ProductRead.model_validate(product) for product in cached_data]

    query = select(Product).where(or_((Product.is_public == True), (Product.user_id == user_id)))
    result = await db.execute(query)
    products = result.scalars().all()
    products_list = [ProductRead.model_validate(product) for product in products]
    await cache.set(cache_key, [product.model_dump(mode="json") for product in products_list], expire=3600)
    return products_list

async def get_products_by_name(db: AsyncSession, product_name: str, user_id: int):
    cache_key = f"products:{user_id}:{product_name}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return [ProductRead.model_validate(product) for product in cached_data]

    query = select(Product).where(or_((Product.is_public == True), (Product.user_id == user_id)),
                                    Product.name.ilike(f"%{product_name}%"))
    result = await db.execute(query)
    products = result.scalars().all()
    products_list = [ProductRead.model_validate(product) for product in products]
    await cache.set(cache_key, [product.model_dump(mode="json") for product in products_list], expire=3600)
    return products_list

async def get_product_by_exact_name(db: AsyncSession, product_name: str, user_id: int):
    cache_key = f"product:{user_id}:{product_name}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return ProductRead.model_validate(cached_data)

    query = select(Product).where(and_(or_((Product.is_public == True), (Product.user_id == user_id)),
                                      (Product.name == product_name)))
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if product:
        product_pydantic = ProductRead.model_validate(product)
        await cache.set(cache_key, product_pydantic.model_dump(mode="json"), expire=3600)
        return product_pydantic
    return None

async def get_product_by_id(db: AsyncSession, product_id: int, user_id: int):
    cache_key = f"products:{user_id}:{product_id}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return ProductRead.model_validate(cached_data)

    query = select(Product).where(and_(
        (Product.id == product_id),
        or_((Product.is_public == True), (Product.user_id == user_id)))
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if product:
        product_pydantic = ProductRead.model_validate(product)
        await cache.set(cache_key, product_pydantic.model_dump(mode="json"), expire=3600)
        return product_pydantic
    return None

async def get_product_available_to_change_by_id(db: AsyncSession, product_id: int, user_id: int):
    cache_key = f"personal_product:{user_id}:{product_id}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return ProductRead.model_validate(cached_data)

    query = select(Product).where(
        or_((Product.id == product_id),
        and_((Product.is_public == False), (Product.user_id == user_id)))
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if product:
        product_pydantic = ProductRead.model_validate(product)
        await cache.set(cache_key, product_pydantic.model_dump(mode="json"), expire=3600)
        return product
    return None

async def get_product_available_to_change_by_name(db: AsyncSession, product_name: str, user_id: int):
    cache_key = f"personal_product:{user_id}:{product_name}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return ProductRead.model_validate(cached_data)

    query = select(Product).where(
        and_((Product.name == product_name),
        and_((Product.is_public == False), (Product.user_id == user_id)))
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    product_pydantic = ProductRead.model_validate(product)
    await cache.set(cache_key, product_pydantic.model_dump(mode="json"), expire=3600)
    return product_pydantic

async def update_product(db: AsyncSession, product_update: ProductUpdate, user_id: int):
    db_product = await get_product_available_to_change_by_id(db, product_update.id, user_id)
    if db_product is not None:
        if product_update.name is not None:
            db_product.name = product_update.name
        if product_update.weight is not None:
            db_product.weight = product_update.weight
        if product_update.calories is not None:
            db_product.calories = product_update.calories
        if product_update.proteins is not None:
            db_product.proteins = product_update.proteins
        if product_update.fats is not None:
            db_product.fats = product_update.fats
        if product_update.carbohydrates is not None:
            db_product.carbohydrates = product_update.carbohydrates
        if product_update.description is not None:
            db_product.description = product_update.description
        if product_update.picture_path is not None:
            db_product.picture_path = product_update.picture_path
    else:
        HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=""
        )
    await db.commit()
    await db.refresh(db_product)
    await cache.delete(f"products:{user_id}")
    await cache.delete(f"personal_product:{user_id}:{db_product.id}")
    await cache.delete(f"personal_product:{user_id}:{db_product.name}")
    await cache.delete(f"products:{user_id}:{db_product.id}")
    await cache.delete(f"products:{user_id}:{db_product.name}")
    return ProductRead.model_validate(db_product)

async def searching_products(db: AsyncSession, user_id: int, query: str):
    if not query:
        return await get_products(db, user_id)

    formatted_query = query.capitalize()
    query = select(Product).where(
        or_((Product.is_public == True), (Product.user_id == user_id)),
        Product.name.ilike(f"{formatted_query}%")
    )
    result = await db.execute(query)
    products = result.scalars().all()
    return [ProductRead.model_validate(product) for product in products]

async def delete_product(db: AsyncSession, user_id: int, product_id: int):
    product = await get_product_available_to_change_by_id(db, product_id, user_id)
    if product is not None:
        await db.delete(product)
        await db.commit()
        await cache.delete(f"products:{user_id}")
        await cache.delete(f"personal_product:{user_id}:{product.id}")
        await cache.delete(f"personal_product:{user_id}:{product.name}")
        await cache.delete(f"products:{user_id}:{product.id}")
        await cache.delete(f"products:{user_id}:{product.name}")
        await cache.delete(f"product:{user_id}:{product.name}")

        return ProductRead.model_validate(product)
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=""
    )
