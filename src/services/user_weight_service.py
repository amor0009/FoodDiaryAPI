from datetime import datetime, timedelta, date
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.models.user_weight import UserWeight
from src.schemas.user_weight import UserWeightUpdate


async def save_or_update_weight(user_weight: UserWeightUpdate, db: AsyncSession, current_user: User):
    current_date = date.today()
    query = select(UserWeight).where(and_(
        UserWeight.user_id == current_user.id,
        UserWeight.recorded_at == current_date
    ))
    result = await db.execute(query)
    user_weight_db = result.scalar_one_or_none()

    if user_weight_db:
        # Если запись существует, обновляем вес
        user_weight_db.weight = user_weight.weight
    else:
        # Иначе создаем новую запись, используя SQLAlchemy модель
        new_user_weight = UserWeight(
            user_id=current_user.id,
            weight=user_weight.weight
        )
        db.add(new_user_weight)

    await db.commit()
    return user_weight


async def get_current_weight(current_date: str, db: AsyncSession, current_user: User):
    current_date_obj = datetime.strptime(current_date, '%Y-%m-%d').date()
    query = select(UserWeight).where(
        (UserWeight.user_id == current_user.id) &
        (UserWeight.recorded_at == current_date_obj)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_weights(db: AsyncSession, current_user: User):
    thirty_days_ago = datetime.today() - timedelta(days=30)
    result = await db.execute(
        select(UserWeight).where(
            UserWeight.user_id == current_user.id and
            UserWeight.recorded_at >= thirty_days_ago
        ).order_by(UserWeight.recorded_at)
    )
    weight_history = result.scalars().all()
    return weight_history
