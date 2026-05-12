from pathlib import Path

from outreach.config import Settings
from outreach.email.sender import EmailSender
from outreach.models import Contact, GeneratedEmail


def test_write_eml(tmp_path: Path) -> None:
    settings = Settings(
        SMTP_FROM_EMAIL="me@example.com",
        SMTP_USERNAME="me@example.com",
        SMTP_PASSWORD="secret",
    )
    sender = EmailSender(settings)
    contact = Contact(email="hr@example.com", company_name="Example")
    generated = GeneratedEmail(
        subject="Role fit",
        body="Hello, would you be open to a quick conversation?",
        personalization_notes=[],
        confidence=0.8,
        warnings=[],
    )

    path = tmp_path / "email.eml"
    sender.write_eml(contact, generated, path)

    assert path.exists()
    assert "Subject: Role fit" in path.read_text(encoding="utf-8")
