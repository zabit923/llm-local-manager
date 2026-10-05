from src.application.agent.config import language


def advice_about_fulfillment(context: dict) -> bool:
    question = context["customer_text"].lower()
    prior = (context.get("last_agent_question") or "").lower()
    return (
        language.contains_any(question, language.ADVICE_REQUESTS)
        and language.PICKUP_MARKER in prior
        and language.contains_any(prior, language.DELIVERY_MARKERS)
    )


def finished_adding(context: dict) -> bool:
    text = context["customer_text"].lower()
    prior = (context.get("last_agent_question") or "").lower()
    return language.contains_any(text, language.FINISHED_CART_MARKERS) or (
        text.strip() in language.DECLINED_ADDITIONS
        and language.contains_any(prior, language.ADDITIONAL_ITEM_QUESTIONS)
    )
