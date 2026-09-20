from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domain.models.choises.enum import (
    DeliveryType,
    OrderStatus,
    PaymentMethod,
)


class OrderItemCreate(BaseModel):
    dish_id: UUID | None = None
    drink_id: UUID | None = None
    quantity: int = Field(gt=0)

    @model_validator(mode="after")
    def exactly_one_menu_item(self) -> "OrderItemCreate":
        if (self.dish_id is None) == (self.drink_id is None):
            raise ValueError("provide exactly one of dish_id or drink_id")
        return self


class OrderCreate(BaseModel):
    customer_name: str | None = Field(default=None, max_length=120)
    branch: str = Field(min_length=1, max_length=120)
    items: list[OrderItemCreate] = Field(min_length=1)
    comment: str | None = None

    delivery_type: DeliveryType = DeliveryType.delivery
    address: str | None = None
    payment_method: PaymentMethod = PaymentMethod.cash


class OrderItemQuantityUpdate(BaseModel):
    quantity: int = Field(gt=0)


class OrderItemDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dish_id: UUID | None
    drink_id: UUID | None
    title: str
    quantity: int
    unit_price_minor: int


class OrderDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: OrderStatus
    customer_name: str | None
    branch: str
    comment: str | None
    delivery_type: DeliveryType
    address: str | None
    payment_method: PaymentMethod
    total_price_minor: int
    items: list[OrderItemDetail]
