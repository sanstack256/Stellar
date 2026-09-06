from checkout.controller import CheckoutController
from refunds.service import RefundService


def test_checkout_success():
    controller = CheckoutController()
    cart = {"total": 42.0}
    payment = {"id": "p1", "card_country": "US", "billing_country": "US"}
    result = controller.checkout(cart, payment)
    assert result["status"] == "authorized"


def test_checkout_failure_high_amount():
    controller = CheckoutController()
    cart = {"total": 99999.0}
    payment = {"id": "p2", "card_country": "US", "billing_country": "US"}
    try:
        controller.checkout(cart, payment)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_refund():
    controller = CheckoutController()
    refund_service = RefundService()
    refund_service.payment_service = controller.payment_service
    cart = {"total": 20.0}
    payment = {"id": "p3", "card_country": "US", "billing_country": "US"}
    controller.checkout(cart, payment)
    refunded = refund_service.process_refund("p3")
    assert refunded["status"] == "refunded"
