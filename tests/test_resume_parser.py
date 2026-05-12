from pathlib import Path

from outreach.resume.parser import load_resume_profile


def test_load_resume_profile_txt_and_portfolio(tmp_path: Path) -> None:
    resume = tmp_path / "resume.txt"
    portfolio = tmp_path / "profile.md"
    resume.write_text("Python automation engineer", encoding="utf-8")
    portfolio.write_text("GitHub: example", encoding="utf-8")

    profile = load_resume_profile(resume, portfolio, max_chars=1000)

    assert "Python automation" in profile.resume_text
    assert "GitHub" in profile.portfolio_text
