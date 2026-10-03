"""Validate model-proposed actions against the customer's words and menu."""

from __future__ import annotations

import re

from src.application.agent.catalog import (
    CatalogEntry,
    CatalogMatcher,
    QuantityParser,
)
from src.application.agent.constants import BRANCHES, NUMBER_WORDS
from src.application.agent.state import CartLine, ConversationState
from src.domain.models.choises.enum import DeliveryType


def _said(text: str, evidence: object) -> bool:
    return (
        isinstance(evidence, str)
        and len(evidence.strip()) >= 2
        and evidence.lower().strip() in text.lower()
    )


def _quantity_was_said(text: str) -> bool:
    if re.search(r"\b\d{1,2}\b", text):
        return True
    return any(
        re.search(rf"\b{word}\w*\b", text.lower()) for word in NUMBER_WORDS
    )


class ActionExecutor:
    def __init__(self, catalog: CatalogMatcher) -> None:
        self._catalog = catalog

    async def apply(
        self,
        plan: dict,
        text: str,
        state: ConversationState,
        entries: list[CatalogEntry],
    ) -> list[dict[str, object]]:
        by_sku = {entry.sku: entry for entry in entries}
        events: list[dict[str, object]] = []
        actions = plan.get("actions", [])[:8]
        for action in actions:
            if not isinstance(action, dict):
                continue
            name = action.get("name")
            if name == "add_item":
                event = await self._add_item(action, text, state, by_sku)
            elif name == "remove_item":
                event = await self._remove_item(action, text, state, by_sku)
            elif name == "set_quantity":
                event = await self._set_quantity(action, text, state, by_sku)
            elif name == "set_branch":
                event = self._set_branch(action, text, state)
            elif name == "set_delivery":
                event = self._set_delivery(action, text, state)
            elif name == "set_address":
                event = self._set_address(action, text, state)
            else:
                event = {
                    "action": str(name),
                    "status": "rejected",
                    "reason": "unknown action",
                }
            events.append(event)
        suggestion = plan.get("suggested_delivery")
        if suggestion in ("pickup", "delivery") and state.delivery_type is None:
            state.suggested_delivery = DeliveryType(suggestion)
        return events

    async def _add_item(
        self,
        action: dict,
        text: str,
        state: ConversationState,
        entries: dict[str, CatalogEntry],
    ) -> dict[str, object]:
        entry = entries.get(action.get("sku"))
        evidence = action.get("evidence")
        quantity = action.get("quantity")
        rejected = {"action": "add_item", "status": "rejected"}
        if entry is None or not entry.item.is_available:
            return {**rejected, "reason": "item unavailable or unknown"}
        if not isinstance(quantity, int) or not 1 <= quantity <= 20:
            return {**rejected, "reason": "invalid quantity"}
        if not _said(text, evidence):
            return {**rejected, "reason": "item not heard from customer"}
        match = await self._catalog.find(evidence)
        if match is None or match.item.id != entry.item.id:
            return {**rejected, "reason": "ambiguous or mismatched item"}
        if _quantity_was_said(evidence):
            if QuantityParser.parse(evidence) != quantity:
                return {**rejected, "reason": "quantity mismatch"}
        elif quantity != 1:
            return {**rejected, "reason": "quantity not heard"}
        line = next(
            (line for line in state.lines if line.item_id == entry.item.id),
            None,
        )
        if line is None:
            state.lines.append(
                CartLine(
                    item_id=entry.item.id,
                    kind=entry.kind,
                    name=entry.item.name,
                    unit_price_minor=entry.item.price_minor,
                    quantity=quantity,
                )
            )
        else:
            line.quantity += quantity
        return {
            "action": "add_item",
            "status": "applied",
            "item": entry.item.name,
            "quantity": quantity,
        }

    async def _remove_item(
        self,
        action: dict,
        text: str,
        state: ConversationState,
        entries: dict[str, CatalogEntry],
    ) -> dict[str, object]:
        entry = entries.get(action.get("sku"))
        matched = await self._catalog.find(text)
        if (
            entry
            and re.search(
                r"\b(убери|убрать|без|отмени|не надо)\b", text.lower()
            )
            and matched
            and matched.item.id == entry.item.id
        ):
            before = len(state.lines)
            state.lines = [
                line for line in state.lines if line.item_id != entry.item.id
            ]
            if len(state.lines) != before:
                return {
                    "action": "remove_item",
                    "status": "applied",
                    "item": entry.item.name,
                }
        return {
            "action": "remove_item",
            "status": "rejected",
            "reason": "removal not clear or item not in cart",
        }

    async def _set_quantity(
        self,
        action: dict,
        text: str,
        state: ConversationState,
        entries: dict[str, CatalogEntry],
    ) -> dict[str, object]:
        entry = entries.get(action.get("sku"))
        quantity = action.get("quantity")
        line = next(
            (
                line
                for line in state.lines
                if entry and line.item_id == entry.item.id
            ),
            None,
        )
        matched = await self._catalog.find(text)
        clear_reference = len(state.lines) == 1 or bool(
            entry and matched and matched.item.id == entry.item.id
        )
        if (
            line is not None
            and isinstance(quantity, int)
            and 1 <= quantity <= 20
            and _quantity_was_said(text)
            and QuantityParser.parse(text) == quantity
            and clear_reference
        ):
            line.quantity = quantity
            return {
                "action": "set_quantity",
                "status": "applied",
                "item": line.name,
                "quantity": quantity,
            }
        return {
            "action": "set_quantity",
            "status": "rejected",
            "reason": "quantity or item reference unclear",
        }

    @staticmethod
    def _set_branch(
        action: dict,
        text: str,
        state: ConversationState,
    ) -> dict[str, object]:
        branch = action.get("branch")
        evidence = action.get("evidence")
        if branch not in BRANCHES or not _said(text, evidence):
            return {
                "action": "set_branch",
                "status": "rejected",
                "reason": "branch not heard or unknown",
            }
        spoken = evidence.lower()
        valid = (branch == "Ермошкина" and "ермош" in spoken) or (
            branch == "Центральная" and "централ" in spoken
        )
        if not valid:
            return {
                "action": "set_branch",
                "status": "rejected",
                "reason": "branch evidence mismatch",
            }
        if state.branch is not None and state.branch != branch:
            if not re.search(
                r"\b(нет|поменяй|измени|точка|точку|филиал)\b",
                text.lower(),
            ):
                if (
                    state.delivery_type is DeliveryType.delivery
                    and state.address is None
                ):
                    state.address_street = evidence
                    return {
                        "action": "set_address",
                        "status": "incomplete",
                        "reason": "house number missing",
                        "street": evidence,
                    }
                return {
                    "action": "set_branch",
                    "status": "rejected",
                    "reason": "branch change not explicit",
                }
        state.branch = branch
        return {
            "action": "set_branch",
            "status": "applied",
            "branch": branch,
        }

    @staticmethod
    def _set_delivery(
        action: dict,
        text: str,
        state: ConversationState,
    ) -> dict[str, object]:
        value = action.get("value")
        evidence = action.get("evidence")
        if value not in ("pickup", "delivery") or not _said(text, evidence):
            return {
                "action": "set_delivery",
                "status": "rejected",
                "reason": "fulfillment choice not heard",
            }
        lowered = text.lower().strip()
        pickup = bool(
            re.search(
                r"самовыв|самовоз|самого|сам заберу|заберу|забрать",
                lowered,
            )
        )
        delivery = bool(re.search(r"достав|привез", lowered))
        agreed = lowered in (
            "да",
            "ага",
            "угу",
            "подойдёт",
            "подойдет",
            "согласен",
            "согласна",
            "хорошо",
        )
        declined = lowered in ("нет", "не подходит")
        if value == "pickup":
            valid = pickup or (
                agreed and state.suggested_delivery is DeliveryType.pickup
            )
        else:
            valid = (
                delivery
                or (
                    declined and state.suggested_delivery is DeliveryType.pickup
                )
                or (
                    agreed and state.suggested_delivery is DeliveryType.delivery
                )
            )
        if not valid:
            return {
                "action": "set_delivery",
                "status": "rejected",
                "reason": "choice not explicit",
            }
        state.delivery_type = DeliveryType(value)
        state.suggested_delivery = None
        return {
            "action": "set_delivery",
            "status": "applied",
            "value": value,
        }

    @staticmethod
    def _set_address(
        action: dict,
        text: str,
        state: ConversationState,
    ) -> dict[str, object]:
        if state.delivery_type is not DeliveryType.delivery:
            return {
                "action": "set_address",
                "status": "rejected",
                "reason": "address is allowed only for delivery",
            }
        value = action.get("value")
        if not isinstance(value, str) or not value.strip():
            return {
                "action": "set_address",
                "status": "rejected",
                "reason": "empty address",
            }
        spoken = text.lower().strip()
        value = value.strip()
        if state.address_street and re.fullmatch(r"\d+[а-яa-z]?", spoken):
            value = f"{state.address_street}, дом {text.strip()}"
            state.address = value
            return {
                "action": "set_address",
                "status": "applied",
                "address": value,
            }
        if value.lower() not in spoken:
            return {
                "action": "set_address",
                "status": "rejected",
                "reason": "address not heard from customer",
            }
        if not re.search(r"\b\d+[а-яa-z]?\b", value.lower()):
            if len(value) >= 4:
                state.address_street = value
            return {
                "action": "set_address",
                "status": "incomplete",
                "reason": "house number missing",
                "street": state.address_street,
            }
        if len(value.split()) < 2:
            return {
                "action": "set_address",
                "status": "rejected",
                "reason": "street missing",
            }
        state.address = value
        return {
            "action": "set_address",
            "status": "applied",
            "address": value,
        }
