"""
Клавиатуры корзины и оформления заказа.
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from texts import BTN_CANCEL
from utils.pricing import format_rub


def cart_kb(items: list[dict]) -> InlineKeyboardMarkup:
    if not items:
        return InlineKeyboardMarkup(inline_keyboard=[])

    rows: list[list[InlineKeyboardButton]] = []

    for item in items:
        pid = item["product_id"]
        name = item["product_name"]
        if len(name) > 20:
            name = name[:19] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text="➖",
                    callback_data=f"cart:dec:{pid}",
                ),
                InlineKeyboardButton(
                    text=f"{name} · {item['quantity']} шт.",
                    callback_data="cart:noop",
                ),
                InlineKeyboardButton(
                    text="➕",
                    callback_data=f"cart:inc:{pid}",
                ),
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🗑 Очистить",
                callback_data="cart:clear",
            )
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

    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_order_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить заказ",
                    callback_data="order:confirm",
                ),
                InlineKeyboardButton(
                    text=BTN_CANCEL,
                    callback_data="order:cancel",
                ),
            ]
        ]
    )


def order_payment_kb(
    order_id: int, balance: float, total: float
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="💳 Оплатить через LAVA",
                callback_data=f"order:pay:lava:{order_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"💰 С баланса · {format_rub(balance)}",
                callback_data=(
                    f"order:pay:balance:{order_id}"
                    if balance >= total
                    else "order:pay:balance:low"
                ),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_fsm_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )
