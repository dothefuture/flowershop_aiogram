"""
Хранилище корзины в памяти.
Корзина — отдельный словарь в runtime (FSM использует MemoryStorage).
"""

from __future__ import annotations

from typing import Any

from utils.pricing import effective_price

# user_id (Telegram) -> {product_id: quantity}
_carts: dict[int, dict[int, int]] = {}


def get_cart(user_id: int) -> dict[int, int]:
    """Возвращает корзину пользователя: {product_id: quantity}."""
    return _carts.setdefault(user_id, {})


def add_to_cart(user_id: int, product_id: int, quantity: int = 1) -> None:
    """Добавляет товар в корзину или увеличивает количество."""
    cart = get_cart(user_id)
    cart[product_id] = cart.get(product_id, 0) + quantity


def remove_from_cart(user_id: int, product_id: int) -> None:
    """Удаляет товар из корзины."""
    cart = get_cart(user_id)
    cart.pop(product_id, None)
    if not cart:
        _carts.pop(user_id, None)


def clear_cart(user_id: int) -> None:
    """Очищает корзину после оформления заказа."""
    _carts.pop(user_id, None)


def cart_is_empty(user_id: int) -> bool:
    """Проверяет, пуста ли корзина."""
    return not get_cart(user_id)


async def build_cart_details(user_id: int) -> tuple[list[dict[str, Any]], float]:
    """
    Собирает детали корзины из БД с учётом скидок.
    Возвращает (список позиций, общая сумма).
    """
    from database import get_product

    cart = get_cart(user_id)
    items: list[dict[str, Any]] = []
    total = 0.0

    for product_id, quantity in cart.items():
        product = await get_product(product_id)
        if not product or not product["is_active"]:
            continue

        discount = int(product.get("discount_percent") or 0)
        unit_price = effective_price(product["price"], discount)
        subtotal = unit_price * quantity

        items.append(
            {
                "product_id": product_id,
                "product_name": product["name"],
                "price": unit_price,
                "original_price": product["price"],
                "discount_percent": discount,
                "quantity": quantity,
                "subtotal": subtotal,
            }
        )
        total += subtotal

    return items, total
