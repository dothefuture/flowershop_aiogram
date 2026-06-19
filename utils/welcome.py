"""Главное меню бота — текст и отправка."""

from aiogram.types import Message, User

from database import get_or_create_user, get_setting
from keyboards.main import main_menu_kb
from texts import WELCOME
from utils.auth import is_admin


async def get_welcome_text() -> str:
    custom = await get_setting("welcome_text", "")
    return custom if custom.strip() else WELCOME


async def send_main_menu(message: Message, user: User | None = None) -> None:
    """Отправляет приветствие главного меню (без сброса FSM)."""
    tg_user = user or message.from_user
    await get_or_create_user(tg_user.id, username=tg_user.username)
    kb = main_menu_kb(is_admin=is_admin(tg_user.id))
    text = await get_welcome_text()
    photo_id = await get_setting("welcome_photo_file_id", "")

    if photo_id:
        await message.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=kb,
            parse_mode="HTML",
        )
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
