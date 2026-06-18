"""
Чат поддержки: пользователь ↔ администраторы.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import (
    add_support_message,
    get_or_create_support_thread,
    get_or_create_user,
)
from keyboards.main import main_menu_kb, support_chat_kb
from states import SupportStates
from texts import SUPPORT_ENDED, SUPPORT_START, SUPPORT_USER_SENT
from utils.auth import get_admin_ids, is_admin
from utils.formatting import format_telegram_client

router = Router(name="support")


async def _notify_admins(message: Message, user_text: str) -> None:
    user = message.from_user
    tag = format_telegram_client(user.username)
    header = (
        f"💬 <b>Обращение в поддержку</b>\n"
        f"От: {tag}\n\n"
        f"{user_text}"
    )
    for admin_id in get_admin_ids():
        if admin_id == user.id:
            continue
        try:
            await message.bot.send_message(
                admin_id,
                header,
                parse_mode="HTML",
                reply_markup=None,
            )
        except Exception:
            pass


@router.message(F.text == "💬 Поддержка")
async def start_support(message: Message, state: FSMContext) -> None:
    if is_admin(message.from_user.id):
        await message.answer(
            "Вы администратор — ответы на обращения в 🔧 Админ-панель → Поддержка.",
            reply_markup=main_menu_kb(is_admin=True),
        )
        return

    user = await get_or_create_user(message.from_user.id, username=message.from_user.username)
    await get_or_create_support_thread(user["id"])
    await state.set_state(SupportStates.chatting)
    await message.answer(
        SUPPORT_START,
        reply_markup=support_chat_kb(),
        parse_mode="HTML",
    )


@router.message(SupportStates.chatting, F.text == "❌ Завершить чат")
async def end_support(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        SUPPORT_ENDED,
        reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
        parse_mode="HTML",
    )


@router.message(SupportStates.chatting, F.text)
async def support_user_message(message: Message, state: FSMContext) -> None:
    if message.text.startswith("/"):
        return

    user = await get_or_create_user(message.from_user.id, username=message.from_user.username)
    thread = await get_or_create_support_thread(user["id"])
    await add_support_message(thread["id"], "user", message.text)
    await _notify_admins(message, message.text)
    await message.answer(SUPPORT_USER_SENT, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:support_quick:"))
async def support_quick_reply_btn(callback: CallbackQuery, state: FSMContext) -> None:
    """Быстрый ответ из уведомления (если добавим кнопку)."""
    await callback.answer()
