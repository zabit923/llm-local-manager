"""Formatting verified monetary amounts for spoken replies."""


def _currency_word(amount: int, forms: tuple[str, str, str]) -> str:
    if amount % 100 in range(11, 15):
        return forms[2]
    digit = amount % 10
    if digit == 1:
        return forms[0]
    if digit in (2, 3, 4):
        return forms[1]
    return forms[2]


def money_message(total_price_minor: int) -> str:
    rubles, kopecks = divmod(total_price_minor, 100)
    ruble_word = _currency_word(rubles, ("рубль", "рубля", "рублей"))
    result = f"{rubles} {ruble_word}"
    if kopecks:
        kopeck_word = _currency_word(kopecks, ("копейка", "копейки", "копеек"))
        result += f" {kopecks} {kopeck_word}"
    return result
