from pydantic import BaseModel, Field

from src.domain.models import PaymentMethod
from src.domain.models.choises.enum import DeliveryType


class OrderItemState(BaseModel):
    dish_id: str | None = None
    drink_id: str | None = None
    quantity: int = Field(gt=0)


class OrderState(BaseModel):
    customer_name: str | None = None
    phone: str
    items: list[OrderItemState] = Field(min_length=1)
    comment: str | None

    delivery_type: str = DeliveryType.delivery.value
    address: str | None

    payment_method: str = PaymentMethod.cash.value
    total_price_minor: int = Field(ge=0)
