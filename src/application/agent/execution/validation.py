import re

from src.application.agent.config.settings import NUMBER_WORDS


def said(text: str, evidence: object) -> bool:
    return (
        isinstance(evidence, str)
        and len(evidence.strip()) >= 2
        and evidence.lower().strip() in text.lower()
    )


def quantity_was_said(text: str) -> bool:
    if re.search(r"\b\d{1,2}\b", text):
        return True
    return any(
        re.search(rf"\b{word}\w*\b", text.lower()) for word in NUMBER_WORDS
    )
