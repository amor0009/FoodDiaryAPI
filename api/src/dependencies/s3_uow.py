from types import TracebackType
from typing import Self
from mypy_boto3_s3.client import S3Client
from api.src.core.config import config
from api.src.database.database import s3_session


class S3UnitOfWork:
    def __init__(self):
        self.session = s3_session
        self.client: S3Client | None = None

    async def __aenter__(self) -> Self:
        self.client = await self.session.client(
            service_name="s3",
            region_name=config.S3_REGION,
            endpoint_url=config.S3_ENDPOINT,
            aws_access_key_id=config.S3_KEY_ID,
            aws_secret_access_key=config.S3_SECRET_ACCESS_KEY,
        ).__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def safe_client(self) -> S3Client:
        if self.client is None:
            raise RuntimeError("S3 client not initialized")
        return self.client
