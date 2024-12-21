import aio_pika
from src.core.config import RABBITMQ_HOST, RABBITMQ_PORT

class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT
        )
        self.channel = await self.connection.channel()
        print("Connected to RabbitMQ")

    async def close(self):
        if self.connection:
            await self.connection.close()
            print("RabbitMQ connection closed")

    async def declare_queue(self, queue_name, durable=True):
        if not self.channel:
            raise RuntimeError("RabbitMQ channel is not connected")
        return await self.channel.declare_queue(queue_name, durable=durable)

rabbitmq_client = RabbitMQClient()
