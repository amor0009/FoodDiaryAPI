from aiosmtplib import SMTP
from email.message import EmailMessage
from fastapi import HTTPException
from src.core.config import config
from src.logging_config import logger


class EmailService:
    # Отправка email-сообщения
    @classmethod
    async def send_email(cls, to_email: str, subject: str, template_name: str, context: dict):
        try:
            template = config.env.get_template(template_name)
            html_content = template.render(context)

            message = EmailMessage()
            message['From'] = config.SMTP_USER
            message['To'] = to_email
            message['Subject'] = subject
            message.set_content(html_content, subtype='html')

            async with SMTP(hostname=config.SMTP_HOST, port=config.SMTP_PORT, use_tls=True) as smtp:
                await smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
                await smtp.send_message(message)
                logger.info(f"Email sent to {to_email}")
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            raise HTTPException(status_code=500, detail="Failed to send email")