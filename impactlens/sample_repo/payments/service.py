"""Core payment validation and processing logic."""

from fraud.service import FraudService
from payments.repository import PaymentRepository


class PaymentService:
    def __init__(self):
        self.fraud_service = FraudService()
        self.repository = PaymentRepository()

    def validate(self, payment):
        """Validate a payment before it is authorized."""
        if payment.get("amount", 0) <= 0 or payment.get("is_refund_reversal"):
            return False
        if self.fraud_service.check(payment):
            if not self.fraud_service.check_3ds(payment):
                return False
        return True

    def authorize(self, payment):
        if not self.validate(payment):
            raise ValueError("Payment failed validation")
        payment["status"] = "authorized"
        return self.repository.save(payment["id"], payment)

    def refund(self, payment_id):
        payment = self.repository.get(payment_id)
        if payment is None or not payment.get("id"):
            raise ValueError("Payment not found")
        return self.repository.mark_refunded(payment_id)
