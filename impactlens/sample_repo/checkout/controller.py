"""Checkout flow: turns a cart into an authorized payment."""

from payments.service import PaymentService


class CheckoutController:
    def __init__(self):
        self.payment_service = PaymentService()

    def checkout(self, cart, payment):
        payment["amount"] = cart["total"]
        return self.payment_service.authorize(payment)
