import asyncio
from fastapi import HTTPException, status, UploadFile
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.logging_config import logger
from src.models.meal import Meal
from src.models.meal_products import MealProducts
from src.models.product import Product
from src.schemas.meal import MealRead
from src.schemas.product import ProductCreate, ProductUpdate, ProductAdd, ProductRead
from src.cache.cache import cache

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif"}

# Функция для пересчета характеристик продукта по заданному весу
async def recalculate_product_nutrients(db_product: Product, product_weight: float) -> ProductRead:
    factor = product_weight / 100
    logger.info(f"Recalculating product nutrients for product {db_product.name} with weight {product_weight}g")
    return ProductRead(
        id=db_product.id,
        name=db_product.name,
        weight=product_weight,
        calories=round(db_product.calories * factor, 2),
        proteins=round(db_product.proteins * factor, 2),
        fats=round(db_product.fats * factor, 2),
        carbohydrates=round(db_product.carbohydrates * factor, 2),
        description=db_product.description,
        picture_path=db_product.picture
    )

# Функция для получения всех продуктов пользователя
async def get_products(db: AsyncSession, user_id: int):
    cache_key = f"products:{user_id}"
    cached_products = await cache.get(cache_key)
    if cached_products:
        logger.info(f"Products for user {user_id} retrieved from cache")
        return [ProductRead.model_validate(product) for product in cached_products]

    logger.info(f"Fetching products for user {user_id} from database")
    query = select(Product).where(
        or_((Product.is_public == True), (Product.user_id == user_id))
    )
    result = await db.execute(query)
    products = result.scalars().all()
    logger.info(f"{len(products)} products found in database for user {user_id}")
    products_list = [ProductRead.model_validate(product) for product in products]
    await cache.set(cache_key, [product.model_dump(mode="json") for product in products_list], expire=3600)
    logger.info(f"Products for user {user_id} fetched from DB and cached")
    return products_list

# Функция для добавления нового продукта
async def add_product(db: AsyncSession, product: ProductCreate, user_id: int):
    db_product = await get_product_by_exact_name(db, product.name, user_id)
    if db_product:
        logger.warning(f"Product {product.name} already exists for user {user_id}")
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product {product.name} already exists",
        )

    logger.info(f"Adding new product {product.name} for user {user_id}")
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
    await asyncio.gather(
        cache.delete(f"products:{user_id}"),
        cache.delete(f"product_exact:{user_id}:{new_product.name}"),
        cache.delete(f"personal_product:{user_id}:{new_product.id}"),
        cache.delete(f"personal_product:{user_id}:{new_product.name}"),
        cache.delete(f"personal_products:{user_id}"),
        cache.delete(f"products:{user_id}:{new_product.id}"),
        cache.delete(f"products:{user_id}:{new_product.name}"),
        cache.delete(f"product:{user_id}:{new_product.name}")
    )
    logger.info(f"Product {product.name} added for user {user_id}")
    return ProductRead.model_validate(new_product)

# Функция для изменения информации о продукте в зависимости от веса
async def change_product_info_for_weight(db: AsyncSession, product: ProductAdd, user_id: int):
    db_product = await get_product_by_exact_name(db, product.name, user_id)
    if not db_product:
        logger.error(f"Product {product.name} not found for user {user_id}")
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    logger.info(f"Updating product {product.name} for user {user_id} based on new weight {product.weight}g")
    changed_product = Product(
        id=db_product.id,
        name=product.name,
        weight=product.weight,
        calories=(product.weight * db_product.calories) / db_product.weight,
        proteins=(product.weight * db_product.proteins) / db_product.weight,
        fats=(product.weight * db_product.fats) / db_product.weight,
        carbohydrates=(product.weight * db_product.carbohydrates) / db_product.weight,
        description=db_product.description,
        user_id=user_id
    )
    logger.info(f"Product {product.name} weight and nutrients updated for user {user_id}")
    return ProductRead.model_validate(changed_product)

# Функция для добавления продукта в приём пищи
async def add_product_to_meal(db: AsyncSession, meal_id: int, product: ProductAdd, user_id: int):
    query = select(Meal).where(Meal.id == meal_id)
    result = await db.execute(query)
    meal = result.scalar_one_or_none()
    if not meal:
        logger.error(f"Meal with ID {meal_id} not found for user {user_id}")
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )

    logger.info(f"Adding product {product.name} to meal {meal_id} for user {user_id}")
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
    await asyncio.gather(
        cache.delete(f"products:{user_id}"),
        cache.delete(f"product_exact:{user_id}:{product.name}"),
        cache.delete(f"personal_product:{user_id}:{added_product.id}"),
        cache.delete(f"personal_product:{user_id}:{product.name}"),
        cache.delete(f"personal_products:{user_id}"),
        cache.delete(f"products:{user_id}:{added_product.id}"),
        cache.delete(f"products:{user_id}:{product.name}"),
        cache.delete(f"product:{user_id}:{product.name}")
    )
    logger.info(f"Product {added_product.name} added to meal {meal_id} for user {user_id}")
    return MealRead.model_validate(meal)

# Функция для получения доступных продуктов для пользователя
async def get_personal_products(db: AsyncSession, user_id: int):
    cache_key = f"personal_products:{user_id}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info(f"Available products for user {user_id} retrieved from cache")
        return [ProductRead.model_validate(product) for product in cached_data]

    logger.info(f"Fetching available products for user {user_id} from database")
    query = select(Product).where(Product.user_id == user_id)
    result = await db.execute(query)
    products = result.scalars().all()
    logger.info(f"{len(products)} available products found in database for user {user_id}")
    products_list = [ProductRead.model_validate(product) for product in products]
    await cache.set(cache_key, [product.model_dump(mode="json") for product in products_list], expire=3600)
    logger.info(f"Available products for user {user_id} fetched from DB and cached")
    return products_list

# Функция для поиска продуктов по имени
async def get_products_by_name(db: AsyncSession, product_name: str, user_id: int):
    cache_key = f"products:{user_id}:{product_name}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info(f"Products for user {user_id} with name {product_name} retrieved from cache")
        return [ProductRead.model_validate(product) for product in cached_data]

    logger.info(f"Fetching products for user {user_id} with name {product_name} from database")
    query = select(Product).where(or_((Product.is_public == True), (Product.user_id == user_id)),
                                    Product.name.ilike(f"%{product_name}%"))
    result = await db.execute(query)
    products = result.scalars().all()
    logger.info(f"{len(products)} products found in database for user {user_id} with name {product_name}")
    products_list = [ProductRead.model_validate(product) for product in products]
    await cache.set(cache_key, [product.model_dump(mode="json") for product in products_list], expire=3600)
    logger.info(f"Products for user {user_id} with name {product_name} fetched from DB and cached")
    return products_list

# Функция для получения продукта по точному имени
async def get_product_by_exact_name(db: AsyncSession, product_name: str, user_id: int):
    cache_key = f"product_exact:{user_id}:{product_name}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info(f"Product {product_name} for user {user_id} retrieved from cache")
        return ProductRead.model_validate(cached_data)

    logger.info(f"Fetching product {product_name} for user {user_id} from database")
    query = select(Product).where(and_(or_((Product.is_public == True), (Product.user_id == user_id)),
                                      (Product.name == product_name)))
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if product:
        product_pydantic = ProductRead.model_validate(product)
        await cache.set(cache_key, product_pydantic.model_dump(mode="json"), expire=3600)
        logger.info(f"Product {product_name} for user {user_id} fetched from DB and cached")
        return product_pydantic
    logger.warning(f"Product {product_name} for user {user_id} not found in DB")
    return None

# Функция для получения продукта по ID для указанного пользователя.
async def get_product_by_id(db: AsyncSession, product_id: int, user_id: int):
    cache_key = f"product:{user_id}:{product_id}"

    # Проверяем, есть ли данные в кэше
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for product {product_id} for user {user_id}")
        return ProductRead.model_validate(cached_data)

    logger.info(f"Cache miss for product {product_id} for user {user_id}. Fetching from database.")

    # Запрос к базе данных для получения продукта по ID, с учетом публичности или принадлежности пользователю
    query = select(Product).where(and_(
        (Product.id == product_id),
        or_((Product.is_public == True), (Product.user_id == user_id)))
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if product:
        # Если продукт найден, сохраняем его в кэш и возвращаем
        product_pydantic = ProductRead.model_validate(product)
        await cache.set(cache_key, product_pydantic.model_dump(mode="json"), expire=3600)
        logger.info(f"Product {product_id} for user {user_id} fetched from database and cached.")
        return product_pydantic

    logger.warning(f"Product {product_id} not found for user {user_id}.")
    return None

# Функция для получения продукта по ID, доступного для изменения пользователем
async def get_product_available_to_change_by_id(db: AsyncSession, product_id: int, user_id: int):
    # Формируем запрос
    query = select(Product).where(
        and_(
            Product.id == product_id,  # Продукт должен иметь указанный ID
            or_(
                Product.is_public == False,  # Продукт не публичный
                Product.user_id == user_id  # Или продукт принадлежит пользователю
            )
        )
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if product:
        logger.info(f"Found product {product_id} for user {user_id}")
        return product
    return None

# Функция для получения продукта по имени, доступного для изменения пользователем
async def get_product_available_to_change_by_name(db: AsyncSession, product_name: str, user_id: int):
    cache_key = f"personal_product:{user_id}:{product_name}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info(f"Retrieved product {product_name} from cache for user {user_id}")
        return ProductRead.model_validate(cached_data)

    query = select(Product).where(
        and_((Product.name == product_name),
             and_((Product.is_public == False), (Product.user_id == user_id)))
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if product:
        product_pydantic = ProductRead.model_validate(product)
        await cache.set(cache_key, product_pydantic.model_dump(mode="json"), expire=3600)
        logger.info(f"Added product {product_name} to cache for user {user_id}")
        return product_pydantic
    return None

# Функция для обновления данных продукта, если он доступен пользователю
async def update_product(db: AsyncSession, product_update: ProductUpdate, user_id: int):
    db_product = await get_product_available_to_change_by_id(db, product_update.id, user_id)
    if db_product is None:
        logger.warning(f"Failed to find product {product_update.id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product not found or unavailable"
        )

    update_data = product_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)

    await db.commit()
    await db.refresh(db_product)
    logger.info(f"Updated product {product_update.id} for user {user_id}")

    await asyncio.gather(
        cache.delete(f"products:{user_id}"),
        cache.delete(f"product_exact:{user_id}:{product_update.name}"),
        cache.delete(f"personal_product:{user_id}:{product_update.id}"),
        cache.delete(f"personal_product:{user_id}:{product_update.name}"),
        cache.delete(f"personal_products:{user_id}"),
        cache.delete(f"products:{user_id}:{product_update.id}"),
        cache.delete(f"products:{user_id}:{product_update.name}"),
        cache.delete(f"product:{user_id}:{product_update.name}")
    )

    return ProductRead.model_validate(db_product)

# Функция для поиска продуктов по названию с учетом приватности
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
    logger.info(f"Found {len(products)} products for query '{formatted_query}' for user {user_id}")
    return [ProductRead.model_validate(product) for product in products]

# Функция для удаления продукта, если он доступен пользователю
async def delete_product(db: AsyncSession, user_id: int, product_id: int):
    product = await get_product_available_to_change_by_id(db, product_id, user_id)
    if product is None:
        logger.warning(f"Failed to find product {product_id} for deletion by user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    await db.delete(product)
    await db.commit()
    logger.info(f"Deleted product {product_id} for user {user_id}")

    await asyncio.gather(
        cache.delete(f"products:{user_id}"),
        cache.delete(f"product_exact:{user_id}:{product.name}"),
        cache.delete(f"personal_product:{user_id}:{product.id}"),
        cache.delete(f"personal_product:{user_id}:{product.name}"),
        cache.delete(f"personal_products:{user_id}"),
        cache.delete(f"products:{user_id}:{product.id}"),
        cache.delete(f"products:{user_id}:{product.name}"),
        cache.delete(f"product:{user_id}:{product.name}")
    )

    return ProductRead.model_validate(product)

# Функция для загрузки фотографии профиля пользователя
async def upload_product_picture(file: UploadFile, user_id: int, product_id: int, db: AsyncSession):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        logger.warning(f"Attempted to upload an unsupported image type: {file.content_type}")
        raise HTTPException(status_code=400, detail="Only images (JPEG, PNG, GIF) are allowed")

    product = await get_product_available_to_change_by_id(db, product_id, user_id)

    # Обновление фотографии профиля пользователя
    product.picture = await file.read()
    await db.commit()
    await db.refresh(product)
    logger.info(f"Picture updated for user's {user_id} product {product_id}")

    await asyncio.gather(
        cache.delete(f"products:{user_id}"),
        cache.delete(f"product_exact:{user_id}:{product.name}"),
        cache.delete(f"personal_product:{user_id}:{product.id}"),
        cache.delete(f"personal_product:{user_id}:{product.name}"),
        cache.delete(f"personal_products:{user_id}"),
        cache.delete(f"products:{user_id}:{product.id}"),
        cache.delete(f"products:{user_id}:{product.name}"),
        cache.delete(f"product:{user_id}:{product.name}")
    )

    return {"message": "Product picture updated"}

# Функция для получения фотографии профиля пользователя
async def get_product_picture(user_id: int, product_id: int, db: AsyncSession):
    product = await get_product_available_to_change_by_id(db, product_id, user_id)

    if not product or not product.picture:
        logger.warning(f"Picture is not found for user's {user_id} product {product_id}")
        raise HTTPException(status_code=404, detail="No picture found")

    logger.info(f"Picture retrieved for user's {user_id} product {product_id}")
    return product.picture