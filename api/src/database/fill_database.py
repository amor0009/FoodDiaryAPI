import io
import json
import os
from datetime import datetime
from pathlib import Path
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from api.src.models.base import generate_uuid
from api.src.models.product import Product
from api.logging_config import logger


# Функция для преобразования изображения в бинарный формат
async def image_to_binary(image_path: str) -> bytes:
    try:
        logger.info(f"Loading image from: {image_path}")

        # Проверка существования файла
        if not Path(image_path).exists():
            logger.error(f"File does not exist: {image_path}")
            return None

        # Проверка доступности файла
        if not os.access(image_path, os.R_OK):
            logger.error(f"No read permissions for: {image_path}")
            return None

        # Открытие изображения
        with Image.open(image_path) as img:
            logger.info(f"Image opened successfully. Format: {img.format}, Mode: {img.mode}")

            # Конвертация в bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            img_bytes = img_byte_arr.getvalue()

            if not img_bytes:
                logger.error("Converted image is empty!")
                return None

            logger.info(f"Image converted successfully. Size: {len(img_bytes)} bytes")
            return img_bytes

    except Exception as e:
        logger.error(f"Error in image_to_binary: {str(e)}", exc_info=True)
        return None


# Загрузка продуктов из JSON-файла и добавление их в базу данных
async def load_products_from_json(db: AsyncSession, file_path: str):
    try:
        filepath = Path(file_path)
        if not filepath.exists():
            logger.error(f"File not found: {file_path}")
            return

        # Открываем и загружаем данные из JSON-файла
        with open(file_path, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
            logger.info(f"Successfully loaded products from {file_path}")

        loaded_count = 0
        skipped_count = 0

        for product_data in products_data:
            try:
                # Проверяем, существует ли уже продукт с таким названием или slug
                from sqlalchemy import select
                stmt = select(Product).where(
                    (Product.name == product_data["name"]) |
                    (Product.slug == product_data["slug"])
                )
                result = await db.execute(stmt)
                existing_product = result.scalar_one_or_none()

                if existing_product:
                    logger.info(f"Product '{product_data['name']}' already exists, skipping")
                    skipped_count += 1
                    continue

                # Создаем объект Product из данных
                product = Product(
                    id=generate_uuid(),
                    name=product_data["name"],
                    slug=product_data["slug"],
                    weight=product_data["weight"],
                    calories=product_data["calories"],
                    proteins=product_data["proteins"],
                    fats=product_data["fats"],
                    carbohydrates=product_data["carbohydrates"],
                    description=product_data["description"],
                    is_public=product_data["is_public"],
                    user_id=product_data["user_id"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()  # Добавлено поле updated_at
                )
                db.add(product)
                loaded_count += 1
                logger.info(f"Added product: {product_data['name']}")

            except Exception as e:
                logger.error(f"Error processing product '{product_data.get('name', 'Unknown')}': {e}")
                skipped_count += 1
                continue

        # Применяем изменения в базу данных
        await db.commit()
        logger.info(f"Products successfully added to the database. Loaded: {loaded_count}, Skipped: {skipped_count}")

    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from the file: {e}")
    except Exception as e:
        # Откатываем транзакцию в случае ошибки
        await db.rollback()
        logger.error(f"Error committing to database: {e}")


# Заполнение базы данных продуктами из JSON-файла
async def fill_database(db: AsyncSession, file_path: str):
    await load_products_from_json(db, file_path)


# Функция для обновления существующих продуктов (добавление slug)
async def add_slugs_to_existing_products(db: AsyncSession):
    """Добавляет slug к существующим продуктам, у которых его нет"""
    try:
        from sqlalchemy import select
        from api.src.utils.common import generate_unique_slug

        stmt = select(Product).where(Product.slug == None)
        result = await db.execute(stmt)
        products_without_slug = result.scalars().all()

        logger.info(f"Found {len(products_without_slug)} products without slug")

        updated_count = 0
        for product in products_without_slug:
            try:
                # Генерируем уникальный slug
                slug = await generate_unique_slug(db, product.name, Product, exclude_id=product.id)
                product.slug = slug
                product.updated_at = datetime.utcnow()  # Обновляем updated_at
                updated_count += 1
                logger.info(f"Added slug '{slug}' for product '{product.name}'")

            except Exception as e:
                logger.error(f"Error adding slug for product '{product.name}': {e}")

        await db.commit()
        logger.info(f"Successfully added slugs to {updated_count} products")

    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating products with slugs: {e}")
