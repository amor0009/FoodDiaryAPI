from abc import ABC, abstractmethod

from fastapi import UploadFile


class BaseObjectRepository(ABC):
    @abstractmethod
    async def add(self, file: UploadFile, file_key: str | None = None) -> str: ...

    @abstractmethod
    async def add_via_link(
        self, link: str, content_type: str, file_key: str | None = None
    ) -> str: ...

    @abstractmethod
    def get_url(self, filename: str) -> str: ...

    @abstractmethod
    async def is_exist(self, filename: str) -> bool: ...

    @abstractmethod
    async def delete(self, filename: str) -> None: ...

    @abstractmethod
    async def add_from_bytes(
        self, file_data: bytes, file_name: str, content_type: str
    ) -> str: ...
