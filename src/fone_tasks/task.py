from datetime import datetime, timedelta
import asyncio
from celery_config import celery
from sqlalchemy import delete
from src.database.database import get_async_session
from src.logging_config import logger
from src.models.user_weight import UserWeight
from src.models.meal_products import MealProducts
from src.rabbitmq.client import rabbitmq_client
from src.rabbitmq.consumer import consume_messages

@celery.task(name="start_rabbitmq_consumer")
def start_rabbitmq_consumer(queue_name="registration_queue"):
    async def main():
        try:
            await rabbitmq_client.connect()
            logger.info("RabbitMQ connection established for consumer")
            await consume_messages(queue_name)
        except Exception as e:
            logger.error(f"Error starting RabbitMQ consumer: {e}")

    asyncio.run(main())

# Задача для удаления старых записей user_weight (старше 30 дней)
@celery.task
async def delete_old_user_weights():
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    async with get_async_session() as db:
        await db.execute(delete(UserWeight).where(UserWeight.recorded_at < thirty_days_ago))
        await db.commit()
        logger.info('Deleted old user weights (last 30 days)')

# Задача для удаления старых записей meal_products (старше 7 дней)
@celery.task
async def delete_old_meal_products():
    seven_days_ago = datetime.now().date() - timedelta(days=7)
    async with get_async_session() as db:
        await db.execute(delete(MealProducts).where(MealProducts.meal.recorded_at < seven_days_ago))
        await db.commit()
        logger.info('Deleted old meal products (last 7 days)')
