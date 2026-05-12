from outreach.utils.logging import mask_email


def test_mask_email_hides_local_part() -> None:
    assert mask_email("recruiting@example.com") == "re***@example.com"
    assert mask_email("a@example.com") == "a***@example.com"
