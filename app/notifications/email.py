"""SMTP-отправка email-уведомлений HR.

Используем Yandex 360 (smtp.yandex.ru:465 SSL) с собственного домена
voxscreen.ru — настроены SPF/DKIM, чтобы письма не уходили в спам.
Провайдера легко поменять через .env (smtp_host/port/use_ssl).
"""

from __future__ import annotations

import aiosmtplib
import structlog
from email.message import EmailMessage

from app.config import settings

log = structlog.get_logger()


async def send_email(
    to: list[str],
    subject: str,
    text: str,
    html: str | None = None,
) -> None:
    """Отправить письмо. Бросает исключение при ошибке SMTP — выше ловит Celery
    и делает retry.
    """
    if not to:
        return
    if not settings.smtp_user or not settings.smtp_password:
        # На dev .env часто пустое — лог-варнинг, но не падать.
        log.warning("email_skipped_no_smtp_creds", to=to, subject=subject)
        return

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        use_tls=settings.smtp_use_ssl,
        timeout=30,
    )
    log.info("email_sent", to=to, subject=subject)
