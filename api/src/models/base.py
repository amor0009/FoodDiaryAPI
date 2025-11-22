from datetime import datetime
from uuid import UUID
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from uuid_utils import uuid7


def generate_uuid():
    return UUID(str(uuid7()))


class Base(DeclarativeBase):
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone("UTC", func.now()),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone("UTC", func.now()),
        onupdate=func.timezone("UTC", func.now()),
        nullable=False,
    )

    def __repr__(self):
        return f"""<{self.__class__.__name__}({
            [
                ", ".join(
                    f"{k}={self.__dict__[k]}" for k in self.__dict__ if "_sa_" != k[:4]
                )
            ]
        }"""

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
