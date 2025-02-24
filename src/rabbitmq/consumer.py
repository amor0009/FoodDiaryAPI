import json
from aio_pika import IncomingMessage
from .client import rabbitmq_client
from src.services.email_service import send_email
from ..logging_config import logger

async def process_message(message: IncomingMessage):
    try:
        print(f"Received message: {message.body.decode()}")
        logger.info(f'Received message: {message.body.decode()}')
        data = json.loads(message.body.decode())
        to_email = data.get("email")
        user_name = data.get("login")

        if to_email:
            await send_email(
                to_email=to_email,
                subject="Welcome to Food Diary!",
                template_name="registration_email_notification.html",
                context={"user_name": user_name}
            )
        await message.ack()
        print("Message is acknowledged and removed from the queue")
        logger.info(f"Message: {message.body.decode()} - is acknowledged and removed from the queue")
    except Exception as e:
        print(f"Error processing message: {e}")

async def consume_messages(queue_name: str = "registration_queue"):
    if not rabbitmq_client.channel:
        raise RuntimeError("RabbitMQ client is not connected")

    queue = await rabbitmq_client.declare_queue(queue_name, durable=True)
    print(f"Started consuming messages from {queue_name}")
    logger.info(f"Started consuming messages from {queue_name}")
    await queue.consume(process_message)
