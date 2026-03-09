from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.core.security import Security
from api.src.database.database import get_async_session
from api.src.models.user import User
from api.src.schemas.base import Pagination
from api.src.schemas.product import ProductRead, ProductCreate, ProductUpdate, ProductAdd
from api.src.services.product import ProductService
from api.src.dependencies.services import get_product_service
from typing import Optional

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
    name: str = Form(...),
    weight: float = Form(...),
    calories: float = Form(...),
    proteins: float = Form(...),
    fats: float = Form(...),
    carbohydrates: float = Form(...),
    description: str = Form(...),
    picture: Optional[UploadFile] = File(None),
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    product_service: ProductService = Depends(get_product_service),
) -> ProductRead:
    product_data = ProductCreate(
        name=name,
        weight=weight,
        calories=calories,
        proteins=proteins,
        fats=fats,
        carbohydrates=carbohydrates,
        description=description
    )
    return await product_service.create_product_with_picture(
        session, product_data, picture, current_user.id
    )


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
    name: Optional[str] = Form(None),
    weight: Optional[float] = Form(None),
    calories: Optional[float] = Form(None),
    proteins: Optional[float] = Form(None),
    fats: Optional[float] = Form(None),
    carbohydrates: Optional[float] = Form(None),
    description: Optional[str] = Form(None),
    picture: Optional[UploadFile] = File(None),
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    product_service: ProductService = Depends(get_product_service),
) -> ProductRead:
    update_dict = {}
    if name is not None:
        update_dict["name"] = name
    if weight is not None:
        update_dict["weight"] = weight
    if calories is not None:
        update_dict["calories"] = calories
    if proteins is not None:
        update_dict["proteins"] = proteins
    if fats is not None:
        update_dict["fats"] = fats
    if carbohydrates is not None:
        update_dict["carbohydrates"] = carbohydrates
    if description is not None:
        update_dict["description"] = description

    product_update = ProductUpdate(**update_dict)
    return await product_service.update_product_with_picture(
        session, product_id, product_update, picture, current_user.id
    )


@product_router.delete("/{product_id}")
async def delete_product(
    product_id: UUID,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    product_service: ProductService = Depends(get_product_service),
) -> dict:
    return await product_service.delete_product(session, product_id, current_user.id)