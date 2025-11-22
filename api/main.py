from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.src.admin import admin
from api.src.cache.cache import cache
from api.src.core.config import config
from api.src.rabbitmq.client import rabbitmq_client
from api.src.routers.database_router import database_router
from api.src.routers.meal_router import meal_router
from api.src.routers.product_router import product_router
from api.src.routers.auth_router import auth_router
from api.src.routers.user_router import user_router
from api.src.routers.user_weight_router import user_weight_router
from api.src.routers.utils_router import router as utils_router
from starlette.middleware.sessions import SessionMiddleware
import sentry_sdk


app = FastAPI(
    title="Food Diary",
    version="0.1.2",
    docs_url="/docs",
)

sentry_sdk.init(
    dsn=config.SENTRY_DSN,
    traces_sample_rate=1.0,
    environment="api",
    _experiments={
        "continuous_profiling_auto_start": True,
    },
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
    #await rabbitmq_client.connect()
    await cache.connect()


@app.on_event("shutdown")
async def shutdown():
    #await rabbitmq_client.close()
    await cache.disconnect()

app.include_router(user_weight_router)
app.include_router(database_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(product_router)
app.include_router(meal_router)
app.include_router(utils_router)

admin.mount_to(app)
