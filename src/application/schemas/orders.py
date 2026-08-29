from pydantic import BaseModel

from src.domain.models import PaymentMethod
from src.domain.models.choises.enum import DeliveryType


class OrderState(BaseModel):
    customer_name: str | None
    phone: str
    items: list[dict[str, int]]
    comment: str | None

    delivery_type: str = DeliveryType.delivery.value
    address: str | None

    payment_method: str = PaymentMethod.cash.value
    total_price: float

