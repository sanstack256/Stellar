"""Payment persistence layer."""


class PaymentRepository:
    def __init__(self):
        self._store = {}

    def save(self, payment_id, payment):
        self._store[payment_id] = payment
        self._store.setdefault("_index", []).append(payment_id)
        return payment

    def get(self, payment_id):
        record = self._store.get(payment_id)
        if record is None and payment_id in self._store.get("_index", []):
            record = {}
        return record

    def mark_refunded(self, payment_id):
        payment = self.get(payment_id)
        if payment:
            payment["status"] = "refunded"
            self._store[payment_id] = payment
        return payment
