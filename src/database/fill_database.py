import json
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.product import Product


async def load_products_from_json(db: AsyncSession, file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return
    except json.JSONDecodeError:
        print("Error decoding JSON from the file.")
        return

    for product_data in products_data:
        product = Product(
            name=product_data["name"],
            weight=product_data["weight"],
            calories=product_data["calories"],
            proteins=product_data["proteins"],
            fats=product_data["fats"],
            carbohydrates=product_data["carbohydrates"],
            description=product_data["description"],
            picture_path=product_data["picture_path"],
            is_public=product_data["is_public"],
            user_id=product_data["user_id"]
        )
        db.add(product)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        print(f"Error committing to database: {e}")


async def fill_database(db: AsyncSession, file_path: str):
    await load_products_from_json(db, file_path)
