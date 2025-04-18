import asyncio
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import config
from src.logging_config import logger
from src.models.meal import Meal
from src.models.meal_products import MealProducts
from src.models.product import Product
from src.schemas.meal import MealRead
from src.schemas.product import ProductCreate, ProductUpdate, ProductAdd, ProductRead
from src.cache.cache import cache
from src.daos.product_dao import ProductDAO


class ProductService:

    # Функция для пересчета характеристик продукта по заданному весу
    @classmethod
    async def recalculate_product_nutrients(cls, db_product: Product, product_weight: float) -> ProductRead:
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
            has_picture=db_product.has_picture,
            picture=db_product.picture
        )

    # Функция для получения всех продуктов пользователя
    @classmethod
    async def get_products(cls, db: AsyncSession, user_id: int):
        cache_key = f"products:{user_id}"
        cached_products = await cache.get(cache_key)
        if cached_products:
            logger.info(f"Products for user {user_id} retrieved from cache")
            return [ProductRead.model_validate(product) for product in cached_products]

        logger.info(f"Fetching products for user {user_id} from database")
        products = await ProductDAO.get_user_products(db, user_id)

        logger.info(f"{len(products)} products found in database for user {user_id}")
        products_list = [ProductRead.model_validate(product) for product in products]
        await cache.set(cache_key, [product.model_dump(mode="json") for product in products_list], expire=3600)
        logger.info(f"Products for user {user_id} fetched from DB and cached")
        return products_list

    # Функция для добавления нового продукта
    @classmethod
    async def add_product(cls, db: AsyncSession, product: ProductCreate, user_id: int):
        db_product = await ProductDAO.get_by_name(db, product.name, user_id)
        if db_product:
            logger.warning(f"Product {product.name} already exists for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {product.name} already exists",
            )

        logger.info(f"Adding new product {product.name} for user {user_id}")
        product_data = {
            "name": product.name,
            "weight": product.weight,
            "calories": product.calories,
            "proteins": product.proteins,
            "fats": product.fats,
            "carbohydrates": product.carbohydrates,
            "is_public": False,
            "user_id": user_id
        }

        new_product = await ProductDAO.create_product(db, product_data)
        await cls._clear_product_cache(user_id, new_product)
        logger.info(f"Product {product.name} added for user {user_id}")
        return ProductRead.model_validate(new_product)

    # Функция для изменения информации о продукте в зависимости от веса
    @classmethod
    async def change_product_info_for_weight(cls, db: AsyncSession, product: ProductAdd, user_id: int):
        db_product = await ProductDAO.get_by_name(db, product.name, user_id)
        if not db_product:
            logger.error(f"Product {product.name} not found for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        logger.info(f"Updating product {product.name} for user {user_id} based on new weight {product.weight}g")
        return ProductRead(
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

    # Функция для добавления продукта в приём пищи
    @classmethod
    async def add_product_to_meal(cls, db: AsyncSession, meal_id: int, product: ProductAdd, user_id: int):
        meal = await db.get(Meal, meal_id)
        if not meal:
            logger.error(f"Meal with ID {meal_id} not found for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meal not found"
            )

        logger.info(f"Adding product {product.name} to meal {meal_id} for user {user_id}")
        added_product = await cls.change_product_info_for_weight(db, product, user_id)

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
        await cls._clear_product_cache(user_id, added_product)
        logger.info(f"Product {added_product.name} added to meal {meal_id} for user {user_id}")
        return MealRead.model_validate(meal)

    # Функция для получения доступных продуктов для пользователя
    @classmethod
    async def get_personal_products(cls, db: AsyncSession, user_id: int):
        cache_key = f"personal_products:{user_id}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Available products for user {user_id} retrieved from cache")
            return [ProductRead.model_validate(product) for product in cached_data]

        logger.info(f"Fetching available products for user {user_id} from database")
        products = await ProductDAO.get_personal_products(db, user_id)

        logger.info(f"{len(products)} available products found in database for user {user_id}")
        products_list = [ProductRead.model_validate(product) for product in products]
        await cache.set(cache_key, [product.model_dump(mode="json") for product in products_list], expire=3600)
        logger.info(f"Available products for user {user_id} fetched from DB and cached")
        return products_list

    # Функция для поиска продуктов по имени
    @classmethod
    async def get_products_by_name(cls, db: AsyncSession, product_name: str, user_id: int):
        cache_key = f"products:{user_id}:{product_name}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Products for user {user_id} with name {product_name} retrieved from cache")
            return [ProductRead.model_validate(product) for product in cached_data]

        logger.info(f"Fetching products for user {user_id} with name {product_name} from database")
        products = await ProductDAO.search_products(db, user_id, product_name)

        logger.info(f"{len(products)} products found in database for user {user_id} with name {product_name}")
        products_list = [ProductRead.model_validate(product) for product in products]
        await cache.set(cache_key, [product.model_dump(mode="json") for product in products_list], expire=3600)
        logger.info(f"Products for user {user_id} with name {product_name} fetched from DB and cached")
        return products_list

    # Функция для получения продукта по точному имени
    @classmethod
    async def get_product_by_exact_name(cls, db: AsyncSession, product_name: str, user_id: int):
        cache_key = f"product_exact:{user_id}:{product_name}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Product {product_name} for user {user_id} retrieved from cache")
            return ProductRead.model_validate(cached_data)

        logger.info(f"Fetching product {product_name} for user {user_id} from database")
        product = await ProductDAO.get_by_name(db, product_name, user_id)

        if product:
            product_pydantic = ProductRead.model_validate(product)
            await cache.set(cache_key, product_pydantic.model_dump(mode="json"), expire=3600)
            logger.info(f"Product {product_name} for user {user_id} fetched from DB and cached")
            return product_pydantic

        logger.warning(f"Product {product_name} for user {user_id} not found in DB")
        return None

    # Функция для получения продукта по ID для указанного пользователя
    @classmethod
    async def get_product_by_id(cls, db: AsyncSession, product_id: int, user_id: int):
        cache_key = f"product:{user_id}:{product_id}"

        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for product {product_id} for user {user_id}")
            return ProductRead.model_validate(cached_data)

        logger.info(f"Cache miss for product {product_id} for user {user_id}. Fetching from database.")
        product = await ProductDAO.get_by_id(db, product_id, user_id)

        if product:
            product_pydantic = ProductRead.model_validate(product)
            await cache.set(cache_key, product_pydantic.model_dump(mode="json"), expire=3600)
            logger.info(f"Product {product_id} for user {user_id} fetched from database and cached.")
            return product_pydantic

        logger.warning(f"Product {product_id} not found for user {user_id}.")
        return None

    # Функция для получения продукта по ID, доступного для изменения пользователем
    @classmethod
    async def get_product_available_to_change_by_id(cls, db: AsyncSession, product_id: int, user_id: int):
        product = await ProductDAO.get_editable_by_id(db, product_id, user_id)
        if product:
            logger.info(f"Found product {product_id} for user {user_id}")
            return product
        return None

    # Функция для получения продукта по имени, доступного для изменения пользователем
    @classmethod
    async def get_product_available_to_change_by_name(cls, db: AsyncSession, product_name: str, user_id: int):
        cache_key = f"personal_product:{user_id}:{product_name}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Retrieved product {product_name} from cache for user {user_id}")
            return ProductRead.model_validate(cached_data)

        product = await ProductDAO.get_editable_by_name(db, product_name, user_id)
        if product:
            product_pydantic = ProductRead.model_validate(product)
            await cache.set(cache_key, product_pydantic.model_dump(mode="json"), expire=3600)
            logger.info(f"Added product {product_name} to cache for user {user_id}")
            return product_pydantic
        return None

    # Функция для обновления данных продукта
    @classmethod
    async def update_product(cls, db: AsyncSession, product_update: ProductUpdate, user_id: int):
        db_product = await cls.get_product_available_to_change_by_id(db, product_update.id, user_id)
        if db_product is None:
            logger.warning(f"Failed to find product {product_update.id} for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product not found or unavailable"
            )

        update_data = product_update.model_dump(exclude_unset=True)
        updated_product = await ProductDAO.update_product(db, db_product, update_data)
        await cls._clear_product_cache(user_id, updated_product)
        logger.info(f"Updated product {product_update.id} for user {user_id}")
        return ProductRead.model_validate(updated_product)

    # Функция для поиска продуктов по названию с учетом приватности
    @classmethod
    async def searching_products(cls, db: AsyncSession, user_id: int, query: str):
        if not query:
            return await cls.get_products(db, user_id)

        products = await ProductDAO.search_products(db, user_id, query)
        logger.info(f"Found {len(products)} products for query '{query}' for user {user_id}")
        return [ProductRead.model_validate(product) for product in products]

    # Функция для удаления продукта
    @classmethod
    async def delete_product(cls, db: AsyncSession, user_id: int, product_id: int):
        product = await cls.get_product_available_to_change_by_id(db, product_id, user_id)
        if product is None:
            logger.warning(f"Failed to find product {product_id} for deletion by user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        deleted_product = await ProductDAO.delete_product(db, product)
        await cls._clear_product_cache(user_id, deleted_product)
        logger.info(f"Deleted product {product_id} for user {user_id}")
        return ProductRead.model_validate(deleted_product)

    # Функция для загрузки фотографии продукта
    @classmethod
    async def upload_product_picture(cls, file: UploadFile, user_id: int, product_id: int, db: AsyncSession):
        if file.content_type not in config.ALLOWED_IMAGE_TYPES:
            logger.warning(f"Attempted to upload an unsupported image type: {file.content_type}")
            raise HTTPException(status_code=400, detail="Only images (JPEG, PNG, GIF) are allowed")

        product = await cls.get_product_available_to_change_by_id(db, product_id, user_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product = await ProductDAO.update_product_picture(db, product, await file.read())
        await cls._clear_product_cache(user_id, product)
        logger.info(f"Picture updated for user's {user_id} product {product_id}")
        return {"message": "Product picture updated"}

    # Функция для получения фотографии продукта
    @classmethod
    async def get_product_picture(cls, user_id: int, product_id: int, db: AsyncSession):
        product = await db.get(Product, product_id)

        if not product or not product.picture:
            logger.warning(f"Picture is not found for user's {user_id} product {product_id}")
            raise HTTPException(status_code=404, detail="No picture found")

        logger.info(f"Picture retrieved for user's {user_id} product {product_id}")
        return product.picture

    # Внутренний метод для очистки кеша продукта
    @classmethod
    async def _clear_product_cache(cls, user_id: int, product: Product):
        keys = [
            f"products:{user_id}",
            f"product_exact:{user_id}:{product.name}",
            f"personal_product:{user_id}:{product.id}",
            f"personal_product:{user_id}:{product.name}",
            f"personal_products:{user_id}",
            f"products:{user_id}:{product.id}",
            f"products:{user_id}:{product.name}",
            f"product:{user_id}:{product.name}"
        ]
        await asyncio.gather(*(cache.delete(k) for k in keys))
        logger.info(f"Cleared product cache for user {user_id} and product {product.id}")
