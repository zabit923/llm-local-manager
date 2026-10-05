from pydantic import ValidationError

from src.application.agent.catalog.dto import CatalogEntry
from src.application.agent.catalog.matcher import CatalogMatcher
from src.application.agent.conversation.state import ConversationState
from src.application.agent.execution.cart import CartActions
from src.application.agent.execution.fulfillment import FulfillmentActions
from src.application.agent.execution.reasons import ActionReason
from src.application.agent.execution.schema import ActionProposal
from src.domain.models.choises.enum import DeliveryType


class ActionExecutor:
    def __init__(self, catalog: CatalogMatcher) -> None:
        cart = CartActions(catalog)
        fulfillment = FulfillmentActions()
        self._handlers = {
            "add_item": cart.add_item,
            "remove_item": cart.remove_item,
            "set_quantity": cart.set_quantity,
            "set_branch": fulfillment.set_branch,
            "set_delivery": fulfillment.set_delivery,
            "set_address": fulfillment.set_address,
        }

    async def apply(
        self,
        plan: dict,
        text: str,
        state: ConversationState,
        entries: list[CatalogEntry],
    ) -> list[dict[str, object]]:
        by_sku = {entry.sku: entry for entry in entries}
        events = []
        for action in plan.get("actions", [])[:8]:
            if not isinstance(action, dict):
                continue
            try:
                action = ActionProposal.model_validate(action).model_dump()
            except ValidationError:
                events.append(
                    {
                        "action": str(action.get("name")),
                        "status": "rejected",
                        "reason": ActionReason.INVALID_ACTION_SHAPE,
                    }
                )
                continue
            handler = self._handlers.get(action.get("name"))
            if handler is None:
                events.append(
                    {
                        "action": str(action.get("name")),
                        "status": "rejected",
                        "reason": ActionReason.UNKNOWN_ACTION,
                    }
                )
                continue
            events.append(await handler(action, text, state, by_sku))
        suggestion = plan.get("suggested_delivery")
        if suggestion in ("pickup", "delivery") and state.delivery_type is None:
            state.suggested_delivery = DeliveryType(suggestion)
        return events
