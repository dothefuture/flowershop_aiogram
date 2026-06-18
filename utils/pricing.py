"""Форматирование цен и расчёт скидок."""


def effective_price(price: float, discount_percent: int = 0) -> float:
    """Возвращает цену с учётом скидки."""
    if discount_percent <= 0:
        return price
    return round(price * (1 - discount_percent / 100), 2)


def format_rub(amount: float) -> str:
    """Сумма с символом рубля."""
    return f"{amount:.0f} ₽"


def format_price_line(price: float, discount_percent: int = 0) -> str:
    """
    Строка цены для каталога.
    Без скидки: 💰 <b>2500 ₽</b>
    Со скидкой: 💰 <s>2500 ₽</s> <b>2000 ₽</b>  🏷 <b>-20%</b>
    """
    if discount_percent <= 0:
        return f"💰 <b>{price:.0f} ₽</b>"

    sale = effective_price(price, discount_percent)
    return (
        f"💰 <s>{price:.0f} ₽</s> "
        f"<b>{sale:.0f} ₽</b>  🏷 <b>-{discount_percent}%</b>"
    )


def format_price_short(price: float, discount_percent: int = 0) -> str:
    """Краткая строка цены для списков и корзины."""
    if discount_percent <= 0:
        return f"{price:.0f} ₽"

    sale = effective_price(price, discount_percent)
    return f"<s>{price:.0f}</s> {sale:.0f} ₽ (-{discount_percent}%)"
