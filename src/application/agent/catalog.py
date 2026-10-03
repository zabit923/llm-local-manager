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


@dataclass(frozen=True)
class CatalogEntry:
    sku: str
    item: object
    kind: str

    def as_context(self) -> dict[str, object]:
        return {
            "sku": self.sku,
            "name": self.item.name,
            "price_minor": self.item.price_minor,
            "available": self.item.is_available,
        }


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

    async def entries(self) -> list[CatalogEntry]:
        dishes = await self._dishes.list()
        drinks = await self._drinks.list()
        return [
            CatalogEntry(f"D{index}", dish, "dish")
            for index, dish in enumerate(dishes, 1)
        ] + [
            CatalogEntry(f"R{index}", drink, "drink")
            for index, drink in enumerate(drinks, 1)
        ]

    @staticmethod
    def _score(text: str, name: str) -> float:
        query = CatalogMatcher._stem_words(text)
        target = CatalogMatcher._stem_words(name)
        if not query or not target:
            return 0.0
        scores = []
        for word in target:
            candidates = [
                SequenceMatcher(None, word, spoken).ratio()
                for spoken in query
                if spoken[:3] == word[:3]
            ]
            scores.append(max(candidates, default=0.0))
        matched = sum(score >= 0.8 for score in scores)
        return max(scores, default=0.0) + 0.2 * max(0, matched - 1)

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
        available = await self._candidates(True)
        normal = text.lower()
        if re.search(r"\b(обычн\w*|классич\w*)\b", normal):
            if re.search(r"\b(гир\w*|кир\w*|герой|киа|kia)\b", normal):
                classic = next(
                    (
                        item
                        for item, kind in available
                        if kind == "dish"
                        and item.name.lower().startswith("классический гирос")
                    ),
                    None,
                )
                if classic is not None:
                    return CatalogMatch(classic, "dish")
        ranked = sorted(
            available,
            key=lambda pair: self._score(text, pair[0].name),
            reverse=True,
        )
        if ranked and self._score(text, ranked[0][0].name) >= 0.8:
            best_score = self._score(text, ranked[0][0].name)
            if len(ranked) > 1:
                second_score = self._score(text, ranked[1][0].name)
                if best_score - second_score < 0.15:
                    return None
            return CatalogMatch(*ranked[0])
        unavailable = await self._candidates(False)
        for item, _ in unavailable:
            if self._score(text, item.name) >= 0.8:
                return CatalogMatch(item, "unavailable")
        return None

    async def suggestions(self, text: str) -> list[str]:
        candidates = await self._candidates(True)
        return [
            item.name
            for item, _ in candidates
            if self._score(text, item.name) >= 0.8
        ]

    async def available_names(self) -> list[str]:
        candidates = await self._candidates(True)
        return [item.name for item, _ in candidates]

    @staticmethod
    def to_order_item(match: CatalogMatch, quantity: int) -> OrderItemCreate:
        field = "dish_id" if match.kind == "dish" else "drink_id"
        return OrderItemCreate(**{field: match.item.id, "quantity": quantity})
