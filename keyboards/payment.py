"""Клавиатуры оплаты LAVA и баланса."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from texts import BTN_EXIT


def payment_kb(payment_url: str, *, label: str = "💳 Оплатить заказ") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, url=payment_url)]
        ]
    )


def topup_amount_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="500 ₽", callback_data="profile:topup:500"),
                InlineKeyboardButton(text="1 000 ₽", callback_data="profile:topup:1000"),
            ],
            [
                InlineKeyboardButton(text="2 000 ₽", callback_data="profile:topup:2000"),
                InlineKeyboardButton(text="5 000 ₽", callback_data="profile:topup:5000"),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Другая сумма",
                    callback_data="profile:topup:custom",
                )
            ],
            [
                InlineKeyboardButton(
                    text=BTN_EXIT,
                    callback_data="profile:topup:cancel",
                )
            ],
        ]
    )


def topup_custom_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_EXIT,
                    callback_data="profile:topup:cancel",
                )
            ]
        ]
    )
