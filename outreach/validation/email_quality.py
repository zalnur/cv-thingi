"""Deterministic email quality and safety checks."""

import re

from outreach.models import Contact, GeneratedEmail, ValidationResult


SPAM_PHRASES = {
    "act now",
    "free",
    "guaranteed",
    "limited time",
    "limited time offer",
    "once-in-a-lifetime",
    "revolutionary",
    "urgent",
}
SPAM_PATTERNS = {phrase: re.compile(rf"\b{re.escape(phrase)}\b") for phrase in SPAM_PHRASES}
WORD_PATTERN = re.compile(r"\b[\w'-]+\b")


def validate_generated_email(generated: GeneratedEmail, contact: Contact) -> ValidationResult:
    """Validate AI output before writing or sending."""
    errors: list[str] = []
    warnings: list[str] = []
    subject = generated.subject.strip()
    body = generated.body.strip()
    lower_text = f"{subject} {body}".lower()

    if subject.lower().startswith(("re:", "fwd:")):
        errors.append("Subject must not use deceptive Re: or Fwd: prefix.")
    if len(subject) > 60:
        warnings.append("Subject is longer than 60 characters.")
    for phrase, pattern in SPAM_PATTERNS.items():
        if pattern.search(lower_text):
            errors.append(f"Spam-like phrase detected: {phrase}")

    word_count = len(WORD_PATTERN.findall(body))
    if word_count < 35:
        warnings.append("Body is very short; personalization may be thin.")
    if word_count > 150:
        errors.append("Body exceeds 150 words.")

    if "?" not in body:
        warnings.append("Body does not include a clear question/CTA.")
    if generated.confidence < 0.45:
        errors.append("AI confidence is too low to send automatically.")
    if not _has_specific_context(generated, contact):
        warnings.append("Email may lack company/role-specific context.")

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def _has_specific_context(generated: GeneratedEmail, contact: Contact) -> bool:
    text = f"{generated.subject} {generated.body}".lower()
    candidates = [contact.company_name, contact.role, contact.domain.split(".")[0]]
    return any(value and value.lower() in text for value in candidates)
