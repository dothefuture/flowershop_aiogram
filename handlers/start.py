"""Обработчик /start и /s — главное меню без сброса FSM."""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from utils.welcome import send_main_menu

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await send_main_menu(message)


@router.message(Command("s"))
async def cmd_quick_start(message: Message, state: FSMContext) -> None:
    await send_main_menu(message)
