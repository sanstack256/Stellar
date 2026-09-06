"""Refund processing."""

from payments.service import PaymentService


class RefundService:
    def __init__(self):
        self.payment_service = PaymentService()

    def process_refund(self, payment_id):
        return self.payment_service.refund(payment_id)
