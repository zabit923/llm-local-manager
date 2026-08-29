from taskiq import AsyncBroker


def register_tasks(broker: AsyncBroker) -> None:
    """"""
    # broker.register_task(
    #     confirm_payout_webhook_task,
    #     task_name=confirm_payout_webhook_task.__name__,
    #     uniq=True,
    #     ttl=1800,
    # )
