from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

SECRET_AUTH = os.environ.get("SECRET_AUTH")
ALGORITHM = os.environ.get("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES"))

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT"))

SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_PORT = os.environ.get("SMTP_PORT")
SMTP_HOST = os.environ.get("SMTP_HOST")

TEMPLATES_PATH = os.environ.get("TEMPLATES_PATH")

FILE_PATH = os.environ.get("FILE_PATH")

REDIRECT_URI = os.environ.get("REDIRECT_URI")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

GOOGLE_AUTH_URL = os.environ.get("GOOGLE_AUTH_URL")
GOOGLE_TOKEN_URL = os.environ.get("GOOGLE_TOKEN_URL")
GOOGLE_USERINFO_URL = os.environ.get("GOOGLE_USERINFO_URL")

REDIS_URL = os.environ.get("REDIS_URL")
