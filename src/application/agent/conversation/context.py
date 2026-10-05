from src.application.agent.catalog.dto import CatalogEntry
from src.application.agent.catalog.matcher import CatalogMatcher
from src.application.agent.config.settings import BRANCHES, MAX_HISTORY_TURNS
from src.application.agent.conversation.dto import ConversationTurn
from src.application.agent.conversation.state import ConversationState
from src.application.agent.execution.validation import quantity_was_said
from src.application.agent.responses.money import money_message
from src.domain.models.choises.enum import DeliveryType
from src.domain.models.order import Order


class ContextBuilder:

    def __init__(self, catalog: CatalogMatcher) -> None:
        self._catalog = catalog

    async def prepare(
        self,
        text: str,
        state: ConversationState,
    ) -> ConversationTurn:
        self._catalog.clear_snapshot()
        text = await self._resolve_clarification(text, state)
        entries = await self._catalog.entries()
        history = state.history[-MAX_HISTORY_TURNS:]
        recognized = await self._catalog.find(text)
        suggestions = (
            await self._catalog.suggestions(text) if recognized is None else []
        )
        ambiguous = suggestions if len(suggestions) >= 2 else []
        if ambiguous:
            state.pending_item_text = text
        recognized_item = next(
            (
                {"sku": entry.sku, "name": entry.item.name}
                for entry in entries
                if recognized and entry.item.id == recognized.item.id
            ),
            None,
        )
        context = {
            "customer_text": text,
            "history": history,
            "state": self.state(state),
            "menu": self.menu(entries),
            "branches": BRANCHES,
            "recognized_item": recognized_item,
            "ambiguous_items": ambiguous,
        }
        return ConversationTurn(text, entries, history, context)

    async def _resolve_clarification(
        self,
        text: str,
        state: ConversationState,
    ) -> str:
        pending = state.pending_item_text
        if not pending or quantity_was_said(text):
            return text
        picked = await self._catalog.find(text)
        options = await self._catalog.suggestions(pending)
        if picked and picked.item.name in options:
            return f"{pending} {text}"
        return text

    def reply_context(
        self,
        turn: ConversationTurn,
        state: ConversationState,
        plan: dict,
        events: list[dict],
        order: Order | None,
    ) -> dict:
        return {
            **turn.planner_context,
            "last_agent_question": (
                turn.history[-1][1] if turn.history else None
            ),
            "intent": plan.get("intent"),
            "verified_events": events,
            "state": self.state(state),
            "available_menu": [
                {
                    "name": entry.item.name,
                    "price": money_message(entry.item.price_minor),
                }
                for entry in turn.entries
                if entry.item.is_available
            ],
            "order_created": order is not None,
            "order_id": str(order.id) if order else None,
            "exact_total": (
                money_message(order.total_price_minor) if order else None
            ),
        }

    @staticmethod
    def menu(entries: list[CatalogEntry]) -> list[dict]:
        return [
            {
                **entry.as_context(),
                "price_spoken": money_message(entry.item.price_minor),
            }
            for entry in entries
        ]

    @staticmethod
    def state(state: ConversationState) -> dict:
        missing = []
        if not state.lines:
            missing.append("items")
        if state.branch is None:
            missing.append("branch")
        if state.delivery_type is None:
            missing.append("delivery_type")
        if (
            state.delivery_type is DeliveryType.delivery
            and state.address is None
        ):
            missing.append("address_with_house_number")
        return {
            "cart": [
                {
                    "name": line.name,
                    "quantity": line.quantity,
                    "unit_price_minor": line.unit_price_minor,
                }
                for line in state.lines
            ],
            "subtotal": money_message(state.subtotal_minor),
            "branch": state.branch,
            "delivery_type": (
                state.delivery_type.value if state.delivery_type else None
            ),
            "address": state.address,
            "partial_address": state.address_street,
            "suggested_delivery": (
                state.suggested_delivery.value
                if state.suggested_delivery
                else None
            ),
            "missing_for_order": missing,
        }
