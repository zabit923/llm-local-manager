from src.application.agent.contracts.errors import ModelUnavailable
from src.application.agent.contracts.ports import AgentModel
from src.application.agent.conversation.dto import ConversationTurn
from src.application.agent.conversation.state import ConversationState
from src.application.agent.execution.executor import ActionExecutor
from src.application.agent.planning.dto import PlanResult
from src.application.logging import agent_log


class PlanningService:

    def __init__(self, model: AgentModel, actions: ActionExecutor) -> None:
        self._model = model
        self._actions = actions

    async def execute(
        self,
        session_id: str,
        turn: ConversationTurn,
        state: ConversationState,
    ) -> PlanResult:
        context = dict(turn.planner_context)
        result = await self._apply(session_id, context, turn, state)
        rejected = result.events and all(
            event.get("status") == "rejected" for event in result.events
        )
        if rejected:
            context["validation_feedback"] = result.events
            try:
                result = await self._apply(session_id, context, turn, state)
            except ModelUnavailable:
                pass
        agent_log.actions(session_id, result.events)
        if any(
            event.get("action") == "add_item"
            and event.get("status") == "applied"
            for event in result.events
        ):
            state.pending_item_text = None
        return result

    async def _apply(
        self,
        session_id: str,
        context: dict,
        turn: ConversationTurn,
        state: ConversationState,
    ) -> PlanResult:
        plan = await self._model.plan(context)
        agent_log.extraction(session_id, plan)
        events = await self._actions.apply(
            plan,
            turn.text,
            state,
            turn.entries,
        )
        return PlanResult(plan, events)
