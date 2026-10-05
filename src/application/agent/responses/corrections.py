from src.application.agent.config import messages
from src.application.agent.planning.intent import (
    advice_about_fulfillment,
    finished_adding,
)
from src.application.agent.responses.dto import ReplyFacts


def correction_for(facts: ReplyFacts) -> str:
    state = facts.context["state"]
    rules = (
        (not state["cart"], messages.RETRY_EMPTY_CART),
        (facts.context.get("ambiguous_items"), messages.RETRY_AMBIGUOUS_ITEM),
        (
            state["partial_address"] and not state["address"],
            messages.RETRY_HOUSE_NUMBER,
        ),
        (state["delivery_type"] == "pickup", messages.RETRY_PICKUP),
        (facts.added, messages.RETRY_ITEM_ADDED),
        (
            state["cart"]
            and state["branch"]
            and state["delivery_type"] is None,
            messages.RETRY_MISSING_DELIVERY,
        ),
        (
            any(
                word in facts.lowered
                for word in (
                    messages.SPEED_MARKER,
                    messages.COST_MARKER,
                )
            ),
            messages.RETRY_UNSUPPORTED_COMPARISON,
        ),
        (
            advice_about_fulfillment(facts.context),
            messages.RETRY_DELIVERY_ADVICE,
        ),
        (
            finished_adding(facts.context) and state["cart"],
            messages.RETRY_FINISHED_CART,
        ),
    )
    guidance = [messages.RETRY_FACTS]
    guidance.extend(message for condition, message in rules if condition)
    guidance.append(messages.RETRY_REJECTED_ACTION)
    return " ".join(guidance)
