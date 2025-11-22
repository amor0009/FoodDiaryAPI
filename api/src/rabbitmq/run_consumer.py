import asyncio
from api.src.rabbitmq.consumer import consume_messages
from api.src.rabbitmq.client import rabbitmq_client
from api.logging_config import logger


async def main():
    try:
        await rabbitmq_client.connect()
        await consume_messages()

        while True:
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
    finally:
        await rabbitmq_client.close()


if __name__ == "__main__":
    asyncio.run(main())
