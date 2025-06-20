from fastapi import APIRouter, Depends, UploadFile, File, Response
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import Security
from src.database.database import get_async_session
from src.models.user import User
from src.schemas.product import ProductCreate, ProductUpdate
from src.services.product_service import ProductService


product_router = APIRouter(tags=["Products"])


# Эндпоинт для получения всех продуктов пользователя
@product_router.get('/products')
async def get_all_products(
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(Security.get_required_user)
):
    products = await ProductService.get_products(db, current_user.id)
    return products


# Эндпоинт для поиска продуктов по запросу
@product_router.get('/search')
async def search_products(
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(Security.get_required_user),
        query: str = None
):
    return await ProductService.searching_products(db, current_user.id, query)


# Эндпоинт для создания нового продукта
@product_router.post('/product')
async def create_product(
        product: ProductCreate,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(Security.get_required_user)
):
    return await ProductService.add_product(db, product, current_user.id)


# Эндпоинт для добавления продукта в прием пищи
@product_router.post('/add_to_meal')
async def add_product_to_meal(
        product: ProductCreate,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(Security.get_required_user)
):
    return await ProductService.add_product(db, product, current_user.id)


# Эндпоинт для получения продукта по его имени
@product_router.get('/{product.name}')
async def get_by_name(
        product: ProductCreate,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(Security.get_required_user)
):
    return await ProductService.get_products_by_name(db, product.name, current_user.id)


# Эндпоинт для обновления данных о продукте
@product_router.put('/update/{product_id}')
async def update(
        product_id: int,
        product: ProductUpdate,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(Security.get_required_user)
):
    return await ProductService.update_product(db, product, current_user.id)


# Эндпоинт для удаления продукта
@product_router.delete('/delete/{product_id}')
async def delete(
        product_id: int,
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(Security.get_required_user)
):
    return await ProductService.delete_product(db, current_user.id, product_id)


# Эндпоинт для получения личных продуктов
@product_router.get('/my-products')
async def get_my_products(
        db: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(Security.get_required_user)
):
    return await ProductService.get_personal_products(db, current_user.id)


# Эндпоинт для загрузки нового фото профиля
@product_router.post('/upload-product-picture/{product_id}')
async def upload_photo(
    product_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(Security.get_required_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await ProductService.upload_product_picture(file, current_user.id, product_id, db)


# Эндпоинт для получения фото профиля
@product_router.get('/product-picture/{product_id}')
async def get_photo(
    product_id: int,
    current_user: User = Depends(Security.get_required_user),
    db: AsyncSession = Depends(get_async_session),
):
    # Получаем фото профиля пользователя
    image = await ProductService.get_product_picture(current_user.id, product_id, db)
    return Response(content=image, media_type="image/jpeg")  # Возвращаем изображение в формате JPEG
