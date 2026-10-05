from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from src.domain.types.abs.base_value import BaseValueObject


@dataclass(frozen=True, slots=True)
class MinorAmount(BaseValueObject):
    value: int

    def _validate(self) -> None:
        if not isinstance(self.value, int):
            raise TypeError(
                "MinorAmount.value must be int, got "
                f"{type(self.value).__name__}"
            )
        if self.value < 0:
            raise ValueError(
                f"MinorAmount.value must be >= 0, got {self.value}"
            )

    def __add__(self, other: MinorAmount) -> MinorAmount:
        if not isinstance(other, MinorAmount):
            return NotImplemented
        return MinorAmount(self.value + other.value)

    def __sub__(self, other: MinorAmount) -> MinorAmount:
        if not isinstance(other, MinorAmount):
            return NotImplemented
        result = self.value - other.value
        if result < 0:
            raise ValueError(
                f"MinorAmount subtraction result is negative: "
                f"{self.value} - {other.value} = {result}"
            )
        return MinorAmount(result)

    def __mul__(self, factor: int) -> MinorAmount:
        if not isinstance(factor, int):
            return NotImplemented
        result = self.value * factor
        if result < 0:
            raise ValueError(
                f"MinorAmount multiplication result is negative: {result}"
            )
        return MinorAmount(result)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MinorAmount):
            return NotImplemented
        return self.value == other.value

    def __lt__(self, other: MinorAmount) -> bool:
        if not isinstance(other, MinorAmount):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: MinorAmount) -> bool:
        if not isinstance(other, MinorAmount):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other: MinorAmount) -> bool:
        if not isinstance(other, MinorAmount):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: MinorAmount) -> bool:
        if not isinstance(other, MinorAmount):
            return NotImplemented
        return self.value >= other.value

    def to_decimal(self) -> Decimal:
        """Копейки → рубли как Decimal. Для отображения и записи в Money."""
        return (Decimal(self.value) / Decimal(100)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_EVEN
        )

    def __bool__(self) -> bool:
        return self.value != 0

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"MinorAmount(value={self.value})"

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def zero(cls) -> MinorAmount:
        return cls(0)

    @classmethod
    def from_decimal(cls, amount: Decimal) -> MinorAmount:
        result = int((amount * 100).to_integral_value(rounding=ROUND_HALF_EVEN))
        return cls(result)
