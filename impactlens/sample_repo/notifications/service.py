"""Customer notification helpers -- deliberately isolated, no other module
depends on this yet, and it's fully unit tested. Used as the LOW-risk demo
scenario: a self-contained change with no blast radius."""


def format_receipt_subject(order_id: str) -> str:
    return f"Your receipt for order #{order_id}"


def send_receipt_email(order_id: str, email: str) -> dict:
    return {
        "to": email,
        "subject": format_receipt_subject(order_id),
        "sent": True,
    }
