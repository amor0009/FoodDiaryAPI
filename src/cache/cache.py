import redis.asyncio as aioredis
import json
from datetime import datetime
from typing import Optional, Union
from src.core.config import REDIS_URL
from src.logging_config import logger

class Cache:
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_url = redis_url
        self.pool: Optional[aioredis.Redis] = None

    # Подключение к Redis для работы с кэшем
    async def connect(self) -> None:
        self.pool = await aioredis.from_url(self.redis_url, decode_responses=True)
        logger.info("Connected to Redis (cache)")

    # Преобразует поле 'recorded_at' в формат даты
    def _convert_recorded_at(self, item: dict) -> dict:
        if "recorded_at" in item:
            item["recorded_at"] = datetime.fromisoformat(item["recorded_at"]).date()
        return item

    # Получение данных из кэша по ключу
    async def get(self, key: str) -> Optional[Union[dict, list]]:
        if not self.pool:
            logger.error("Redis connection is not established")
            return None

        try:
            logger.info(f"Attempting to get data from cache for key {key}")
            value = await self.pool.get(key)
            if value:
                logger.info(f"Data successfully retrieved from cache for key {key}")
                data = json.loads(value)

                if isinstance(data, list):
                    data = [self._convert_recorded_at(item) for item in data]
                else:
                    data = self._convert_recorded_at(data)

                return data
            else:
                logger.warning(f"Data not found in cache for key {key}")
                return None
        except Exception as e:
            logger.exception(f"Error while getting data from cache for key {key}")
            raise

    # Добавление данных в кэш с ключом
    async def set(self, key: str, value: dict, expire: int = 3600) -> None:
        if not self.pool:
            logger.error("Redis connection is not established")
            return

        try:
            logger.info(f"Adding data to cache with key {key}")
            json_value = json.dumps(value)
            await self.pool.set(key, json_value, ex=expire)
            logger.info(f"Data successfully added to cache with key {key}")
        except Exception as e:
            logger.exception(f"Error while adding data to cache with key {key}")
            raise

    # Удаление данных из кэша по ключу
    async def delete(self, key: str) -> None:
        if not self.pool:
            logger.error("Redis connection is not established")
            return

        await self.pool.delete(key)
        logger.info(f"Cache deleted for key {key}")

    # Очистка всех данных в Redis
    async def flushdb(self) -> None:
        if not self.pool:
            logger.error("Redis connection is not established")
            return

        await self.pool.flushdb()
        logger.info("All data in Redis has been flushed")

    # Отключение от Redis
    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.aclose()
            logger.info("Disconnected from Redis (cache)")


cache = Cache()
