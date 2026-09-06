"""Notification and email delivery service."""

def format_receipt_subject(order_id: str) -> str:
    return f"[Receipt] Order #{order_id}"

def send_receipt_email(order_id: str, email: str) -> bool:
    subject = format_receipt_subject(order_id)
    return bool(order_id and email)
