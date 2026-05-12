"""Command-line orchestration for the outreach workflow."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from outreach.ai.openai_client import OpenAIEmailGenerator
from outreach.config import get_settings
from outreach.email.sender import EmailSender
from outreach.models import Contact
from outreach.prompts import build_user_prompt, system_prompt
from outreach.research.fetcher import ResearchClient
from outreach.resume.parser import load_resume_profile
from outreach.utils.csv_loader import load_contacts
from outreach.utils.files import ensure_directories, slugify
from outreach.utils.logging import configure_logging
from outreach.utils.rate_limit import AsyncRateLimiter
from outreach.validation.email_quality import validate_generated_email


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate personalized AI job outreach emails.")
    parser.add_argument("--contacts", required=True, type=Path, help="CSV file with target contacts.")
    parser.add_argument("--resume", required=True, type=Path, help="Resume/CV file: PDF, TXT, or MD.")
    parser.add_argument("--portfolio", type=Path, help="Optional TXT/MD portfolio or profile file.")
    parser.add_argument("--send", action="store_true", help="Actually send emails through SMTP.")
    parser.add_argument("--limit", type=int, help="Maximum contacts to process this run.")
    parser.add_argument("--skip-research", action="store_true", help="Skip website/job HTTP research.")
    return parser


async def process_contact(
    contact: Contact,
    *,
    generator: OpenAIEmailGenerator,
    research_client: ResearchClient,
    sender: EmailSender,
    resume_text: str,
    portfolio_text: str,
    send: bool,
    output_dir: Path,
    send_limiter: AsyncRateLimiter,
    skip_research: bool,
) -> dict[str, object]:
    research = await research_client.research(contact) if not skip_research else None
    prompt = build_user_prompt(
        contact=contact,
        resume_text=resume_text,
        portfolio_text=portfolio_text,
        company_text=research.company_text if research else "",
        job_text=research.job_text if research else "",
        sources=research.sources if research else [],
        research_warnings=research.warnings if research else ["Research skipped by CLI flag."],
    )
    generated = await generator.generate_email(system_prompt(), prompt)
    validation = validate_generated_email(generated, contact)

    stem = slugify(f"{contact.safe_company_name}-{contact.email}")
    metadata = {
        "recipient": contact.model_dump(mode="json"),
        "email": generated.model_dump(),
        "validation": {
            "ok": validation.ok,
            "errors": validation.errors,
            "warnings": validation.warnings,
        },
        "research_sources": research.sources if research else [],
        "research_warnings": research.warnings if research else [],
    }
    json_path = output_dir / f"{stem}.json"
    eml_path = output_dir / f"{stem}.eml"
    json_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    sender.write_eml(contact, generated, eml_path)

    sent = False
    if send:
        if not validation.ok:
            raise ValueError(f"Refusing to send invalid email to {contact.email}: {validation.errors}")
        await send_limiter.wait()
        await sender.send(contact, generated)
        sent = True

    return {
        "email": str(contact.email),
        "company": contact.safe_company_name,
        "valid": validation.ok,
        "sent": sent,
        "json_path": str(json_path),
        "eml_path": str(eml_path),
        "warnings": validation.warnings + generated.warnings,
    }


async def run(args: argparse.Namespace) -> int:
    settings = get_settings()
    settings.require_openai()
    if args.send:
        settings.require_smtp()

    ensure_directories(settings.outputs_dir, settings.logs_dir, Path("data"))
    logger = configure_logging(settings.logs_dir)
    contacts = load_contacts(args.contacts)
    if args.limit:
        contacts = contacts[: args.limit]
    if args.send and len(contacts) > settings.daily_send_limit:
        raise ValueError(
            f"Refusing to send {len(contacts)} emails; DAILY_SEND_LIMIT is {settings.daily_send_limit}."
        )

    profile = load_resume_profile(args.resume, args.portfolio, max_chars=settings.max_resume_chars)
    generator = OpenAIEmailGenerator(settings.openai_api_key, settings.openai_model)
    sender = EmailSender(settings)
    send_limiter = AsyncRateLimiter(settings.seconds_between_sends)

    logger.info("Starting outreach run: contacts=%s send=%s", len(contacts), args.send)
    results: list[dict[str, object]] = []
    async with ResearchClient(
        timeout_seconds=settings.http_timeout_seconds,
        max_page_chars=settings.max_page_chars,
    ) as research_client:
        for contact in contacts:
            try:
                result = await process_contact(
                    contact,
                    generator=generator,
                    research_client=research_client,
                    sender=sender,
                    resume_text=profile.resume_text,
                    portfolio_text=profile.portfolio_text,
                    send=args.send,
                    output_dir=settings.outputs_dir,
                    send_limiter=send_limiter,
                    skip_research=args.skip_research,
                )
                results.append(result)
                logger.info("Processed %s valid=%s sent=%s", result["email"], result["valid"], result["sent"])
            except Exception:
                logger.exception("Failed processing %s", contact.email)

    summary_path = settings.outputs_dir / "run-summary.json"
    summary_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Processed {len(results)}/{len(contacts)} contacts. Summary: {summary_path}")
    if not args.send:
        print("Dry-run complete. No emails were sent.")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(run(args))
