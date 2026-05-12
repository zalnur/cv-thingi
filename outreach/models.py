"""Typed domain models used across the outreach pipeline."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator


class Tone(str, Enum):
    """Supported email tone controls."""

    warm = "warm"
    technical = "technical"
    concise = "concise"
    professional = "professional"

    @classmethod
    def from_csv(cls, value: str | None) -> "Tone":
        normalized = (value or "").strip().lower()
        aliases = {
            "": cls.warm,
            "warm": cls.warm,
            "friendly": cls.warm,
            "technical": cls.technical,
            "tech": cls.technical,
            "concise": cls.concise,
            "short": cls.concise,
            "professional": cls.professional,
        }
        return aliases.get(normalized, cls.warm)


class Contact(BaseModel):
    """One outreach recipient loaded from CSV."""

    email: EmailStr
    company_name: str | None = None
    tone: Tone = Tone.warm
    contact_name: str | None = None
    role: str | None = None
    job_url: HttpUrl | None = None
    website_url: HttpUrl | None = None
    notes: str | None = None

    @field_validator("company_name", "contact_name", "role", "notes", mode="before")
    @classmethod
    def blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def domain(self) -> str:
        return self.email.split("@", maxsplit=1)[1].lower()

    @property
    def inferred_website(self) -> str:
        return str(self.website_url) if self.website_url else f"https://{self.domain}"

    @property
    def safe_company_name(self) -> str:
        return self.company_name or self.domain


@dataclass(slots=True)
class ResearchResult:
    """Public context collected for a company."""

    company_text: str = ""
    job_text: str = ""
    sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResumeProfile:
    """Resume and optional portfolio text."""

    resume_text: str
    portfolio_text: str = ""
    source_paths: list[Path] = field(default_factory=list)


class GeneratedEmail(BaseModel):
    """Structured model output for one outreach email."""

    subject: str = Field(min_length=3, max_length=90)
    body: str = Field(min_length=20)
    personalization_notes: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class ValidationResult:
    """Result from deterministic quality checks."""

    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
