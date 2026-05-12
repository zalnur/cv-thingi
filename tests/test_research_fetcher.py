from outreach.research.fetcher import ResearchClient


def test_html_to_text_removes_script() -> None:
    client = ResearchClient(timeout_seconds=1, max_page_chars=100)

    text = client._html_to_text("<html><script>alert(1)</script><body><h1>Hello</h1></body></html>")

    assert text == "Hello"
