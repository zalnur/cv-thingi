"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for AI generation, research, and email sending."""

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")

    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=465, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: EmailStr | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="", alias="SMTP_FROM_NAME")

    daily_send_limit: int = Field(default=10, alias="DAILY_SEND_LIMIT")
    seconds_between_sends: float = Field(default=60.0, alias="SECONDS_BETWEEN_SENDS")
    http_timeout_seconds: float = Field(default=12.0, alias="HTTP_TIMEOUT_SECONDS")
    max_page_chars: int = Field(default=12000, alias="MAX_PAGE_CHARS")
    max_resume_chars: int = Field(default=9000, alias="MAX_RESUME_CHARS")

    outputs_dir: Path = Path("outputs")
    logs_dir: Path = Path("logs")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("openai_model", "smtp_host", "smtp_username", "smtp_password", "smtp_from_name")
    @classmethod
    def strip_string_setting(cls, value: str) -> str:
        return value.strip()

    @field_validator("smtp_host")
    @classmethod
    def validate_smtp_host(cls, value: str) -> str:
        if not value or any(character.isspace() for character in value):
            raise ValueError("SMTP_HOST must be a non-empty hostname without whitespace.")
        return value

    @field_validator("smtp_port")
    @classmethod
    def validate_smtp_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("SMTP_PORT must be between 1 and 65535.")
        return value

    @field_validator("daily_send_limit")
    @classmethod
    def validate_daily_send_limit(cls, value: int) -> int:
        if not 1 <= value <= 100:
            raise ValueError("DAILY_SEND_LIMIT must be between 1 and 100.")
        return value

    @field_validator("seconds_between_sends")
    @classmethod
    def validate_seconds_between_sends(cls, value: float) -> float:
        if not 0 <= value <= 3600:
            raise ValueError("SECONDS_BETWEEN_SENDS must be between 0 and 3600.")
        return value

    @field_validator("http_timeout_seconds")
    @classmethod
    def validate_http_timeout_seconds(cls, value: float) -> float:
        if not 1 <= value <= 30:
            raise ValueError("HTTP_TIMEOUT_SECONDS must be between 1 and 30.")
        return value

    @field_validator("max_page_chars", "max_resume_chars")
    @classmethod
    def validate_text_limits(cls, value: int) -> int:
        if not 1000 <= value <= 50000:
            raise ValueError("Text limits must be between 1000 and 50000 characters.")
        return value

    def require_openai(self) -> None:
        """Raise when the OpenAI key is missing."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required. Add it to .env or the environment.")

    def require_smtp(self) -> None:
        """Raise when SMTP credentials are incomplete."""
        missing = [
            name
            for name, value in {
                "SMTP_USERNAME": self.smtp_username,
                "SMTP_PASSWORD": self.smtp_password,
                "SMTP_FROM_EMAIL": self.smtp_from_email,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"SMTP sending requires: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()
