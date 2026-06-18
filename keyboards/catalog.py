"""Inline-клавиатуры каталога."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def product_card_kb(product_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Кнопки карточки товара: заказ + пагинация."""
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="🛒 Добавить в корзину",
                callback_data=f"catalog:order:{product_id}",
            )
        ]
    ]

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

    return InlineKeyboardMarkup(inline_keyboard=rows)
