from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import get_current_user
from src.database.database import get_async_session
from src.models.user import User
from src.schemas.product import ProductCreate, ProductUpdate
from src.services.product_service import add_product, get_products_by_name, delete_product, update_product, get_products, \
    searching_products


product_router = APIRouter()


@product_router.get('/products')
async def get_all_products(db: AsyncSession = Depends(get_async_session),
                           current_user: User = Depends(get_current_user)):
    products = await get_products(db, current_user.id)
    return products


@product_router.get('/search')
async def search_products(db: AsyncSession = Depends(get_async_session),
                          current_user: User = Depends(get_current_user), query: str = None):
    return await searching_products(db, current_user.id, query)


@product_router.post('/product')
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(get_current_user)):
    return await add_product(db, product, current_user.id)


@product_router.post('/add_to_meal')
async def add_product_to_meal(product: ProductCreate, db: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(get_current_user)):
    return await add_product(db, product, current_user.id)


@product_router.get('/{product.name}')
async def get_by_name(product: ProductCreate, db: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(get_current_user)):
    return await get_products_by_name(db, product.name, current_user.id)


@product_router.put('/{product.name}')
async def update(product: ProductUpdate, db: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(get_current_user)):
    return await update_product(db, product, current_user.id)


@product_router.delete('/{product.name}')
async def delete(product: ProductCreate, db: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(get_current_user)):
    return await delete_product(db, product.id, current_user.id)
