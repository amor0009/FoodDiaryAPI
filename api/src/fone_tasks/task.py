from datetime import datetime, timedelta
import asyncio
from api.src.core.config import config
from api.src.fone_tasks.verification import send_mail
from api.src.fone_tasks.celery_config import celery_app
from sqlalchemy import delete, select
from api.src.database.database import get_async_session
from api.logging_config import logger
from api.src.models.user_weight import UserWeight
from api.src.models.meal_products import MealProducts
from api.src.rabbitmq.client import rabbitmq_client
from api.src.rabbitmq.consumer import consume_messages


@celery_app.task(bind=True, name="start_rabbitmq_consumer")
def start_rabbitmq_consumer(self, queue_name="registration_queue"):
    async def run_consumer():
        try:
            await rabbitmq_client.connect()
            logger.info("RabbitMQ connection established for consumer")
            await consume_messages(queue_name)
        except Exception as e:
            logger.error(f"Error starting RabbitMQ consumer: {e}")
            self.retry(exc=e, countdown=60)

    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(run_consumer())
    else:
        loop.run_until_complete(run_consumer())


@celery_app.task(bind=True, name="delete_old_user_weights")
def delete_old_user_weights(self):
    async def run_deletion():
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        try:
            async with get_async_session() as db:
                await db.execute(delete(UserWeight).where(UserWeight.created_at < thirty_days_ago))
                await db.commit()
                logger.info('Deleted old user weights (last 30 days)')
        except Exception as e:
            logger.error(f"Error deleting old weights: {e}")
            self.retry(exc=e, countdown=300)

    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(run_deletion())
    else:
        loop.run_until_complete(run_deletion())


@celery_app.task(bind=True, name="delete_old_meal_products")
def delete_old_meal_products(self):
    async def run_deletion():
        seven_days_ago = datetime.now().date() - timedelta(days=7)
        try:
            async with get_async_session() as db:
                await db.execute(delete(MealProducts).where(MealProducts.meal.created_at < seven_days_ago))
                await db.commit()
                logger.info('Deleted old meal products (last 7 days)')
        except Exception as e:
            logger.error(f"Error deleting old meals: {e}")
            self.retry(exc=e, countdown=300)

    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(run_deletion())
    else:
        loop.run_until_complete(run_deletion())


@celery_app.task(bind=True, name="add_daily_weight_records")
def add_daily_weight_records(self):
    async def run_addition():
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
                        .order_by(UserWeight.created_at.desc())
                        .limit(1)
                    )
                    last_weight = last_weight.scalar_one_or_none()

                    if not last_weight:
                        continue

                    has_today_record = await db.execute(
                        select(UserWeight)
                        .where(
                            (UserWeight.user_id == user_id) &
                            (UserWeight.created_at >= today)
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
            self.retry(exc=e, countdown=600)

    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(run_addition())
    else:
        loop.run_until_complete(run_addition())


@celery_app.task(bind=True, name="send_code")
def send_code(self, code: str, send_type: str, recipient: str, template_path: str, subject: str) -> None:
    if send_type == "email":
        try:
            template = config.TEMPLATES_PATH.get_template(template_path)
            email_content = template.render(code=code)

            send_mail(
                recipient=recipient,
                text=email_content,
                subject=subject,
                use_html=True,
            )
            logger.info(f"Confirmation code sent to {recipient} using template {template_path}")
        except Exception as e:
            logger.error(f"Failed to send confirmation code to {recipient}: {str(e)}")
            self.retry(exc=e, countdown=30, max_retries=3)
    else:
        logger.warning(f"Unsupported send type: {send_type}")
        raise ValueError(f"Unsupported send type: {send_type}")
