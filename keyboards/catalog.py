"""Inline-клавиатуры каталога."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def product_card_kb(
    product_id: int, page: int, total_pages: int, qty: int
) -> InlineKeyboardMarkup:
    """Добавить в корзину или +/- если товар уже в корзине."""
    rows: list[list[InlineKeyboardButton]] = []

    if qty > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    text="➖",
                    callback_data=f"catalog:qty:{product_id}:dec",
                ),
                InlineKeyboardButton(
                    text=f"{qty} шт.",
                    callback_data="catalog:noop",
                ),
                InlineKeyboardButton(
                    text="➕",
                    callback_data=f"catalog:qty:{product_id}:inc",
                ),
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🛒 Добавить в корзину",
                    callback_data=f"catalog:add:{product_id}",
                )
            ]
        )

    nav_buttons: list[InlineKeyboardButton] = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"catalog:page:{page - 1}")
        )
    if total_pages > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text=f"· {page + 1}/{total_pages} ·",
                callback_data="catalog:noop",
            )
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"catalog:page:{page + 1}")
        )

    if nav_buttons:
        rows.append(nav_buttons)

    rows.append(
        [
            InlineKeyboardButton(
                text="🛒 Корзина",
                callback_data="catalog:cart",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)
