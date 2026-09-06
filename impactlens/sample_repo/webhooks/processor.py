"""Handles asynchronous payment webhook retries."""

from payments.service import PaymentService


class WebhookProcessor:
    def __init__(self):
        self.payment_service = PaymentService()

    def handle_payment_webhook(self, event):
        payment = event["payment"]
        if self.payment_service.validate(payment):
            return self.payment_service.authorize(payment)
        return None

    def retry(self, event, attempts=3):
        for _ in range(attempts):
            result = self.handle_payment_webhook(event)
            if result:
                return result
        return None
