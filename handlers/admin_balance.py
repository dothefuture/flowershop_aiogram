"""Ручное начисление баланса администратором."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import add_user_balance, get_or_create_user, get_user_by_username
from keyboards.main import main_menu_kb
from utils.auth import can_credit_balance
from utils.formatting import format_telegram_tag
from utils.pricing import format_rub

router = Router(name="admin_balance")

_USAGE = (
    "💰 <b>Начисление баланса</b>\n\n"
    "Формат:\n"
    "<code>/addbalance @username СУММА</code>\n\n"
    "Пример:\n"
    "<code>/addbalance @ivanov 500</code>"
)


async def _resolve_user(raw: str):
    """Telegram ID или @username."""
    token = raw.strip().lstrip("@")
    if token.isdigit():
        user = await get_or_create_user(int(token))
        return user, int(token)
    user = await get_user_by_username(token)
    if not user:
        return None, None
    return user, user["telegram_id"]


@router.message(Command("addbalance"))
async def cmd_add_balance(message: Message) -> None:
    if not can_credit_balance(message.from_user.id):
        await message.answer("⛔ Команда недоступна для вашего аккаунта.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(_USAGE, parse_mode="HTML")
        return

    user_raw = parts[1].strip()
    amount_raw = parts[2].strip().replace(",", ".").replace(" ", "")

    try:
        amount = float(amount_raw)
    except ValueError:
        await message.answer("Некорректная сумма.", parse_mode="HTML")
        return

    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.", parse_mode="HTML")
        return

    user, telegram_id = await _resolve_user(user_raw)
    if not user or telegram_id is None:
        await message.answer(
            f"Пользователь <code>{user_raw}</code> не найден.\n"
            "Он должен хотя бы раз написать боту.",
            parse_mode="HTML",
        )
        return

    new_balance = await add_user_balance(user["id"], amount)
    tag = format_telegram_tag(user.get("username"))

    await message.answer(
        f"✅ Начислено <b>{format_rub(amount)}</b>\n"
        f"Пользователь: {tag}\n"
        f"Баланс: <b>{format_rub(new_balance)}</b>",
        reply_markup=main_menu_kb(is_admin=True),
        parse_mode="HTML",
    )

    try:
        await message.bot.send_message(
            telegram_id,
            f"💰 Вам начислено <b>{format_rub(amount)}</b>\n"
            f"На счету: <b>{format_rub(new_balance)}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass
