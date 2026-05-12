"""Prompt templates for AI-generated recruiting outreach."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from outreach.models import Contact


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = PROJECT_ROOT / "prompts"


def load_prompt_file(filename: str) -> str:
    """Load a prompt file from the project-level prompts directory."""
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Prompt file is empty: {path}")
    return text


def system_prompt() -> str:
    return load_prompt_file("system_prompt.md")


def build_user_prompt(
    *,
    contact: Contact,
    resume_text: str,
    portfolio_text: str,
    company_text: str,
    job_text: str,
    sources: list[str],
    research_warnings: list[str],
) -> str:
    """Build the user prompt with explicit delimiters and anti-hallucination context."""
    return f"""Create one personalized recruiting outreach email.

<recipient>
email: {contact.email}
company_name: {contact.company_name or ""}
contact_name: {contact.contact_name or ""}
role: {contact.role or ""}
tone: {contact.tone.value}
notes: {contact.notes or ""}
</recipient>

<sources>
{chr(10).join(sources) if sources else "No fetched sources."}
</sources>

<research_warnings>
{chr(10).join(research_warnings) if research_warnings else "None."}
</research_warnings>

<job_posting>
{job_text or "No job posting text was available."}
</job_posting>

<company_research>
{company_text or "No company website text was available."}
</company_research>

<resume>
{resume_text}
</resume>

<portfolio>
{portfolio_text or "No portfolio text was provided."}
</portfolio>

Personalization logic:
- Prefer matching the candidate's strongest resume evidence to the role/company context.
- If a specific job posting is available, mention the role and 1 relevant fit point.
- If only company website data is available, mention a concrete company area or product only if present in the text.
- If neither is available, keep personalization light and do not pretend to know details.
- For technical tone, emphasize concrete skills/projects.
- For warm tone, keep it personable but still concise.
- For concise tone, use the fewest words that remain specific.

Return this exact JSON shape:
{{
  "subject": "string",
  "body": "string",
  "personalization_notes": ["string"],
  "confidence": 0.0,
  "warnings": ["string"]
}}"""
