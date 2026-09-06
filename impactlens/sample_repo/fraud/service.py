"""Fraud detection service."""


class FraudService:
    def check(self, payment):
        """Return True if the payment looks fraudulent."""
        if payment.get("amount", 0) > 10000:
            return True
        if payment.get("card_country") != payment.get("billing_country"):
            return True
        return False

    def check_3ds(self, payment):
        """Check 3D Secure authentication result."""
        return payment.get("three_ds_status") == "authenticated"
