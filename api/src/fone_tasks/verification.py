import secrets
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import os
from jinja2 import Template
from api.src.cache.cache import cache
from api.src.core.config import config
from api.logging_config import logger


def generate_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


async def create_6_digits(name: str, data: str, expired_at: int = 1800) -> str:
    if not cache.pool:
        await cache.connect()

    code = None
    attempts = 0
    max_attempts = 10

    while attempts < max_attempts:
        code = generate_code()
        print(code)
        key = f"{name}_{code}"

        existing_data = await cache.pool.get(key)
        if not existing_data:
            break
        attempts += 1
    else:
        raise Exception("Не удалось сгенерировать уникальный код")

    key = f"{name}_{code}"
    await cache.pool.set(key, data, ex=expired_at)

    logger.info(f"Created {name} code for {data}: {code} (expires in {expired_at}s)")
    return code


async def get_code_data(name: str, code: str) -> Optional[str]:
    if not cache.pool:
        await cache.connect()

    key = f"{name}_{code}"
    data = await cache.pool.get(key)

    if data is None:
        logger.warning(f"Code not found or expired: {name}_{code}")
        return None

    logger.info(f"Retrieved {name} data for code {code}: {data}")
    return data


async def delete_code(name: str, code: str) -> bool:
    if not cache.pool:
        await cache.connect()

    key = f"{name}_{code}"
    result = await cache.pool.delete(key)

    if result:
        logger.info(f"Deleted {name} code: {code}")
    else:
        logger.warning(f"Code not found for deletion: {name}_{code}")

    return bool(result)


async def verify_code(name: str, code: str, expected_data: str) -> bool:
    stored_data = await get_code_data(name, code)

    if stored_data is None:
        return False

    is_valid = stored_data == expected_data

    if is_valid:
        logger.info(f"Code verification successful for {expected_data}")
    else:
        logger.warning(
            f"Code verification failed for {expected_data}. Stored: {stored_data}, Expected: {expected_data}")

    return is_valid


def send_mail(
        recipient: str,
        text: str = None,
        subject: str = None,
        use_html: bool = False,
        template_name: str = None,
        context: dict = None
) -> None:
    if not recipient:
        logger.warning("No recipient specified for email")
        return

    if template_name and context:
        try:
            template_path = os.path.join("templates", "emails", template_name)
            with open(template_path, 'r', encoding='utf-8') as file:
                template_content = file.read()

            template = Template(template_content)
            text = template.render(**context)
            use_html = True
        except Exception as e:
            logger.error(f"Error loading template {template_name}: {e}")
            return

    if not text:
        logger.error("No text content for email")
        return

    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = config.SMTP_USER
    message["To"] = recipient
    message.attach(MIMEText(text, "html" if use_html else "plain"))

    try:
        context = ssl.create_default_context()

        logger.info(f"Attempting to connect to SMTP: {config.SMTP_HOST}:{config.SMTP_PORT}")

        with smtplib.SMTP(
                host=config.SMTP_HOST,
                port=config.SMTP_PORT,
                timeout=30
        ) as server:
            server.ehlo()
            if server.has_extn('STARTTLS'):
                server.starttls(context=context)
                server.ehlo()

            logger.info(f"Logging in as: {config.SMTP_USER}")
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)

            logger.info(f"Sending email to: {recipient}")
            server.send_message(message)

        logger.info(f"Email sent successfully to {recipient}")

    except smtplib.SMTPServerDisconnected as e:
        logger.error(f"SMTP server disconnected: {str(e)}")
        raise
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {str(e)}")
        raise
