from io import BytesIO
from fastapi import UploadFile
from magic import from_buffer
from PIL import Image


from api.src.core.config import config


async def is_correct_size(file: UploadFile) -> bool:
    return file.size < config.MAX_FILE_SIZE


async def is_correct_mime_type(file: UploadFile) -> bool:
    file_header = await file.read(2048)
    await file.seek(0)

    mime_type = from_buffer(file_header, mime=True)

    return mime_type in config.ALLOWED_MIME_TYPES


async def covert_to_webp(file: UploadFile, quality: int = 80):
    with Image.open(BytesIO(await file.read())) as img:
        img = img.convert("RGBA")
        webp_file = BytesIO()
        img.save(webp_file, format="WEBP", quality=quality)
        webp_file.seek(0)

    if not file.file.closed:
        file.file.close()

    file.file = webp_file
    file.filename = file.filename.rsplit(".", 1)[0] + ".webp"
