import logging

from src.core.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOGGER_FILE_PATH, mode='a', encoding='utf-8')
    ]
)

logger = logging.getLogger("food_diary_backend")
