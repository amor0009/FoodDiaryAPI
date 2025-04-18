from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import Security
from src.database.database import get_async_session
from src.logging_config import logger
from src.models.user import User
from src.schemas.meal_products import MealProductsCreate, MealProductsUpdate
from src.services.meal_products_service import MealProductsService


meal_products_router = APIRouter(tags=["Meal_Products"])


# Эндпоинт для получения всех продуктов для конкретного блюда
@meal_products_router.get("/{meal_id}")
async def get_all_meal_products(
    meal_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(Security.get_current_user)
):
    logger.info(f"Fetching all meal products for meal_id {meal_id}")
    return await MealProductsService.get_meal_products(db, meal_id)


# Эндпоинт для добавления нового продукта в конкретное блюдо
@meal_products_router.post("/{meal_id}")
async def add_meal_product(
    meal_id: int,
    data: MealProductsCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(Security.get_current_user)
):
    logger.info(f"Adding new meal product for meal_id {meal_id}")
    return await MealProductsService.add_meal_product(db, meal_id, data)


# Эндпоинт для обновления продукта в конкретном блюде
@meal_products_router.put("/{meal_id}")
async def update(
    meal_id: int,
    data: MealProductsUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(Security.get_current_user)
):
    updated = await MealProductsService.update_meal_product(db, meal_id, data)
    if not updated:
        logger.warning(f"Meal product not found for meal_id {meal_id}")
        raise HTTPException(status_code=404, detail="Meal product not found")
    logger.info(f"Meal product for meal_id {meal_id} updated successfully")
    return updated


# Эндпоинт для удаления продукта из конкретного блюда
@meal_products_router.delete("/{meal_id}/{product_id}")
async def delete(
    meal_id: int,
    product_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(Security.get_current_user)
):
    success = await MealProductsService.delete_meal_product(db, meal_id, product_id)
    if not success:
        logger.warning(f"Meal product not found for meal_id {meal_id} and product_id {product_id}")
        raise HTTPException(status_code=404, detail="Meal product not found")
    logger.info(f"Meal product for meal_id {meal_id} and product_id {product_id} deleted successfully")
    return {"message": "Meal product deleted successfully"}
