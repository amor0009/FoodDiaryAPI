from api.src.models.user_weight import UserWeight
from api.src.schemas.user_weight import UserWeightRead


def convert_user_weight_model_to_schema(user_weight_model: UserWeight) -> UserWeightRead:
    return UserWeightRead(
        id=user_weight_model.id,
        user_id=user_weight_model.user_id,
        weight=user_weight_model.weight,
        created_at=user_weight_model.created_at,
    )
