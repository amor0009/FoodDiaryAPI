from datetime import datetime, timedelta
from celery_config import celery
from sqlalchemy import delete
from src.database.database import get_async_session
from src.models.user_weight import UserWeight
from src.models.meal_products import MealProducts

# Задача для удаления старых записей user_weight (старше 30 дней)
@celery.task
async def delete_old_user_weights():
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    async with get_async_session() as db:
        await db.execute(delete(UserWeight).where(UserWeight.recorded_at < thirty_days_ago))
        await db.commit()

# Задача для удаления старых записей meal_products (старше 7 дней)
@celery.task
async def delete_old_meal_products():
    seven_days_ago = datetime.now().date() - timedelta(days=7)
    async with get_async_session() as db:
        await db.execute(delete(MealProducts).where(MealProducts.meal.recorded_at < seven_days_ago))
        await db.commit()
