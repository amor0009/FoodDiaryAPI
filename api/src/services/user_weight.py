from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.logging_config import logger
from api.src.schemas.user_weight import UserWeightRead, UserWeightCreate
from api.src.repositories.user_weight.base import BaseUserWeightRepository
from api.src.services.converters.user_weight import convert_user_weight_model_to_schema


@dataclass(slots=True)
class UserWeightService:
    _user_weight_repository: BaseUserWeightRepository

    async def get_by_date(self, session: AsyncSession, user_id: UUID, target_date: date) -> UserWeightRead | None:
        logger.info(f"Getting weight for user {user_id} on date {target_date}")

        user_weight = await self._user_weight_repository.get_by_date(session, user_id, target_date)
        if not user_weight:
            logger.info(f"No weight record found for user {user_id} on date {target_date}")
            return None

        return convert_user_weight_model_to_schema(user_weight)

    async def create_or_update(
            self,
            session: AsyncSession,
            user_id: UUID,
            weight_data: UserWeightCreate,
    ) -> UserWeightRead:
        logger.info(f"Creating/updating weight for user {user_id} on date {datetime.now()}")

        if not weight_data.weight or weight_data.weight <= 0:
            logger.error(f"Invalid weight value: {weight_data.weight}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Weight must be a positive number"
            )

        try:
            existing_weight = await self._user_weight_repository.get_by_date(session, user_id, datetime.now())

            if existing_weight:
                if existing_weight.weight == weight_data.weight:
                    logger.info(
                        f"Weight record for user {user_id} on date {datetime.now()} already exists with same weight")
                    return convert_user_weight_model_to_schema(existing_weight)
                else:
                    logger.info(f"Creating additional weight record for user {user_id} on date {datetime.now()}")

            user_weight = await self._user_weight_repository.create_or_update(
                session, user_id, weight_data.weight
            )

            logger.info(f"Weight record created for user {user_id}")
            return convert_user_weight_model_to_schema(user_weight)

        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating/updating weight for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save weight record"
            )

    async def get_last_30_days(self, session: AsyncSession, user_id: UUID) -> list[UserWeightRead] | None:
        logger.info(f"Getting weight history for user {user_id} for last 30 days")

        user_weights = await self._user_weight_repository.get_last_30_days(session, user_id)

        weight_history = [convert_user_weight_model_to_schema(uw) for uw in user_weights]
        logger.info(f"Found {len(weight_history)} weight records for user {user_id}")

        return weight_history

    async def get_weight_trend(self, session: AsyncSession, user_id: UUID) -> dict:
        logger.info(f"Calculating weight trend for user {user_id}")

        weight_history = await self.get_last_30_days(session, user_id)

        if len(weight_history) < 2:
            logger.info(f"Not enough data for trend calculation for user {user_id}")
            return {
                "trend": "insufficient_data",
                "message": "Not enough data to calculate trend",
                "records_count": len(weight_history)
            }

        sorted_weights = sorted(weight_history, key=lambda x: x.created_at)

        first_weight = sorted_weights[0].weight
        last_weight = sorted_weights[-1].weight
        weight_change = last_weight - first_weight

        if weight_change > 0.5:
            trend = "increasing"
            message = f"Weight increased by {weight_change:.1f}kg"
        elif weight_change < -0.5:
            trend = "decreasing"
            message = f"Weight decreased by {abs(weight_change):.1f}kg"
        else:
            trend = "stable"
            message = "Weight remains stable"

        result = {
            "trend": trend,
            "weight_change": round(weight_change, 1),
            "first_weight": round(first_weight, 1),
            "last_weight": round(last_weight, 1),
            "period_days": (sorted_weights[-1].created_at - sorted_weights[0].created_at).days,
            "records_count": len(weight_history),
            "message": message
        }

        logger.info(f"Weight trend for user {user_id}: {trend} ({weight_change:.1f}kg)")
        return result

    async def get_current_weight(self, session: AsyncSession, user_id: UUID) -> UserWeightRead | None:
        logger.info(f"Getting current weight for user {user_id}")

        current_weight = await self.get_by_date(session, user_id, date.today())

        if current_weight:
            logger.info(f"Current weight for user {user_id}: {current_weight.weight}kg")
        else:
            logger.info(f"No weight record for today for user {user_id}")

        return current_weight

    async def delete_weight_record(self, session: AsyncSession, user_id: UUID, target_date: date) -> bool:
        logger.info(f"Deleting weight record for user {user_id} on date {target_date}")

        user_weight = await self._user_weight_repository.get_by_date(session, user_id, target_date)
        if not user_weight:
            logger.warning(f"No weight record found for deletion for user {user_id} on date {target_date}")
            return False

        try:
            await self._user_weight_repository.delete(session, user_weight.id)
            await session.commit()

            logger.info(f"Weight record deleted for user {user_id} on date {target_date}")
            return True

        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting weight record for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete weight record"
            )
