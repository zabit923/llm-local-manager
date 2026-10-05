class ActionReason:
    INVALID_ACTION_SHAPE = "invalid action field types"

    UNKNOWN_ACTION = "unknown action"
    ITEM_UNAVAILABLE_OR_UNKNOWN = "item unavailable or unknown"
    INVALID_QUANTITY = "invalid quantity"
    ITEM_NOT_HEARD_FROM_CUSTOMER = "item not heard from customer"
    AMBIGUOUS_OR_MISMATCHED_ITEM = "ambiguous or mismatched item"
    QUANTITY_MISMATCH = "quantity mismatch"
    QUANTITY_NOT_HEARD = "quantity not heard"
    REMOVAL_NOT_CLEAR_OR_ITEM_NOT_IN_CART = (
        "removal not clear or item not in cart"
    )
    QUANTITY_OR_ITEM_REFERENCE_UNCLEAR = "quantity or item reference unclear"
    BRANCH_NOT_HEARD_OR_UNKNOWN = "branch not heard or unknown"
    BRANCH_EVIDENCE_MISMATCH = "branch evidence mismatch"
    HOUSE_NUMBER_MISSING = "house number missing"
    BRANCH_CHANGE_NOT_EXPLICIT = "branch change not explicit"
    FULFILLMENT_CHOICE_NOT_HEARD = "fulfillment choice not heard"
    CHOICE_NOT_EXPLICIT = "choice not explicit"
    ADDRESS_IS_ALLOWED_ONLY_FOR_DELIVERY = (
        "address is allowed only for delivery"
    )
    EMPTY_ADDRESS = "empty address"
    ADDRESS_NOT_HEARD_FROM_CUSTOMER = "address not heard from customer"
    STREET_MISSING = "street missing"
