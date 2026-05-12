"""CSV input parsing."""

import csv
from pathlib import Path

from pydantic import ValidationError

from outreach.models import Contact, Tone


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
    contacts: list[Contact] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Contacts CSV has no header row.")
        for row_number, row in enumerate(reader, start=2):
            normalized = _normalize_row(row)
            if not normalized.get("email"):
                raise ValueError(f"Row {row_number} is missing required Email.")
            normalized["tone"] = Tone.from_csv(normalized.get("tone"))
            try:
                contacts.append(Contact.model_validate(normalized))
            except ValidationError as exc:
                raise ValueError(f"Invalid contact row {row_number}: {exc}") from exc
    if not contacts:
        raise ValueError("Contacts CSV contains no contacts.")
    return contacts


def _normalize_row(row: dict[str, str | None]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in row.items():
        mapped = HEADER_MAP.get((key or "").strip().lower())
        if mapped:
            normalized[mapped] = (value or "").strip()
    return normalized
