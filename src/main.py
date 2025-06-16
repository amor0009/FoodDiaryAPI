from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.admin import admin
from src.cache.cache import cache
from src.core.config import config
from src.rabbitmq.client import rabbitmq_client
from src.routers.database_router import database_router
from src.routers.meal_products_router import meal_products_router
from src.routers.meal_router import meal_router
from src.routers.product_router import product_router
from src.routers.auth_router import auth_router
from src.routers.user_router import user_router
from src.routers.user_weight_router import user_weight_router
from starlette.middleware.sessions import SessionMiddleware


app = FastAPI(
    title="Food Diary",
    version="0.1.2",
    docs_url="/docs",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=config.STAFF_SECRET_AUTH,
    session_cookie="gbt_admin_session",
    max_age=1800
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5172"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await rabbitmq_client.connect()
    await cache.connect()


@app.on_event("shutdown")
async def shutdown():
    await rabbitmq_client.close()
    await cache.disconnect()

app.include_router(meal_products_router, prefix="/meal_products")
app.include_router(user_weight_router, prefix="/user_weight")
app.include_router(database_router, prefix="/database")
app.include_router(auth_router, prefix="/auth")
app.include_router(user_router, prefix="/user")
app.include_router(product_router, prefix="/product")
app.include_router(meal_router, prefix="/meal")

admin.mount_to(app)

