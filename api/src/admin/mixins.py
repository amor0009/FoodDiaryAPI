from api.src.dependencies.repositories import get_object_repository
from api.src.repositories.objects.base import BaseObjectRepository
from api.src.utils.images import covert_to_webp
from fastapi import UploadFile


class MixinImageControl:
    _object_repository: BaseObjectRepository = get_object_repository()

    async def _save_image(self, image: UploadFile) -> str:
        await covert_to_webp(image)
        file_id = await self._object_repository.add(image)
        return file_id

    async def create_image(self, image: UploadFile | None) -> str | None:
        if image:
            return await self._save_image(image)
        return None

    async def edit_image(
        self,
        old_image: str | None,
        new_image: UploadFile | None,
    ) -> str | None:
        if old_image and new_image:
            await self._object_repository.delete(old_image)
            return await self._save_image(new_image)
        elif new_image:
            return await self._save_image(new_image)
        return old_image

    async def delete_image(self, image: str | None) -> None:
        if image:
            await self._object_repository.delete(image)
