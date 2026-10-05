import re

from src.application.agent.catalog.dto import CatalogEntry
from src.application.agent.catalog.matcher import CatalogMatcher, QuantityParser
from src.application.agent.config.language import REMOVAL_PATTERN
from src.application.agent.conversation.state import CartLine, ConversationState
from src.application.agent.execution.reasons import ActionReason
from src.application.agent.execution.validation import quantity_was_said, said


class CartActions:

    def __init__(self, catalog: CatalogMatcher) -> None:
        self._catalog = catalog

    async def add_item(
        self,
        action: dict,
        text: str,
        state: ConversationState,
        entries: dict[str, CatalogEntry],
    ) -> dict[str, object]:
        entry = entries.get(action.get("sku"))
        reason = await self._addition_error(action, text, entry)
        if reason:
            return {
                "action": "add_item",
                "status": "rejected",
                "reason": reason,
            }
        quantity = action["quantity"]
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

    async def _addition_error(
        self,
        action: dict,
        text: str,
        entry: CatalogEntry | None,
    ) -> str | None:
        evidence, quantity = action.get("evidence"), action.get("quantity")
        if entry is None or not entry.item.is_available:
            return ActionReason.ITEM_UNAVAILABLE_OR_UNKNOWN
        if (
            not isinstance(quantity, int)
            or isinstance(quantity, bool)
            or not 1 <= quantity <= 20
        ):
            return ActionReason.INVALID_QUANTITY
        if not said(text, evidence):
            return ActionReason.ITEM_NOT_HEARD_FROM_CUSTOMER
        match = await self._catalog.find(evidence)
        if match is None or match.item.id != entry.item.id:
            return ActionReason.AMBIGUOUS_OR_MISMATCHED_ITEM
        spoken_quantity = quantity_was_said(evidence)
        expected = QuantityParser.parse(evidence) if spoken_quantity else 1
        if quantity != expected:
            return (
                ActionReason.QUANTITY_MISMATCH
                if spoken_quantity
                else ActionReason.QUANTITY_NOT_HEARD
            )
        return None

    async def remove_item(
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
            and re.search(REMOVAL_PATTERN, text.lower())
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
            "reason": ActionReason.REMOVAL_NOT_CLEAR_OR_ITEM_NOT_IN_CART,
        }

    async def set_quantity(
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
        valid_quantity = (
            isinstance(quantity, int)
            and not isinstance(quantity, bool)
            and 1 <= quantity <= 20
        )
        if (
            line is not None
            and valid_quantity
            and quantity_was_said(text)
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
            "reason": ActionReason.QUANTITY_OR_ITEM_REFERENCE_UNCLEAR,
        }
