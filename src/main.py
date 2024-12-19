from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers.database_router import database_router
from src.routers.meal_products_router import meal_products_router
from src.routers.meal_router import meal_router
from src.routers.product_router import product_router
from src.routers.auth_router import auth_router
from src.routers.user_router import user_router
from src.routers.user_weight_router import user_weight_router

app = FastAPI(
    title="Food Diary",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meal_products_router, prefix="/meal_products")
app.include_router(user_weight_router, prefix="/user_weight")
app.include_router(database_router, prefix="/database")
app.include_router(auth_router, prefix="/auth")
app.include_router(user_router, prefix="/user")
app.include_router(product_router, prefix="/product")
app.include_router(meal_router, prefix="/meal")
