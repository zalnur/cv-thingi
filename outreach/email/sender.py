"""SMTP email sender and dry-run .eml writer."""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from outreach.config import Settings
from outreach.models import Contact, GeneratedEmail
from outreach.utils.files import write_private_bytes


class EmailSender:
    """Render and optionally send emails through SMTP over SSL."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_message(self, contact: Contact, generated: GeneratedEmail) -> EmailMessage:
        """Build a standards-compliant plain text email."""
        message = EmailMessage()
        from_email = str(self._settings.smtp_from_email or self._settings.smtp_username)
        from_name = self._settings.smtp_from_name or from_email
        message["From"] = formataddr((from_name, from_email))
        message["To"] = str(contact.email)
        message["Subject"] = _single_line_header(generated.subject)
        message.set_content(generated.body.strip() + "\n")
        return message

    def write_eml(self, contact: Contact, generated: GeneratedEmail, path: Path) -> None:
        """Write a dry-run email file without sending."""
        write_private_bytes(path, self.build_message(contact, generated).as_bytes())

    async def send(self, contact: Contact, generated: GeneratedEmail) -> None:
        """Send email asynchronously using a thread for blocking SMTP I/O."""
        message = self.build_message(contact, generated)
        await asyncio.to_thread(self._send_blocking, message)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type((smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, TimeoutError)),
        reraise=True,
    )
    def _send_blocking(self, message: EmailMessage) -> None:
        tls_context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            self._settings.smtp_host,
            self._settings.smtp_port,
            timeout=30,
            context=tls_context,
        ) as smtp:
            smtp.login(self._settings.smtp_username, self._settings.smtp_password)
            smtp.send_message(message)

def _single_line_header(value: str) -> str:
    header = " ".join(value.strip().splitlines())
    if not header:
        raise ValueError("Email subject cannot be empty.")
    return header
