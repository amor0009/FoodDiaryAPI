import re
from typing import Annotated
from uuid import UUID
from pydantic_extra_types.phone_numbers import PhoneNumberValidator
from slowapi import Limiter
from slowapi.util import get_remote_address
from slugify import slugify
from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession


FormatedPhoneNumberType = Annotated[str, PhoneNumberValidator(number_format="E164")]


limiter = Limiter(key_func=get_remote_address)


async def generate_unique_slug(
    session: AsyncSession,
    title: str,
    model,
    max_length: int = 255,
    exclude_id: UUID | None = None,
) -> str:
    base_slug = slugify(title)

    if len(base_slug) > max_length:
        base_slug = base_slug[: max_length - 6]

    regular = "^" + re.escape(base_slug) + "(-([0-9]+))?$"
    query = select(model.slug).where(model.slug.op("~")(regular))

    if exclude_id is not None:
        query = query.where(model.id != exclude_id)

    result = await session.execute(query)
    existing_slugs = result.scalars().all()

    if base_slug not in existing_slugs:
        return base_slug

    prefix = base_slug + "-"
    max_slug_num = 0

    for slug in existing_slugs:
        if slug.startswith(prefix) and slug[len(prefix) :].isdigit():
            num = int(slug[len(prefix) :])
            if num > max_slug_num:
                max_slug_num = num

    new_slug = f"{base_slug}-{max_slug_num + 1}"

    if len(new_slug) > max_length:
        new_suffix = f"-{max_slug_num + 1}"
        base_slug_trimmed = base_slug[: max_length - len(new_suffix)]
        new_slug = f"{base_slug_trimmed}{new_suffix}"

    return new_slug


async def async_generate_unique_slug(
    session: AsyncSession,
    title: str,
    model,
    max_length: int = 255,
    exclude_id: UUID | None = None,
) -> str:
    base_slug = slugify(title)

    if len(base_slug) > max_length:
        base_slug = base_slug[: max_length - 6]

    regular = "^" + re.escape(base_slug) + "(-([0-9]+))?$"
    query = select(model.slug).where(model.slug.op("~")(regular))

    if exclude_id is not None:
        query = query.where(model.id != exclude_id)

    result = await session.execute(query)
    existing_slugs = result.scalars().all()

    if base_slug not in existing_slugs:
        return base_slug

    prefix = base_slug + "-"
    max_slug_num = 0

    for slug in existing_slugs:
        if slug.startswith(prefix) and slug[len(prefix) :].isdigit():
            num = int(slug[len(prefix) :])
            if num > max_slug_num:
                max_slug_num = num

    new_slug = f"{base_slug}-{max_slug_num + 1}"

    if len(new_slug) > max_length:
        new_suffix = f"-{max_slug_num + 1}"
        base_slug_trimmed = base_slug[: max_length - len(new_suffix)]
        new_slug = f"{base_slug_trimmed}{new_suffix}"

    return new_slug


async def is_uniq_slug(session: AsyncSession, slug: str, model, exclude_id: UUID | None = None) -> bool:
    conditions = [model.slug == slug]
    if exclude_id is not None:
        conditions.append(model.id != exclude_id)

    query = select(exists().where(and_(*conditions)))

    result = await session.execute(query)

    return not result.scalar()


def is_valid_slug(slug: str) -> bool:
    regular = r"^[a-z0-9-]+$"
    if re.match(regular, slug):
        return True
    else:
        return False
