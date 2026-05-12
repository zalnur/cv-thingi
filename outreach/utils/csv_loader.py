"""CSV input parsing."""

import csv
from pathlib import Path

from pydantic import ValidationError

from outreach.models import Contact, Tone


MAX_CONTACT_ROWS = 1000
MAX_FIELD_CHARS = 2000

HEADER_MAP = {
    "email": "email",
    "company name": "company_name",
    "company": "company_name",
    "tone": "tone",
    "contact name": "contact_name",
    "name": "contact_name",
    "role": "role",
    "job url": "job_url",
    "job posting": "job_url",
    "website url": "website_url",
    "website": "website_url",
    "notes": "notes",
}


def load_contacts(path: Path) -> list[Contact]:
    """Load contacts from a CSV file."""
    if not path.exists():
        raise FileNotFoundError(f"Contacts CSV not found: {path}")
    if not path.is_file():
        raise ValueError(f"Contacts path is not a file: {path}")
    contacts: list[Contact] = []
    previous_field_limit = csv.field_size_limit()
    csv.field_size_limit(MAX_FIELD_CHARS)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        try:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("Contacts CSV has no header row.")
            _validate_row_values(dict.fromkeys(reader.fieldnames, ""), row_number=1)
            for row_number, row in enumerate(reader, start=2):
                if row_number - 1 > MAX_CONTACT_ROWS:
                    raise ValueError(f"Contacts CSV exceeds the limit of {MAX_CONTACT_ROWS} contacts.")
                _validate_row_values(row, row_number=row_number)
                normalized = _normalize_row(row)
                if not normalized.get("email"):
                    raise ValueError(f"Row {row_number} is missing required Email.")
                tone_value = normalized.get("tone")
                normalized["tone"] = Tone.from_csv(tone_value if isinstance(tone_value, str) else None)
                try:
                    contacts.append(Contact.model_validate(normalized))
                except ValidationError as exc:
                    raise ValueError(f"Invalid contact row {row_number}: {exc}") from exc
        except csv.Error as exc:
            raise ValueError(f"Invalid contacts CSV: {exc}") from exc
        finally:
            csv.field_size_limit(previous_field_limit)
    if not contacts:
        raise ValueError("Contacts CSV contains no contacts.")
    return contacts


def _validate_row_values(row: dict[str, str | None], *, row_number: int) -> None:
    for key, value in row.items():
        if key is not None and len(key) > MAX_FIELD_CHARS:
            raise ValueError(f"Row {row_number} contains a header exceeding {MAX_FIELD_CHARS} characters.")
        if value is not None and len(value) > MAX_FIELD_CHARS:
            raise ValueError(f"Row {row_number} contains a field exceeding {MAX_FIELD_CHARS} characters.")


def _normalize_row(row: dict[str, str | None]) -> dict[str, object]:
    return {
        mapped: (value or "").strip()
        for key, value in row.items()
        if (mapped := HEADER_MAP.get((key or "").strip().lower()))
    }
