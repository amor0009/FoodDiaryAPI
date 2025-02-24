from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.database import get_async_session
from src.schemas.meal_products import MealProductsRead, MealProductsCreate, MealProductsUpdate
from src.services.meal_products_service import (
    get_meal_products,
    add_meal_product,
    update_meal_product,
    delete_meal_product
)

meal_products_router = APIRouter()

@meal_products_router.get("/{meal_id}")
async def get_all_meal_products(
    meal_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    return await get_meal_products(db, meal_id)

@meal_products_router.post("/{meal_id}")
async def add_meal_product(
    meal_id: int,
    data: MealProductsCreate,
    db: AsyncSession = Depends(get_async_session),
):
    return await add_meal_product(db, meal_id, data)

@meal_products_router.put("/{meal_id}")
async def update(
    meal_id: int,
    data: MealProductsUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    updated = await update_meal_product(db, meal_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Meal product not found")
    return updated

@meal_products_router.delete("/{meal_id}/{product_id}")
async def delete(
    meal_id: int,
    product_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    success = await delete_meal_product(db, meal_id, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Meal product not found")
    return {"message": "Meal product deleted successfully"}
