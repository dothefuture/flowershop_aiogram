"""Обработчик /start и /s — сброс состояния и главное меню."""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import get_or_create_user
from keyboards.main import main_menu_kb
from texts import WELCOME, WELCOME_RESTART
from utils.auth import is_admin

router = Router(name="start")


async def _send_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    await get_or_create_user(user.id, username=user.username)
    await message.answer(
        WELCOME_RESTART + WELCOME,
        reply_markup=main_menu_kb(is_admin=is_admin(user.id)),
        parse_mode="HTML",
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await _send_start(message, state)


@router.message(Command("s"))
async def cmd_quick_start(message: Message, state: FSMContext) -> None:
    """Быстрая команда /s — то же, что /start."""
    await _send_start(message, state)
