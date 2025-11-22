from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.core.security import Security
from api.src.database.database import get_async_session
from api.src.models.user import User
from api.src.schemas.base import Pagination
from api.src.schemas.product import ProductRead, ProductCreate, ProductUpdate, ProductAdd
from api.src.services.product import ProductService
from api.src.dependencies.services import get_product_service


product_router = APIRouter(prefix="/api/products", tags=["products"])


@product_router.get("/")
async def get_products(
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    product_service: ProductService = Depends(get_product_service),
    pagination: Pagination = Depends()
) -> list[ProductRead]:
    return await product_service.get_user_products(session, current_user.id, pagination)


@product_router.get("/personal")
async def get_personal_products(
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    product_service: ProductService = Depends(get_product_service),
    pagination: Pagination = Depends()
) -> list[ProductRead]:
    return await product_service.get_personal_products(session, current_user.id, pagination)


@product_router.get("/search")
async def search_products(
    query: str = Query(..., min_length=1, description="Поисковый запрос"),
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    product_service: ProductService = Depends(get_product_service),
    pagination: Pagination = Depends()
) -> list[ProductRead]:
    return await product_service.search_products(session, current_user.id, query, pagination)


@product_router.get("/{product_id}")
async def get_product(
    product_id: UUID,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    product_service: ProductService = Depends(get_product_service),
) -> ProductRead:
    product = await product_service.get_product_by_id(session, product_id, current_user.id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@product_router.post("/")
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    product_service: ProductService = Depends(get_product_service),
) -> ProductRead:
    return await product_service.create_product(session, product_data, current_user.id)


@product_router.post("/quick")
async def create_quick_product(
    product_data: ProductAdd,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    product_service: ProductService = Depends(get_product_service),
) -> ProductRead:
    return await product_service.add_quick_product(session, product_data, current_user.id)


@product_router.put("/{product_id}")
async def update_product(
    product_id: UUID,
    product_update: ProductUpdate,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    product_service: ProductService = Depends(get_product_service),
) -> ProductRead:
    return await product_service.update_product(session, product_id, product_update, current_user.id)


@product_router.delete("/{product_id}")
async def delete_product(
    product_id: UUID,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    product_service: ProductService = Depends(get_product_service),
) -> dict:
    return await product_service.delete_product(session, product_id, current_user.id)
