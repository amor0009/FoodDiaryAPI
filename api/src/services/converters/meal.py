from api.src.models.meal import Meal
from api.src.models.meal_products import MealProducts
from api.src.models.product import Product
from api.src.schemas.meal import MealRead
from api.src.schemas.product import ProductRead, ProductMedia


def convert_product_model_to_schema(product_model: Product, product_weight: float = None) -> ProductRead:
    images_data = None
    if product_model.images:
        images_data = ProductMedia(
            cover=product_model.images.get("cover"),
            extra_media=product_model.images.get("extra_media", []),
        )

    if product_weight is not None:
        ratio = product_weight / 100.0
        calories = product_model.calories * ratio
        proteins = product_model.proteins * ratio
        fats = product_model.fats * ratio
        carbohydrates = product_model.carbohydrates * ratio
    else:
        calories = product_model.calories
        proteins = product_model.proteins
        fats = product_model.fats
        carbohydrates = product_model.carbohydrates

    return ProductRead(
        id=product_model.id,
        name=product_model.name,
        weight=product_weight if product_weight is not None else product_model.weight,
        calories=calories,
        proteins=proteins,
        fats=fats,
        carbohydrates=carbohydrates,
        description=product_model.description,
        has_images=product_model.has_images,
        images=images_data,
        is_public=product_model.is_public,
        user_id=product_model.user_id,
        created_at=product_model.created_at,
    )


def convert_meal_model_to_schema(meal_model: Meal) -> MealRead:
    products = []
    for meal_product in meal_model.meal_products:
        if meal_product.product:
            product_schema = convert_product_model_to_schema(
                meal_product.product,
                meal_product.product_weight
            )
            products.append(product_schema)

    return MealRead(
        id=meal_model.id,
        name=meal_model.name,
        weight=meal_model.weight,
        calories=meal_model.calories,
        proteins=meal_model.proteins,
        fats=meal_model.fats,
        carbohydrates=meal_model.carbohydrates,
        created_at=meal_model.created_at.date(),
        user_id=meal_model.user_id,
        products=products,
    )
