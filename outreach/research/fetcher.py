"""Respectful public HTTP research for company/job pages."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup  # type: ignore[import-untyped]

from outreach.models import Contact, ResearchResult


ROBOTS_USER_AGENT = "AIJobOutreachBot"
USER_AGENT = f"{ROBOTS_USER_AGENT}/1.0 respectful-contact-research"
MAX_REDIRECTS = 3
MAX_RESPONSE_BYTES = 1_000_000
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
MIN_TIMEOUT_SECONDS = 1.0
MAX_TIMEOUT_SECONDS = 30.0
MIN_PAGE_CHARS = 1_000
MAX_PAGE_CHARS = 50_000


@dataclass(frozen=True, slots=True)
class PublicUrl:
    """A URL whose host resolves only to public internet addresses."""

    url: str
    origin: str


class ResearchClient:
    """Fetch public website and job posting text with conservative limits."""

    def __init__(self, *, timeout_seconds: float, max_page_chars: int) -> None:
        self._timeout_seconds = min(max(timeout_seconds, MIN_TIMEOUT_SECONDS), MAX_TIMEOUT_SECONDS)
        self._max_page_chars = min(max(max_page_chars, MIN_PAGE_CHARS), MAX_PAGE_CHARS)
        self._client: httpx.AsyncClient | None = None
        self._robots_cache: dict[str, RobotFileParser | None] = {}
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "ResearchClient":
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout_seconds),
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
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
        public_url, warning = await self._validate_public_url(url)
        if public_url is None:
            return "", warning or "Invalid URL."
        allowed = await self._allowed_by_robots(public_url)
        if not allowed:
            return "", "Skipped because robots.txt disallows fetching."
        try:
            response, warning = await self._get_with_public_redirects(public_url)
            if warning or response is None:
                return "", warning or "Fetch failed."
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return "", f"Fetch failed: {exc.__class__.__name__}"
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return "", f"Skipped non-text content type: {content_type or 'unknown'}"
        return self._html_to_text(response.text), None

    async def _get_with_public_redirects(self, public_url: PublicUrl) -> tuple[httpx.Response | None, str | None]:
        if not self._client:
            raise RuntimeError("ResearchClient must be used as an async context manager.")
        current = public_url
        for _ in range(MAX_REDIRECTS + 1):
            async with self._client.stream("GET", current.url) as response:
                if response.status_code in REDIRECT_STATUS_CODES:
                    location = response.headers.get("location")
                    if not location:
                        body, warning = await _read_limited_response(response)
                        if warning:
                            return None, warning
                        return _copy_response(response, body), None
                    redirected_url = urljoin(current.url, location)
                    next_url, warning = await self._validate_public_url(redirected_url)
                    if next_url is None:
                        return None, f"Blocked unsafe redirect: {warning}"
                    current = next_url
                    continue
                body, warning = await _read_limited_response(response)
                if warning:
                    return None, warning
                return _copy_response(response, body), None
        return None, "Too many redirects."

    async def _allowed_by_robots(self, public_url: PublicUrl) -> bool:
        async with self._lock:
            if public_url.origin in self._robots_cache:
                parser = self._robots_cache[public_url.origin]
            else:
                parser = await self._load_robots(public_url.origin)
                self._robots_cache[public_url.origin] = parser
        return True if parser is None else parser.can_fetch(ROBOTS_USER_AGENT, public_url.url)

    async def _load_robots(self, origin: str) -> RobotFileParser | None:
        if not self._client:
            return None
        robots_url = f"{origin}/robots.txt"
        public_url, warning = await self._validate_public_url(robots_url)
        if public_url is None:
            return None
        try:
            response, warning = await self._get_with_public_redirects(public_url)
            if warning or response is None:
                return None
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

    async def _validate_public_url(self, url: str) -> tuple[PublicUrl | None, str | None]:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None, "Invalid URL."
        if parsed.username or parsed.password:
            return None, "URL credentials are not allowed."
        try:
            host = parsed.hostname
            port = parsed.port
        except ValueError:
            return None, "Invalid URL port."
        if not host:
            return None, "Invalid URL host."
        try:
            normalized_host = host.encode("idna").decode("ascii").lower()
        except UnicodeError:
            return None, "Invalid URL host."
        if not await asyncio.to_thread(_host_resolves_publicly, normalized_host, port):
            return None, "Blocked non-public host."

        netloc = normalized_host if port is None else f"{normalized_host}:{port}"
        normalized = parsed._replace(netloc=netloc, fragment="")
        origin = urlunparse((normalized.scheme, normalized.netloc, "", "", "", ""))
        return PublicUrl(url=urlunparse(normalized), origin=origin), None


def _host_resolves_publicly(host: str, port: int | None) -> bool:
    try:
        infos = socket.getaddrinfo(host, port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    addresses = {str(info[4][0]) for info in infos}
    return bool(addresses) and all(_is_public_ip(address) for address in addresses)


async def _read_limited_response(response: httpx.Response) -> tuple[bytes, str | None]:
    body = bytearray()
    async for chunk in response.aiter_bytes():
        body.extend(chunk)
        if len(body) > MAX_RESPONSE_BYTES:
            return b"", "Skipped response exceeding size limit."
    return bytes(body), None


def _copy_response(response: httpx.Response, body: bytes) -> httpx.Response:
    return httpx.Response(
        status_code=response.status_code,
        headers=response.headers,
        content=body,
        request=response.request,
        extensions=response.extensions,
    )


def _is_public_ip(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return ip.is_global and not (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )
