from notifications.service import send_receipt_email, format_receipt_subject


def test_format_receipt_subject():
    assert format_receipt_subject("42") == "Your receipt for order #42"


def test_send_receipt_email():
    result = send_receipt_email("42", "buyer@example.com")
    assert result["sent"] is True
    assert result["to"] == "buyer@example.com"
