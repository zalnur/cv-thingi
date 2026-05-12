from pathlib import Path

import pytest
from pypdf import PdfWriter

from outreach.resume import parser
from outreach.resume.parser import load_resume_profile


def test_load_resume_profile_txt_and_portfolio(tmp_path: Path) -> None:
    resume = tmp_path / "resume.txt"
    portfolio = tmp_path / "profile.md"
    resume.write_text("Python automation engineer", encoding="utf-8")
    portfolio.write_text("GitHub: example", encoding="utf-8")

    profile = load_resume_profile(resume, portfolio, max_chars=1000)

    assert "Python automation" in profile.resume_text
    assert "GitHub" in profile.portfolio_text


def test_load_resume_profile_rejects_empty_text(tmp_path: Path) -> None:
    resume = tmp_path / "resume.txt"
    resume.write_text("   ", encoding="utf-8")

    with pytest.raises(ValueError, match="No text"):
        load_resume_profile(resume, None, max_chars=1000)


def test_load_resume_profile_rejects_oversized_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parser, "MAX_INPUT_FILE_BYTES", 4)
    resume = tmp_path / "resume.txt"
    resume.write_text("Python automation engineer", encoding="utf-8")

    with pytest.raises(ValueError, match="exceeds"):
        load_resume_profile(resume, None, max_chars=1000)


def test_load_resume_profile_rejects_large_pdf_page_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parser, "MAX_PDF_PAGES", 1)
    resume = tmp_path / "resume.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with resume.open("wb") as handle:
        writer.write(handle)

    with pytest.raises(ValueError, match="page limit"):
        load_resume_profile(resume, None, max_chars=1000)
