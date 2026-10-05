import re

from src.application.agent.catalog.dto import CatalogEntry
from src.application.agent.config import language
from src.application.agent.config.settings import BRANCHES
from src.application.agent.conversation.state import ConversationState
from src.application.agent.execution.reasons import ActionReason
from src.application.agent.execution.validation import said
from src.domain.models.choises.enum import DeliveryType


class FulfillmentActions:

    @staticmethod
    async def set_branch(
        action: dict,
        text: str,
        state: ConversationState,
        _entries: dict[str, CatalogEntry],
    ) -> dict[str, object]:
        branch = action.get("branch")
        evidence = action.get("evidence")
        if branch not in BRANCHES or not said(text, evidence):
            return {
                "action": "set_branch",
                "status": "rejected",
                "reason": ActionReason.BRANCH_NOT_HEARD_OR_UNKNOWN,
            }
        spoken = evidence.lower()
        valid = language.BRANCH_STEMS[branch] in spoken
        if not valid:
            return {
                "action": "set_branch",
                "status": "rejected",
                "reason": ActionReason.BRANCH_EVIDENCE_MISMATCH,
            }
        if state.branch is not None and state.branch != branch:
            if not re.search(
                language.BRANCH_CHANGE_PATTERN,
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
                        "reason": ActionReason.HOUSE_NUMBER_MISSING,
                        "street": evidence,
                    }
                return {
                    "action": "set_branch",
                    "status": "rejected",
                    "reason": ActionReason.BRANCH_CHANGE_NOT_EXPLICIT,
                }
        state.branch = branch
        return {
            "action": "set_branch",
            "status": "applied",
            "branch": branch,
        }

    @staticmethod
    async def set_delivery(
        action: dict,
        text: str,
        state: ConversationState,
        _entries: dict[str, CatalogEntry],
    ) -> dict[str, object]:
        value = action.get("value")
        evidence = action.get("evidence")
        if value not in ("pickup", "delivery") or not said(text, evidence):
            return {
                "action": "set_delivery",
                "status": "rejected",
                "reason": ActionReason.FULFILLMENT_CHOICE_NOT_HEARD,
            }
        lowered = text.lower().strip()
        pickup = bool(
            re.search(
                language.PICKUP_PATTERN,
                lowered,
            )
        )
        delivery = bool(re.search(language.DELIVERY_PATTERN, lowered))
        agreed = lowered in language.FULFILLMENT_AGREEMENTS
        declined = lowered in language.FULFILLMENT_DECLINES
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
                "reason": ActionReason.CHOICE_NOT_EXPLICIT,
            }
        state.delivery_type = DeliveryType(value)
        state.suggested_delivery = None
        return {
            "action": "set_delivery",
            "status": "applied",
            "value": value,
        }

    @staticmethod
    async def set_address(
        action: dict,
        text: str,
        state: ConversationState,
        _entries: dict[str, CatalogEntry],
    ) -> dict[str, object]:
        reason = FulfillmentActions._address_prerequisite(action, state)
        if reason:
            return {
                "action": "set_address",
                "status": "rejected",
                "reason": reason,
            }
        value = action["value"]
        spoken = text.lower().strip()
        value = value.strip()
        if state.address_street and re.fullmatch(
            language.HOUSE_NUMBER_PATTERN, spoken
        ):
            value = language.STREET_AND_HOUSE.format(
                street=state.address_street,
                number=text.strip(),
            )
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
                "reason": ActionReason.ADDRESS_NOT_HEARD_FROM_CUSTOMER,
            }
        if not re.search(language.ADDRESS_NUMBER_PATTERN, value.lower()):
            if len(value) >= 4:
                state.address_street = value
            return {
                "action": "set_address",
                "status": "incomplete",
                "reason": ActionReason.HOUSE_NUMBER_MISSING,
                "street": state.address_street,
            }
        if len(value.split()) < 2:
            return {
                "action": "set_address",
                "status": "rejected",
                "reason": ActionReason.STREET_MISSING,
            }
        state.address = value
        return {
            "action": "set_address",
            "status": "applied",
            "address": value,
        }

    @staticmethod
    def _address_prerequisite(
        action: dict,
        state: ConversationState,
    ) -> str | None:
        if state.delivery_type is not DeliveryType.delivery:
            return ActionReason.ADDRESS_IS_ALLOWED_ONLY_FOR_DELIVERY
        value = action.get("value")
        if not isinstance(value, str) or not value.strip():
            return ActionReason.EMPTY_ADDRESS
        return None
