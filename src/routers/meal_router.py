from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import get_current_user
from src.database.database import get_async_session
from src.models.user import User
from src.schemas.meal import MealUpdate, MealCreate
from src.services.meal_products_service import get_meal_products
from src.services.meal_service import get_user_meals, get_meal_by_id, get_meals_by_date, \
    get_meals_last_7_days, update_meal, delete_meal, add_meal, get_user_meals_with_products_by_date

meal_router = APIRouter()

@meal_router.post("/add")
async def add(meal: MealCreate, current_user: User = Depends(get_current_user),
              db: AsyncSession = Depends(get_async_session)):
    return await add_meal(db, meal, current_user.id)

@meal_router.get("/all_meals")
async def get_meals(db: AsyncSession = Depends(get_async_session),
                          current_user: User = Depends(get_current_user)):
    return await get_user_meals(db, current_user.id)

@meal_router.get("/meals_products/{meal_id}")
async def get_products(meal_id: int, db: AsyncSession = Depends(get_async_session)):
    return await get_meal_products(db, meal_id)

@meal_router.get("/user_meals_with_products/info/{target_date}")
async def get_users_meals_with_products(target_date: str, db: AsyncSession = Depends(get_async_session),
                                        current_user: User = Depends(get_current_user)):
    return await get_user_meals_with_products_by_date(db, current_user.id, target_date)

@meal_router.get("/id/{meal_id}")
async def find_by_id(meal_id: int, current_user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_async_session)):
    return await get_meal_by_id(db, meal_id, current_user.id)

@meal_router.get("/date/{target_date}")
async def find_by_date(target_date: str, current_user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_async_session)):
    return await get_meals_by_date(db, current_user.id, target_date)

@meal_router.get("/history")
async def find_meal_history(current_user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_async_session)):
    return await get_meals_last_7_days(db, current_user.id)

@meal_router.put("/{meal_id}")
async def update(meal_update: MealUpdate, meal_id: int, current_user: User = Depends(get_current_user),
                 db: AsyncSession = Depends(get_async_session)):
    return await update_meal(db, meal_update, meal_id, current_user.id)

@meal_router.delete("/{meal_id}")
async def delete(meal_id: int, current_user: User = Depends(get_current_user),
                 db: AsyncSession = Depends(get_async_session)):
    return await delete_meal(db, meal_id, current_user.id)
