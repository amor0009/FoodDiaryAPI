import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования (INFO, ERROR и т.д.)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Формат логов
    handlers=[
        logging.StreamHandler(),  # Печать в консоль
        logging.FileHandler("C:/D/studies/python/FoodDiaryBackend/app.log", mode='a', encoding='utf-8')
        # Запись в файл app.log
    ]
)

logger = logging.getLogger("food_diary_backend")

class LogRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Логгируем запрос
        logger.info(f"Запрос: {request.method} {request.url.path} от {request.client.host}")

        # Обрабатываем запрос
        response = await call_next(request)

        # Логгируем ответ
        process_time = time.time() - start_time
        logger.info(
            f'{request.client.host} - "{request.method} {request.url.path} HTTP/1.1" {response.status_code} '
            f'{round(process_time, 3)}s'
        )

        return response
