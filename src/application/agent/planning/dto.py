from dataclasses import dataclass


@dataclass(frozen=True)
class PlanResult:

    plan: dict
    events: list[dict]
