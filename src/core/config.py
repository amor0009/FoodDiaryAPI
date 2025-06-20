import re
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
import os


load_dotenv()


class Configuration:

    DB_HOST = os.environ.get("DB_HOST")
    DB_PORT = os.environ.get("DB_PORT")
    DB_NAME = os.environ.get("DB_NAME")
    DB_USER = os.environ.get("DB_USER")
    DB_PASS = os.environ.get("DB_PASS")

    DB_NAME_TEST = os.environ.get("DB_NAME_TEST")
    DB_HOST_TEST = os.environ.get("DB_HOST_TEST")
    DB_HOST_DOCKER_TEST = os.environ.get("DB_HOST_DOCKER_TEST")
    DB_PORT_TEST = os.environ.get("DB_PORT_TEST")
    DB_USER_TEST = os.environ.get("DB_USER_TEST")
    DB_PASS_TEST = os.environ.get("DB_PASS_TEST")

    USER_SECRET_AUTH = os.environ.get("USER_SECRET_AUTH")
    STAFF_SECRET_AUTH = os.environ.get("STAFF_SECRET_AUTH")
    ALGORITHM = os.environ.get("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES"))

    RABBITMQ_DEFAULT_USER = os.environ.get("RABBITMQ_DEFAULT_USER")
    RABBITMQ_DEFAULT_PASS = os.environ.get("RABBITMQ_DEFAULT_PASS")
    RABBITMQ_DEFAULT_HOST = os.environ.get("RABBITMQ_DEFAULT_HOST")
    RABBITMQ_DEFAULT_VHOST = os.environ.get("RABBITMQ_DEFAULT_VHOST")
    RABBITMQ_DEFAULT_PORT = int(os.environ.get("RABBITMQ_DEFAULT_PORT"))

    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
    SMTP_PORT = os.environ.get("SMTP_PORT")
    SMTP_HOST = os.environ.get("SMTP_HOST")

    TEMPLATES_PATH = os.environ.get("TEMPLATES_PATH")
    LOGGER_FILE_PATH = os.environ.get("LOGGER_FILE_PATH")
    FILE_PATH = os.environ.get("FILE_PATH")

    REDIRECT_URI = os.environ.get("REDIRECT_URI")
    CLIENT_ID = os.environ.get("CLIENT_ID")
    CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

    GOOGLE_AUTH_URL = os.environ.get("GOOGLE_AUTH_URL")
    GOOGLE_TOKEN_URL = os.environ.get("GOOGLE_TOKEN_URL")
    GOOGLE_USERINFO_URL = os.environ.get("GOOGLE_USERINFO_URL")

    REDIS_URL = os.environ.get("REDIS_URL")

    ENGLISH_PATTERN = re.compile(r'^[a-zA-Z0-9@._-]+$')
    SPECIAL_CHARS = "!@#$%^&*()_+-="

    ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif"}

    env = Environment(loader=FileSystemLoader(TEMPLATES_PATH))

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def test_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER_TEST}:{self.DB_PASS_TEST}@{self.DB_HOST_TEST}:{self.DB_PORT_TEST}/{self.DB_NAME_TEST}"


config = Configuration()
