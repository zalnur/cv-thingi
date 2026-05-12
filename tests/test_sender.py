from pathlib import Path

import outreach.email.sender as sender_module
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


def test_send_blocking_uses_verified_tls_context(monkeypatch) -> None:
    settings = Settings(
        SMTP_FROM_EMAIL="me@example.com",
        SMTP_USERNAME="me@example.com",
        SMTP_PASSWORD="secret",
    )
    sender = EmailSender(settings)
    message = sender.build_message(
        Contact(email="hr@example.com", company_name="Example"),
        GeneratedEmail(
            subject="Role fit",
            body="Hello, would you be open to a quick conversation?",
            personalization_notes=[],
            confidence=0.8,
            warnings=[],
        ),
    )
    tls_context = object()
    observed = {}

    class FakeSMTP:
        def __init__(self, host, port, *, timeout, context):
            observed["host"] = host
            observed["port"] = port
            observed["timeout"] = timeout
            observed["context"] = context

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def login(self, username, password):
            observed["username"] = username
            observed["password"] = password

        def send_message(self, sent_message):
            observed["message"] = sent_message

    monkeypatch.setattr(sender_module.ssl, "create_default_context", lambda: tls_context)
    monkeypatch.setattr(sender_module.smtplib, "SMTP_SSL", FakeSMTP)

    sender._send_blocking(message)

    assert observed["context"] is tls_context
    assert observed["host"] == "smtp.gmail.com"
    assert observed["port"] == 465
    assert observed["password"] == "secret"


def test_build_message_removes_subject_newlines() -> None:
    settings = Settings(
        SMTP_FROM_EMAIL="me@example.com",
        SMTP_USERNAME="me@example.com",
        SMTP_PASSWORD="secret",
    )
    sender = EmailSender(settings)
    contact = Contact(email="hr@example.com", company_name="Example")
    generated = GeneratedEmail(
        subject="Role fit\nBcc: attacker@example.com",
        body="Hello, would you be open to a quick conversation?",
        personalization_notes=[],
        confidence=0.8,
        warnings=[],
    )

    message = sender.build_message(contact, generated)

    assert message["Subject"] == "Role fit Bcc: attacker@example.com"
