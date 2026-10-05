from src.application.agent.config import messages
from src.application.agent.contracts.errors import ModelUnavailable
from src.application.agent.contracts.ports import AgentModel
from src.application.agent.responses.corrections import correction_for
from src.application.agent.responses.dto import ReplyFacts
from src.application.agent.responses.money import money_message
from src.application.agent.responses.policy import ReplyPolicy
from src.domain.models.order import Order


class ReplyGenerator:

    def __init__(self, model: AgentModel, max_attempts: int = 3) -> None:
        self._model = model
        self._max_attempts = max_attempts

    async def respond(self, facts: ReplyFacts) -> str:
        context = dict(facts.context)
        for _ in range(self._max_attempts):
            try:
                reply = await self._model.respond(context)
            except ModelUnavailable:
                break
            candidate = ReplyFacts(
                reply,
                facts.order,
                facts.events,
                facts.history,
                context,
            )
            if ReplyPolicy.accepts(candidate):
                return reply
            context["correction"] = correction_for(candidate)
            context["rejected_reply"] = reply
        return self.fallback(facts.order)

    @staticmethod
    def fallback(order: Order | None) -> str:
        if order is not None:
            return messages.ORDER_CREATED_REPLY.format(
                total=money_message(order.total_price_minor),
            )
        return messages.INVALID_REPLY
