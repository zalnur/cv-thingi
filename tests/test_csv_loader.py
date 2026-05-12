from pathlib import Path

from outreach.models import Tone
from outreach.utils.csv_loader import load_contacts


def test_load_contacts_accepts_optional_fields(tmp_path: Path) -> None:
    csv_path = tmp_path / "contacts.csv"
    csv_path.write_text(
        "Email,Company Name,Tone,Role\nrecruiting@example.com,Example Co,Technical,Engineer\n",
        encoding="utf-8",
    )

    contacts = load_contacts(csv_path)

    assert len(contacts) == 1
    assert contacts[0].email == "recruiting@example.com"
    assert contacts[0].company_name == "Example Co"
    assert contacts[0].tone == Tone.technical


def test_load_contacts_requires_email(tmp_path: Path) -> None:
    csv_path = tmp_path / "contacts.csv"
    csv_path.write_text("Company Name\nExample Co\n", encoding="utf-8")

    try:
        load_contacts(csv_path)
    except ValueError as exc:
        assert "missing required Email" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
