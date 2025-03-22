from aio_pika import Message
from .client import rabbitmq_client
import json
from src.logging_config import logger

# Публикует сообщение в указанную очередь RabbitMQ
async def publish_message(message_data: dict, queue_name: str):
    if not rabbitmq_client.channel:
        raise RuntimeError("RabbitMQ client is not connected")

    message_body = json.dumps(message_data).encode()

    # Публикуем сообщение в очередь
    await rabbitmq_client.channel.default_exchange.publish(
        Message(body=message_body),
        routing_key=queue_name
    )
    print(f"Message published to queue {queue_name} : {message_data}")
    logger.info(f'Message published to queue {queue_name} : {message_data}')
