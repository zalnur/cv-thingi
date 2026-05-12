"""Respectful public HTTP research for company/job pages."""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from outreach.models import Contact, ResearchResult


class ResearchClient:
    """Fetch public website and job posting text with conservative limits."""

    def __init__(self, *, timeout_seconds: float, max_page_chars: int) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_page_chars = max_page_chars
        self._client: httpx.AsyncClient | None = None
        self._robots_cache: dict[str, RobotFileParser | None] = {}
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "ResearchClient":
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout_seconds),
            follow_redirects=True,
            headers={"User-Agent": "AIJobOutreachBot/1.0 respectful-contact-research"},
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self._client:
            await self._client.aclose()

    async def research(self, contact: Contact) -> ResearchResult:
        """Collect job and company text for one contact."""
        result = ResearchResult()
        if contact.job_url:
            text, warning = await self.fetch_text(str(contact.job_url))
            if text:
                result.job_text = text
                result.sources.append(str(contact.job_url))
            if warning:
                result.warnings.append(f"Job URL: {warning}")

        text, warning = await self.fetch_text(contact.inferred_website)
        if text:
            result.company_text = text
            result.sources.append(contact.inferred_website)
        if warning:
            result.warnings.append(f"Website: {warning}")

        return result

    async def fetch_text(self, url: str) -> tuple[str, str | None]:
        """Fetch and extract readable text from a public page."""
        if not self._client:
            raise RuntimeError("ResearchClient must be used as an async context manager.")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return "", "Invalid URL."
        allowed = await self._allowed_by_robots(url)
        if not allowed:
            return "", "Skipped because robots.txt disallows fetching."
        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return "", f"Fetch failed: {exc.__class__.__name__}"
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return "", f"Skipped non-text content type: {content_type or 'unknown'}"
        return self._html_to_text(response.text), None

    async def _allowed_by_robots(self, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        async with self._lock:
            if origin in self._robots_cache:
                parser = self._robots_cache[origin]
            else:
                parser = await self._load_robots(origin)
                self._robots_cache[origin] = parser
        return True if parser is None else parser.can_fetch("AIJobOutreachBot/1.0", url)

    async def _load_robots(self, origin: str) -> RobotFileParser | None:
        if not self._client:
            return None
        robots_url = f"{origin}/robots.txt"
        try:
            response = await self._client.get(robots_url)
            if response.status_code >= 400:
                return None
        except httpx.HTTPError:
            return None
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        return parser

    def _html_to_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        text = " ".join(soup.get_text(" ").split())
        return text[: self._max_page_chars]
