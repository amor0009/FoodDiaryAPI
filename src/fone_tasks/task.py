from datetime import datetime, timedelta
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from celery_config import celery
from sqlalchemy import delete, select
from src.database.database import get_async_session
from src.logging_config import logger
from src.models.user_weight import UserWeight
from src.models.meal_products import MealProducts
from src.rabbitmq.client import rabbitmq_client
from src.rabbitmq.consumer import consume_messages
from celery.schedules import crontab

@celery.task(bind=True, name="start_rabbitmq_consumer")
def start_rabbitmq_consumer(self, queue_name="registration_queue"):
    async def main():
        try:
            await rabbitmq_client.connect()
            logger.info("RabbitMQ connection established for consumer")
            await consume_messages(queue_name)
        except Exception as e:
            logger.error(f"Error starting RabbitMQ consumer: {e}")
            self.retry(exc=e, countdown=60)  # Повторить через 60 секунд при ошибке

    asyncio.run(main())

@celery.task(bind=True)
async def delete_old_user_weights(self):
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    try:
        async with get_async_session() as db:
            await db.execute(delete(UserWeight).where(UserWeight.recorded_at < thirty_days_ago))
            await db.commit()
            logger.info('Deleted old user weights (last 30 days)')
    except Exception as e:
        logger.error(f"Error deleting old weights: {e}")
        self.retry(exc=e, countdown=300)  # Повторить через 5 минут

@celery.task(bind=True)
async def delete_old_meal_products(self):
    seven_days_ago = datetime.now().date() - timedelta(days=7)
    try:
        async with get_async_session() as db:
            await db.execute(delete(MealProducts).where(MealProducts.meal.recorded_at < seven_days_ago))
            await db.commit()
            logger.info('Deleted old meal products (last 7 days)')
    except Exception as e:
        logger.error(f"Error deleting old meals: {e}")
        self.retry(exc=e, countdown=300)

@celery.task(bind=True)
async def add_daily_weight_records(self):
    try:
        async with get_async_session() as db:
            today = datetime.now().date()
            result = await db.execute(select(UserWeight.user_id).distinct())
            user_ids = [row[0] for row in result.all()]

            if not user_ids:
                logger.info("No users with weight records found")
                return

            for user_id in user_ids:
                last_weight = await db.execute(
                    select(UserWeight)
                    .where(UserWeight.user_id == user_id)
                    .order_by(UserWeight.recorded_at.desc())
                    .limit(1)
                )
                last_weight = last_weight.scalar_one_or_none()

                if not last_weight:
                    continue

                has_today_record = await db.execute(
                    select(UserWeight)
                    .where(
                        (UserWeight.user_id == user_id) &
                        (UserWeight.recorded_at >= today)
                    )
                )
                if not has_today_record.scalar_one_or_none():
                    db.add(UserWeight(
                        user_id=user_id,
                        weight=last_weight.weight,
                        recorded_at=today
                    ))
                    logger.info(f"Added daily weight record for user {user_id}")

            await db.commit()
            logger.info("Daily weight records added successfully")
    except Exception as e:
        logger.error(f"Error adding daily weight records: {e}")
        self.retry(exc=e, countdown=600)  # Повторить через 10 минут