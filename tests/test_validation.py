from outreach.models import Contact, GeneratedEmail
from outreach.validation.email_quality import validate_generated_email


def test_validation_rejects_spam_phrase() -> None:
    contact = Contact(email="hr@example.com", company_name="Example")
    generated = GeneratedEmail(
        subject="Urgent role fit",
        body="I saw Example is hiring. This is guaranteed to help. Open to a quick chat?",
        personalization_notes=["company"],
        confidence=0.9,
        warnings=[],
    )

    result = validate_generated_email(generated, contact)

    assert not result.ok
    assert any("Spam-like" in error for error in result.errors)


def test_validation_accepts_concise_email() -> None:
    contact = Contact(email="hr@example.com", company_name="Example", role="Backend Engineer")
    generated = GeneratedEmail(
        subject="Backend engineer fit for Example",
        body=(
            "Hi, I saw Example is hiring for a Backend Engineer. "
            "My background is in Python automation, APIs, and AI workflow tooling. "
            "I have built production scripts that cleanly connect research, model outputs, and email workflows. "
            "That seems relevant to the role's need for reliable backend systems. "
            "Would you be open to a quick conversation this week?"
        ),
        personalization_notes=["role match"],
        confidence=0.8,
        warnings=[],
    )

    result = validate_generated_email(generated, contact)

    assert result.ok
