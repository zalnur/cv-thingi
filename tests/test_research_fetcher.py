import httpx
import pytest

import outreach.research.fetcher as fetcher
from outreach.research.fetcher import ResearchClient


def test_html_to_text_removes_script() -> None:
    client = ResearchClient(timeout_seconds=1, max_page_chars=100)

    text = client._html_to_text("<html><script>alert(1)</script><body><h1>Hello</h1></body></html>")

    assert text == "Hello"


@pytest.mark.parametrize(
    ("url", "warning"),
    [
        ("ftp://example.com/file", "Invalid URL."),
        ("https://user:pass@example.com", "URL credentials are not allowed."),
        ("https://localhost", "Blocked non-public host."),
        ("https://127.0.0.1", "Blocked non-public host."),
        ("https://[::1]", "Blocked non-public host."),
        ("https://10.0.0.1", "Blocked non-public host."),
        ("https://192.168.1.5", "Blocked non-public host."),
        ("https://169.254.1.1", "Blocked non-public host."),
    ],
)
@pytest.mark.asyncio
async def test_validate_public_url_blocks_unsafe_destinations(monkeypatch: pytest.MonkeyPatch, url: str, warning: str) -> None:
    monkeypatch.setattr(fetcher, "_host_resolves_publicly", lambda host, port: host == "example.com")
    client = ResearchClient(timeout_seconds=1, max_page_chars=1000)

    public_url, actual_warning = await client._validate_public_url(url)

    assert public_url is None
    assert actual_warning == warning


@pytest.mark.asyncio
async def test_fetch_text_allows_public_html(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetcher, "_host_resolves_publicly", lambda host, port: host == "example.com")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<h1>Hello</h1>")

    client = ResearchClient(timeout_seconds=1, max_page_chars=1000)
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)
    try:
        text, warning = await client.fetch_text("https://example.com")
    finally:
        await client._client.aclose()

    assert text == "Hello"
    assert warning is None


@pytest.mark.asyncio
async def test_fetch_text_blocks_redirect_to_private_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetcher, "_host_resolves_publicly", lambda host, port: host == "example.com")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})

    client = ResearchClient(timeout_seconds=1, max_page_chars=1000)
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)
    try:
        text, warning = await client.fetch_text("https://example.com")
    finally:
        await client._client.aclose()

    assert text == ""
    assert warning == "Blocked unsafe redirect: Blocked non-public host."


@pytest.mark.asyncio
async def test_fetch_text_respects_robots(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetcher, "_host_resolves_publicly", lambda host, port: host == "example.com")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                headers={"content-type": "text/plain"},
                text="User-agent: AIJobOutreachBot\nDisallow: /private\n",
            )
        return httpx.Response(200, headers={"content-type": "text/html"}, text="blocked")

    client = ResearchClient(timeout_seconds=1, max_page_chars=1000)
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)
    try:
        text, warning = await client.fetch_text("https://example.com/private")
    finally:
        await client._client.aclose()

    assert text == ""
    assert warning == "Skipped because robots.txt disallows fetching."


@pytest.mark.asyncio
async def test_fetch_text_rejects_oversized_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetcher, "_host_resolves_publicly", lambda host, port: host == "example.com")
    oversized_body = b"a" * (fetcher.MAX_RESPONSE_BYTES + 1)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, headers={"content-type": "text/plain"}, content=oversized_body)

    client = ResearchClient(timeout_seconds=1, max_page_chars=1000)
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)
    try:
        text, warning = await client.fetch_text("https://example.com")
    finally:
        await client._client.aclose()

    assert text == ""
    assert warning == "Skipped response exceeding size limit."
