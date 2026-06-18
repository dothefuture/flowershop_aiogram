"""
Клавиатуры корзины и оформления заказа.
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def cart_kb(items: list[dict]) -> InlineKeyboardMarkup:
    """Кнопки корзины: управление позициями и оформление."""
    if not items:
        return InlineKeyboardMarkup(inline_keyboard=[])

    rows: list[list[InlineKeyboardButton]] = []

    for item in items:
        pid = item["product_id"]
        rows.append(
            [
                InlineKeyboardButton(
                    text="➖",
                    callback_data=f"cart:dec:{pid}",
                ),
                InlineKeyboardButton(
                    text=f"{item['product_name'][:20]} × {item['quantity']}",
                    callback_data="cart:noop",
                ),
                InlineKeyboardButton(
                    text="➕",
                    callback_data=f"cart:inc:{pid}",
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data=f"cart:remove:{pid}",
                ),
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="✅ Оформить заказ",
                callback_data="cart:checkout",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="🗑 Очистить корзину",
                callback_data="cart:clear",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_order_kb() -> InlineKeyboardMarkup:
    """Подтверждение или отмена заказа на последнем шаге FSM."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить заказ",
                    callback_data="order:confirm",
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="order:cancel",
                ),
            ]
        ]
    )


def cancel_fsm_kb() -> ReplyKeyboardMarkup:
    """Кнопка отмены при заполнении формы."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )
