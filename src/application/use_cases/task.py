from taskiq import AsyncBroker


class TaskManager:
    def __init__(
        self,
        broker: AsyncBroker,
    ):
        self._broker = broker

    async def confirm_payout_webhook_task(
        self,
        session_id: str,
    ) -> None:
        if confirm_task := self._broker.find_task(
            task_name="confirm_payout_webhook_task",
        ):
            await confirm_task.kiq(
                session_id=session_id,
            )
        else:
            raise RuntimeError(
                "confirm_payout_webhook_task not registered in broker"
            )
