import io
import json
from pathlib import Path
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.product import Product  # Импортируй модель Product
from src.logging_config import logger  # Импортируй логгер

# Функция для преобразования изображения в бинарный формат
async def image_to_binary(image_path: str) -> bytes:
    try:
        logger.info(f"Loading image from: {image_path}")
        with Image.open(image_path) as img:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')  # Используем JPEG, так как у тебя .jpg
            return img_byte_arr.getvalue()
    except FileNotFoundError:
        logger.error(f"Image file not found: {image_path}")
        return None
    except Exception as e:
        logger.error(f"Error processing image {image_path}: {e}")
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

        for product_data in products_data:
            # Получаем относительный путь к изображению
            relative_picture_path = product_data.get("picture_path")
            picture = None

            if relative_picture_path:
                # Преобразуем относительный путь в абсолютный
                base_dir = Path(__file__).parent  # Директория, где находится fill_database.py
                absolute_picture_path = (base_dir / relative_picture_path).resolve()

                # Преобразуем изображение в бинарный формат
                picture = await image_to_binary(absolute_picture_path)

            # Создаем объект Product из данных
            product = Product(
                name=product_data["name"],
                weight=product_data["weight"],
                calories=product_data["calories"],
                proteins=product_data["proteins"],
                fats=product_data["fats"],
                carbohydrates=product_data["carbohydrates"],
                description=product_data["description"],
                picture=picture,  # Сохраняем бинарные данные изображения
                is_public=product_data["is_public"],
                user_id=product_data["user_id"]
            )
            db.add(product)

        # Применяем изменения в базу данных
        await db.commit()
        logger.info("Products successfully added to the database.")

    except json.JSONDecodeError:
        logger.error("Error decoding JSON from the file.")
    except Exception as e:
        # Откатываем транзакцию в случае ошибки
        await db.rollback()
        logger.error(f"Error committing to database: {e}")

# Заполнение базы данных продуктами из JSON-файла
async def fill_database(db: AsyncSession, file_path: str):
    await load_products_from_json(db, file_path)