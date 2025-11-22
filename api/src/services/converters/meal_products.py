from api.src.models import MealProducts
from api.src.schemas.meal_products import MealProductsRead


def convert_meal_products_model_to_schema(meal_products_model: MealProducts) -> MealProductsRead:
    return MealProductsRead(
        product_weight=meal_products_model.product_weight,
        meal_id=meal_products_model.meal_id,
        product_id=meal_products_model.product_id,
    )
