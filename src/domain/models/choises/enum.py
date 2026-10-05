# pylint: disable=invalid-name
from enum import Enum


class DeliveryType(Enum):
    pickup = "pickup"
    delivery = "delivery"


class PaymentMethod(Enum):
    cash = "cash"
    card = "card"


class OrderStatus(Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    ready = "ready"
    delivering = "delivering"
    completed = "completed"
    cancelled = "cancelled"
