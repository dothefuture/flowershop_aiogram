"""Главное меню — reply-клавиатура."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_kb(*, is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🌷 Каталог"), KeyboardButton(text="🛒 Корзина")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💬 Поддержка")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="🔧 Админ-панель")])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел…",
    )


def support_chat_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="↩️ Завершить чат")]],
        resize_keyboard=True,
    )
