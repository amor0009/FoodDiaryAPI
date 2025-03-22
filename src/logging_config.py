import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("C:/D/studies/python/FoodDiaryBackend/app.log", mode='a', encoding='utf-8')
    ]
)

logger = logging.getLogger("food_diary_backend")
