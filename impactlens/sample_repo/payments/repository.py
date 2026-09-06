"""Payment persistence layer."""


class PaymentRepository:
    def __init__(self):
        self._store = {}

    def save(self, payment_id, data):
        self._store[payment_id] = dict(data)
        return self._store[payment_id]

    def get(self, payment_id):
        return self._store.get(payment_id)

    def mark_refunded(self, payment_id):
        if payment_id not in self._store:
            return None
        self._store[payment_id]["status"] = "refunded"
        self._store[payment_id]["refunded_at"] = 1234567890
        return self._store[payment_id]
