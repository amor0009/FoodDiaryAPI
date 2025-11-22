import json
from aio_pika import IncomingMessage
from .client import rabbitmq_client
from api.logging_config import logger
from ..fone_tasks.verification import send_mail


async def process_message(message: IncomingMessage):
    try:
        data = json.loads(message.body.decode())
        logger.info(f'Processing message: {data}')

        if not data.get("email"):
            logger.error("No email in message")
            await message.reject(requeue=False)
            return

        send_mail(
            recipient=data["email"],
            subject="Welcome to Food Diary!",
            template_name="registration_email_notification.html",
            context={"user_name": data.get("login", "")}
        )

        await message.ack()
        logger.info("Email sent successfully")

    except json.JSONDecodeError:
        logger.error("Invalid JSON format")
        await message.reject(requeue=False)
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await message.reject(requeue=True)


async def consume_messages(queue_name: str = "registration_queue"):
    if not rabbitmq_client.channel:
        raise RuntimeError("RabbitMQ client is not connected")

    queue = await rabbitmq_client.declare_queue(queue_name, durable=True)
    print(f"Started consuming messages from {queue_name}")
    logger.info(f"Started consuming messages from {queue_name}")
    await queue.consume(process_message)
