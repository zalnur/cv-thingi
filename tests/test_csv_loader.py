from pathlib import Path

from outreach.models import Tone
from outreach.utils import csv_loader
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


def test_load_contacts_rejects_directory(tmp_path: Path) -> None:
    try:
        load_contacts(tmp_path)
    except ValueError as exc:
        assert "not a file" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_load_contacts_rejects_oversized_field(tmp_path: Path) -> None:
    csv_path = tmp_path / "contacts.csv"
    csv_path.write_text("Email,Notes\nhr@example.com," + ("x" * (csv_loader.MAX_FIELD_CHARS + 1)), encoding="utf-8")

    try:
        load_contacts(csv_path)
    except ValueError as exc:
        assert "field larger than field limit" in str(exc) or "exceeding" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_load_contacts_rejects_too_many_rows(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(csv_loader, "MAX_CONTACT_ROWS", 1)
    csv_path = tmp_path / "contacts.csv"
    csv_path.write_text("Email\none@example.com\ntwo@example.com\n", encoding="utf-8")

    try:
        load_contacts(csv_path)
    except ValueError as exc:
        assert "exceeds the limit" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
