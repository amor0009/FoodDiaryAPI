from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import get_current_user
from src.database.database import get_async_session
from src.models.user import User
from src.schemas.product import ProductCreate, ProductUpdate
from src.services.product_service import add_product, get_products_by_name, delete_product, update_product, \
    get_products, searching_products, get_personal_products

product_router = APIRouter()

# Эндпоинт для получения всех продуктов пользователя
@product_router.get('/products')
async def get_all_products(db: AsyncSession = Depends(get_async_session),
                           current_user: User = Depends(get_current_user)):
    products = await get_products(db, current_user.id)
    return products

# Эндпоинт для поиска продуктов по запросу
@product_router.get('/search')
async def search_products(db: AsyncSession = Depends(get_async_session),
                          current_user: User = Depends(get_current_user), query: str = None):
    return await searching_products(db, current_user.id, query)

# Эндпоинт для создания нового продукта
@product_router.post('/product')
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(get_current_user)):
    return await add_product(db, product, current_user.id)

# Эндпоинт для добавления продукта в прием пищи
@product_router.post('/add_to_meal')
async def add_product_to_meal(product: ProductCreate, db: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(get_current_user)):
    return await add_product(db, product, current_user.id)

# Эндпоинт для получения продукта по его имени
@product_router.get('/{product.name}')
async def get_by_name(product: ProductCreate, db: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(get_current_user)):
    return await get_products_by_name(db, product.name, current_user.id)

# Эндпоинт для обновления данных о продукте
@product_router.put('/update/{product.id}')
async def update(product: ProductUpdate, db: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(get_current_user)):
    return await update_product(db, product, current_user.id)

# Эндпоинт для удаления продукта
@product_router.delete('/delete/{product_id}')
async def delete(product_id: int, db: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(get_current_user)):
    return await delete_product(db,current_user.id, product_id  )

#Эндпоинт для получения личных продуктов
@product_router.get('/my-products')
async def get_my_products(db: AsyncSession = Depends(get_async_session),
                          current_user: User = Depends(get_current_user)):
    return await get_personal_products(db, current_user.id)
