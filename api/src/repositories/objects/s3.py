import asyncio
import io
import mimetypes
from os.path import splitext
import uuid
import aiohttp
from fastapi import UploadFile
from uuid_utils import uuid7
from api.src.dependencies.s3_uow import S3UnitOfWork
from api.src.repositories.objects.base import BaseObjectRepository
from api.src.core.config import config


class S3ObjectRepository(BaseObjectRepository):
    async def add(self, file: UploadFile, file_key: str | None = None) -> str:
        if file.size is None:
            raise ValueError("File size is required")
        if file.filename is None:
            raise ValueError("Filename is required")

        file_key = file_key or str(uuid7())
        filename = file_key + splitext(file.filename)[1]

        PART_SIZE = 50 * 1024 * 1024
        MULTIPART_THRESHOLD = 100 * 1024 * 1024

        async with S3UnitOfWork() as s3:
            if file.size < MULTIPART_THRESHOLD:
                await s3.safe_client.upload_fileobj(
                    file.file, config.S3_BUCKET, filename
                )
            else:
                create_resp = await s3.safe_client.create_multipart_upload(
                    Bucket=config.S3_BUCKET, Key=filename
                )
                upload_id = create_resp["UploadId"]
                parts = []
                part_number = 1

                while True:
                    chunk = await file.read(PART_SIZE)
                    if not chunk:
                        break
                    resp = await s3.safe_client.upload_part(
                        Bucket=config.S3_BUCKET,
                        Key=filename,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=chunk,
                    )
                    parts.append({"ETag": resp["ETag"], "PartNumber": part_number})
                    part_number += 1

                await s3.safe_client.complete_multipart_upload(
                    Bucket=config.S3_BUCKET,
                    Key=filename,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )

        return filename

    async def add_via_link(
        self, link: str, content_type: str, file_key: str | None = None
    ) -> str:
        file_key = file_key or str(uuid7())
        filename = file_key + (mimetypes.guess_extension(content_type) or "")

        timeout = aiohttp.ClientTimeout(
            total=300,
            connect=30,
            sock_read=270,
        )

        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(link) as response:
                    if response.status != 200:
                        raise ValueError(
                            f"Failed to download file from URL {link} with status {response.status}"
                        )
                    file_data = await response.read()
            except asyncio.TimeoutError as e:
                print(f"AIOHTTP TimeoutError while downloading from {link}")
                raise aiohttp.client_exceptions.ConnectionTimeoutError(
                    f"Connection timeout to host {link}"
                ) from e

        await asyncio.sleep(0.05)

        async with S3UnitOfWork() as s3:
            await s3.safe_client.put_object(
                Bucket=config.S3_BUCKET,
                Key=filename,
                Body=file_data,
                ContentType=content_type,
            )

        return filename

    def get_url(self, filename: str) -> str:
        return f"{config.S3_ACCESS_DOMAIN}/{filename}"

    async def is_exist(self, filename: str) -> bool:
        async with S3UnitOfWork() as s3:
            try:
                await s3.safe_client.head_object(Bucket=config.S3_BUCKET, Key=filename)
                return True
            except s3.safe_client.exceptions.ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    return False
                raise

    async def delete(self, filename: str) -> None:
        async with S3UnitOfWork() as s3:
            await s3.safe_client.delete_object(Bucket=config.S3_BUCKET, Key=filename)

    async def add_from_bytes(
        self, file_data: bytes, file_name: str, content_type: str
    ) -> str:
        file_key = f"{uuid.uuid4()}-{file_name}"
        async with S3UnitOfWork() as s3:
            await s3.safe_client.upload_fileobj(
                io.BytesIO(file_data),
                config.S3_BUCKET,
                file_key,
                ExtraArgs={"ContentType": content_type},
            )
        return file_key

    async def add_from_url_streaming(
        self, link: str, content_type: str, file_key: str | None = None
    ) -> str:
        file_key = file_key or str(uuid7())
        filename = file_key + (mimetypes.guess_extension(content_type) or "")

        timeout = aiohttp.ClientTimeout(
            total=300,
            connect=30,
            sock_read=270,
        )

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(link) as response:
                if response.status != 200:
                    raise ValueError(
                        f"Failed to download file from URL {link} with status {response.status}"
                    )

                async with S3UnitOfWork() as s3:
                    await s3.safe_client.upload_fileobj(
                        response.content,
                        config.S3_BUCKET,
                        filename,
                        ExtraArgs={"ContentType": content_type},
                    )

        return filename
