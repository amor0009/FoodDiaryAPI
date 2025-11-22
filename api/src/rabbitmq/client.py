import aio_pika
from api.src.core.config import config
from api.src.exceptions import RabbitMQChannelError
from api.logging_config import logger


class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None

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

    async def close(self):
        if self.connection:
            await self.connection.close()
            await self.channel.close()
            logger.info("RabbitMQClient disconnected")

    async def declare_queue(self, queue_name, durable=True):
        if not self.channel:
            raise RabbitMQChannelError
        logger.info(f"RabbitMQClient declare_queue with name: {queue_name}")
        return await self.channel.declare_queue(queue_name, durable=durable)


rabbitmq_client = RabbitMQClient()
