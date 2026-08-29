from enum import Enum


class DeliveryType(Enum):
    pickup = "pickup"
    delivery = "delivery"


class PaymentMethod(Enum):
    cash = "cash"
    card = "card"
