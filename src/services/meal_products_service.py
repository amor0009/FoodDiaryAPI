from sqlalchemy import and_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound
from src.models.meal_products import MealProducts
from src.schemas.meal_products import MealProductsCreate, MealProductsUpdate


async def get_meal_products(db: AsyncSession, meal_id: int):
    query = select(MealProducts).where(MealProducts.meal_id == meal_id)
    result = await db.execute(query)
    meal_products = result.scalars().all()
    return meal_products


async def add_meal_product(db: AsyncSession, meal_id: int, data: MealProductsCreate):
    meal_product = MealProducts(
        meal_id=meal_id,
        product_id=data.product_id,
        product_weight=data.product_weight
    )
    db.add(meal_product)
    await db.commit()
    await db.refresh(meal_product)
    return meal_product


async def update_meal_product(db: AsyncSession, meal_id: int, data: MealProductsUpdate):
    query = select(MealProducts).where(
        MealProducts.meal_id == meal_id, MealProducts.product_id == data.product_id
    )
    result = await db.execute(query)

    try:
        meal_product = result.scalars().one()
        meal_product.product_weight = data.product_weight
        await db.commit()
        await db.refresh(meal_product)
        return meal_product
    except NoResultFound:
        return None


async def delete_meal_product(db: AsyncSession, meal_id: int, product_id: int):
    query = select(MealProducts).where(and_(
        MealProducts.meal_id == meal_id, MealProducts.product_id == product_id
    ))
    result = await db.execute(query)

    try:
        meal_product = result.scalars().one()
        await db.delete(meal_product)
        await db.commit()
        return True
    except NoResultFound:
        return False
