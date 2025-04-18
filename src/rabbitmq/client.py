import aio_pika
from src.core.config import config
from src.logging_config import logger


class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None

    # Устанавливает соединение с RabbitMQ и открывает канал
    async def connect(self):
        self.connection = await aio_pika.connect_robust(
            login=config.RABBITMQ_DEFAULT_USER,
            password=config.RABBITMQ_DEFAULT_PASS,
            host=config.RABBITMQ_DEFAULT_HOST,
            virtualhost=config.RABBITMQ_DEFAULT_VHOST,
            port=config.RABBITMQ_DEFAULT_PORT,
        )
        self.channel = await self.connection.channel()
        logger.info("RabbitMQClient connected")

    # Закрывает соединение и канал RabbitMQ
    async def close(self):
        if self.connection:
            await self.connection.close()
            await self.channel.close()
            logger.info("RabbitMQClient disconnected")

    # Объявляет очередь в RabbitMQ
    async def declare_queue(self, queue_name, durable=True):
        if not self.channel:
            raise RuntimeError("RabbitMQ channel is not connected")
        logger.info(f"RabbitMQClient declare_queue with name: {queue_name}")
        return await self.channel.declare_queue(queue_name, durable=durable)


# Создание экземпляра клиента RabbitMQ
rabbitmq_client = RabbitMQClient()
