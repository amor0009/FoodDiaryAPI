from uuid import UUID
from uuid_extensions import uuid7


class UUIDGenerator:
    # Генерация UUID для id записей таблиц
    @staticmethod
    def generate_uuid() -> UUID:
        return uuid7.uuid7()
