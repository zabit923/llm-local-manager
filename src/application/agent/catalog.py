from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from src.application.agent.constants import NUMBER_WORDS, WORD_SUFFIXES
from src.application.schemas.orders import OrderItemCreate
from src.application.use_cases.dishes import DishUseCases
from src.application.use_cases.drinks import DrinkUseCases


@dataclass(frozen=True)
class CatalogMatch:
    item: object
    kind: str


class QuantityParser:
    @staticmethod
    def parse(text: str) -> int:
        match = re.search(r"\b([1-9]|[1-9][0-9])\b", text)
        if match:
            return int(match.group(1))
        for word, value in NUMBER_WORDS.items():
            if re.search(rf"\b{word}\w*\b", text.lower()):
                return value
        return 1


class CatalogMatcher:
    def __init__(self, dishes: DishUseCases, drinks: DrinkUseCases) -> None:
        self._dishes = dishes
        self._drinks = drinks

    @staticmethod
    def _similar(text: str, name: str) -> float:
        text, name = text.lower(), name.lower()
        if name in text:
            return 1.0
        return SequenceMatcher(None, text, name).ratio()

    @staticmethod
    def _has_common_fragment(text: str, name: str) -> bool:
        match = SequenceMatcher(
            None,
            text.lower(),
            name.lower(),
        ).find_longest_match(0, len(text), 0, len(name))
        return match.size >= 3

    @staticmethod
    def _stem_words(value: str) -> set[str]:
        result = set()
        for word in re.findall(r"[а-яёa-z]+", value.lower()):
            for suffix in WORD_SUFFIXES:
                if len(word) > len(suffix) + 2 and word.endswith(suffix):
                    word = word[: -len(suffix)]
                    break
            if len(word) >= 3:
                result.add(word)
        return result

    async def _candidates(self, available: bool) -> list[tuple[object, str]]:
        dishes = [
            dish
            for dish in await self._dishes.list()
            if dish.is_available is available
        ]
        drinks = [
            drink
            for drink in await self._drinks.list()
            if drink.is_available is available
        ]
        return [(dish, "dish") for dish in dishes] + [
            (drink, "drink") for drink in drinks
        ]

    async def find(self, text: str) -> CatalogMatch | None:
        candidates = await self._candidates(True)
        ranked = sorted(
            candidates,
            key=lambda pair: self._similar(text, pair[0].name),
            reverse=True,
        )
        if (
            ranked
            and self._similar(text, ranked[0][0].name) >= 0.38
            and self._has_common_fragment(text, ranked[0][0].name)
        ):
            return CatalogMatch(*ranked[0])
        spoken_words = self._stem_words(text)
        token_ranked = sorted(
            candidates,
            key=lambda pair: len(spoken_words & self._stem_words(pair[0].name)),
            reverse=True,
        )
        if token_ranked and spoken_words & self._stem_words(
            token_ranked[0][0].name
        ):
            return CatalogMatch(*token_ranked[0])
        unavailable = await self._candidates(False)
        ranked_unavailable = sorted(
            unavailable,
            key=lambda pair: self._similar(text, pair[0].name),
            reverse=True,
        )
        if (
            ranked_unavailable
            and self._similar(text, ranked_unavailable[0][0].name) >= 0.45
            and self._has_common_fragment(
                text,
                ranked_unavailable[0][0].name,
            )
        ):
            return CatalogMatch(ranked_unavailable[0][0], "unavailable")
        return None

    async def available_names(self) -> list[str]:
        candidates = await self._candidates(True)
        return [item.name for item, _ in candidates]

    @staticmethod
    def to_order_item(match: CatalogMatch, quantity: int) -> OrderItemCreate:
        field = "dish_id" if match.kind == "dish" else "drink_id"
        return OrderItemCreate(**{field: match.item.id, "quantity": quantity})
