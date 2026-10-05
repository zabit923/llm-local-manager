from src.application.agent.catalog.matcher import CatalogMatcher
from src.application.agent.config.messages import MODEL_UNAVAILABLE_REPLY
from src.application.agent.config.settings import MAX_HISTORY_TURNS
from src.application.agent.contracts.errors import ModelUnavailable
from src.application.agent.contracts.ports import AgentModel, SessionStore
from src.application.agent.conversation.context import ContextBuilder
from src.application.agent.conversation.state import ConversationState
from src.application.agent.execution.checkout import CheckoutService
from src.application.agent.execution.executor import ActionExecutor
from src.application.agent.planning.service import PlanningService
from src.application.agent.responses.dto import ReplyFacts
from src.application.agent.responses.generator import ReplyGenerator
from src.application.logging import agent_log
from src.application.schemas.agent import AgentMessageResponse
from src.application.use_cases.dishes import DishUseCases
from src.application.use_cases.drinks import DrinkUseCases
from src.application.use_cases.orders import OrderUseCases


class OrderAgent:

    def __init__(
        self,
        dishes: DishUseCases,
        drinks: DrinkUseCases,
        orders: OrderUseCases,
        model: AgentModel,
        sessions: SessionStore,
    ) -> None:
        catalog = CatalogMatcher(dishes, drinks)
        self._actions = ActionExecutor(catalog)
        self._context = ContextBuilder(catalog)
        self._checkout = CheckoutService(orders)
        self._model = model
        self._sessions = sessions

    async def handle(self, session_id: str, text: str) -> AgentMessageResponse:
        async with self._sessions.lease(session_id) as state:
            return await self._turn(session_id, text, state)

    async def _turn(
        self,
        session_id: str,
        text: str,
        state: ConversationState,
    ) -> AgentMessageResponse:
        agent_log.input(session_id, text, state)
        turn = await self._context.prepare(text, state)
        planner = PlanningService(self._model, self._actions)
        try:
            result = await planner.execute(session_id, turn, state)
        except ModelUnavailable:
            agent_log.reply(
                session_id, "model_unavailable", MODEL_UNAVAILABLE_REPLY
            )
            return AgentMessageResponse(
                session_id=session_id,
                reply=MODEL_UNAVAILABLE_REPLY,
                cart=state.labels,
            )
        order = await self._checkout.create_if_ready(session_id, state)
        context = self._context.reply_context(
            turn,
            state,
            result.plan,
            result.events,
            order,
        )
        reply = await ReplyGenerator(self._model).respond(
            ReplyFacts("", order, result.events, turn.history, context),
        )
        agent_log.reply(session_id, "model", reply)
        response = AgentMessageResponse(
            session_id=session_id,
            reply=reply,
            cart=state.labels,
            order_id=order.id if order else None,
        )
        if order is not None:
            self._sessions.remove(session_id)
        else:
            state.history.append((turn.text, reply))
            state.history = state.history[-MAX_HISTORY_TURNS:]
        return response
