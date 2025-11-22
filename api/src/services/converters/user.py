from api.src.models.user import User
from api.src.schemas.user import UserRead, UserAvatar


def convert_user_model_to_schema(user_model: User) -> UserRead:
    avatar_data = None
    if user_model.avatar:
        avatar_data = UserAvatar(avatar=user_model.avatar)

    return UserRead(
        id=user_model.id,
        email=user_model.email,
        firstname=user_model.firstname,
        lastname=user_model.lastname,
        age=user_model.age,
        height=user_model.height,
        weight=user_model.weight,
        gender=user_model.gender,
        activity_level=user_model.activity_level,
        aim=user_model.aim,
        recommended_calories=user_model.recommended_calories,
        has_avatar=user_model.has_avatar,
        avatar=avatar_data,
    )
