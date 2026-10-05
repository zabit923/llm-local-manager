import re

from src.application.agent.config import language
from src.application.agent.config.settings import BRANCHES
from src.application.agent.planning.intent import (
    advice_about_fulfillment,
    finished_adding,
)
from src.application.agent.responses.dto import ReplyFacts
from src.application.agent.responses.money import money_message


class ReplyPolicy:

    @classmethod
    def accepts(cls, facts: ReplyFacts) -> bool:
        if not cls._text(facts) or not cls._completion(facts):
            return False
        if facts.order is not None:
            return True
        checks = (
            cls._addition,
            cls._cart,
            cls._finished_cart,
            cls._address,
            cls._branch,
        )
        return all(check(facts) for check in checks)

    @staticmethod
    def _text(facts: ReplyFacts) -> bool:
        reply, history = facts.reply, facts.history
        repeated = bool(history and reply.strip() == history[-1][1].strip())
        greeted = bool(
            history
            and reply.lower().startswith(
                language.GREETING_PREFIXES,
            )
        )
        return bool(
            reply
            and len(reply) <= 420
            and "<think>" not in facts.lowered
            and not repeated
            and not greeted
            and "100.00" not in reply
            and "₽" not in reply
            and not language.contains_any(
                facts.lowered,
                language.UNSUPPORTED_COMPARISONS,
            )
        )

    @staticmethod
    def _completion(facts: ReplyFacts) -> bool:
        lowered = facts.lowered
        if advice_about_fulfillment(facts.context) and not (
            language.contains_any(lowered, language.ADVICE_MARKERS)
        ):
            return False
        if facts.order is not None:
            return (
                language.ORDER_MARKER in lowered
                and money_message(facts.order.total_price_minor) in lowered
            )
        return not (
            language.contains_any(lowered, language.CREATED_CLAIMS)
            or re.search(language.CONFIRMATION_PATTERN, lowered)
        )

    @staticmethod
    def _addition(facts: ReplyFacts) -> bool:
        if not facts.added:
            return not language.contains_any(
                facts.lowered,
                language.ADDITION_CLAIMS,
            )
        return language.contains_any(
            facts.lowered,
            language.ADDITION_ACKNOWLEDGEMENTS,
        ) and not language.contains_any(
            facts.lowered,
            language.REDUNDANT_ADDITION_QUESTIONS,
        )

    @staticmethod
    def _cart(facts: ReplyFacts) -> bool:
        state = facts.context["state"]
        empty = "cart" in state and not state["cart"]
        if empty and re.search(
            language.EMPTY_CART_PROGRESS_PATTERN,
            facts.lowered,
        ):
            return False
        ambiguous = facts.context.get("ambiguous_items", [])
        return (
            not ambiguous
            or facts.added
            or any(name.lower() in facts.lowered for name in ambiguous)
        )

    @staticmethod
    def _finished_cart(facts: ReplyFacts) -> bool:
        state = facts.context["state"]
        if not finished_adding(facts.context) or not state.get("cart", True):
            return True
        mentioned_branch = language.BRANCH_MARKER in facts.lowered or any(
            branch.lower() in facts.lowered
            for branch in facts.context["branches"]
        )
        return (
            state["branch"] is not None or mentioned_branch
        ) and not language.contains_any(
            facts.lowered,
            language.FINISHED_CART_REPETITIONS,
        )

    @staticmethod
    def _address(facts: ReplyFacts) -> bool:
        state = facts.context["state"]
        if state["delivery_type"] == "pickup":
            return not language.contains_any(
                facts.lowered,
                language.PICKUP_ADDRESS_QUESTIONS,
            )
        incomplete = (
            state["delivery_type"] == "delivery"
            and state["partial_address"]
            and not state["address"]
        )
        return not incomplete or (
            language.contains_any(facts.lowered, language.HOUSE_MARKERS)
            and not any(character.isdigit() for character in facts.reply)
        )

    @staticmethod
    def _branch(facts: ReplyFacts) -> bool:
        branch = facts.context["state"]["branch"]
        if not branch:
            return True
        wrong_branch = any(
            template.format(branch=candidate.lower()) in facts.lowered
            for candidate in BRANCHES
            if candidate != branch
            for template in language.WRONG_BRANCH_QUOTES
        )
        return not wrong_branch and not language.contains_any(
            facts.lowered,
            language.BRANCH_QUESTIONS,
        )
