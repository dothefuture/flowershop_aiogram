"""
Счета и оплата — история счетов пользователя.
"""

from aiogram import F, Router
from aiogram.types import Message

from database import BILLING_STATUSES, get_or_create_user, get_user_billing
from keyboards.main import main_menu_kb
from texts import BILLING_EMPTY, BILLING_HEADER
from utils.auth import is_admin
from utils.pricing import format_rub

router = Router(name="billing")


@router.message(F.text == "💳 Счета")
@router.message(F.text == "💳 Биллинг")  # старая кнопка, если клавиатура не обновилась
async def show_billing(message: Message) -> None:
    """Список счетов пользователя с пояснением по оплате."""
    user = await get_or_create_user(
        message.from_user.id, username=message.from_user.username
    )
    records = await get_user_billing(user["id"])
    kb = main_menu_kb(is_admin=is_admin(message.from_user.id))

    if not records:
        await message.answer(BILLING_EMPTY, reply_markup=kb, parse_mode="HTML")
        return

    lines = [BILLING_HEADER]
    for rec in records:
        status = BILLING_STATUSES.get(rec["status"], rec["status"])
        date = rec["created_at"][:10]
        paid = (
            f"\n   ✅ Дата оплаты: {rec['paid_at'][:10]}"
            if rec.get("paid_at")
            else ""
        )
        lines.append(
            f"🔹 <b>Счёт #{rec['id']}</b> · заказ #{rec['order_id']}\n"
            f"   💰 {format_rub(rec['amount'])} · {status}\n"
            f"   📅 Создан: {date}{paid}\n"
        )

    await message.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")
