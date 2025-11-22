from api.src.models import Product
from api.src.schemas.product import ProductRead, ProductMedia


def convert_product_model_to_schema(product_model: Product) -> ProductRead:
    images_data = None
    if product_model.images:
        images_data = ProductMedia(
            cover=product_model.images.get("cover"),
            extra_media=product_model.images.get("extra_media", []),
        )

    return ProductRead(
        id=product_model.id,
        name=product_model.name,
        weight=product_model.weight,
        calories=product_model.calories,
        proteins=product_model.proteins,
        fats=product_model.fats,
        carbohydrates=product_model.carbohydrates,
        description=product_model.description,
        has_images=product_model.has_images,
        images=images_data,
        is_public=product_model.is_public,
        user_id=product_model.user_id,
        created_at=product_model.created_at,
    )
