import pytest

from src.application.agent.conversation.state import ConversationState
from src.application.agent.execution.executor import ActionExecutor


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action",
    [
        {"name": []},
        {"name": "add_item", "sku": []},
        {"name": "add_item", "quantity": True},
        {"name": "set_branch", "branch": {}},
        {"name": "add_item", "evidence": {}},
    ],
)
async def test_malformed_model_action_is_rejected(action):
    state = ConversationState()
    executor = ActionExecutor(None)
    events = await executor.apply({"actions": [action]}, "гирос", state, [])
    assert events[0]["status"] == "rejected"
    assert state.items == []
