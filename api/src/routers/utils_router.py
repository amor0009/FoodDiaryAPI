from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Body, Depends
from api.src.database.database import get_async_session
from api.src.models import Product
from api.src.utils.common import async_generate_unique_slug


router = APIRouter(
    prefix="/api/utils",
    tags=["utils"],
    include_in_schema=False,
)


MODEL_MAPPING = {"product": Product}


@router.post("/generate-slug/{model_name}")
async def generate_slug(
    model_name: str,
    text: Annotated[str, Body(min_length=1)],
    exclude_id: Annotated[str | None, Body()] = None,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    model_class = MODEL_MAPPING[model_name]

    slug = await async_generate_unique_slug(
        session=session, title=text, exclude_id=exclude_id, model=model_class
    )

    return {"slug": slug}
