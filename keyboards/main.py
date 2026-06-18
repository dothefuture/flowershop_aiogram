"""Главное меню — reply-клавиатура (Mini App — кнопка слева от поля ввода)."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_kb(*, is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Клавиатура главного меню магазина."""
    rows = [
        [KeyboardButton(text="🌷 Каталог"), KeyboardButton(text="🛒 Корзина")],
        [KeyboardButton(text="💳 Счета"), KeyboardButton(text="📖 История заказов")],
        [KeyboardButton(text="👤 Профили")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="🔧 Админ-панель")])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел…",
    )
