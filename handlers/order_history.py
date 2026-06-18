"""
История заказов — активные и закрытые.
"""

from aiogram import F, Router
from aiogram.types import Message

from database import format_order_status, get_or_create_user, get_user_orders
from keyboards.main import main_menu_kb
from utils.auth import is_admin
from utils.pricing import format_rub

router = Router(name="order_history")


@router.message(F.text == "📖 История заказов")
async def show_order_history(message: Message) -> None:
    """Список активных и закрытых заказов пользователя."""
    user = await get_or_create_user(message.from_user.id)
    active = await get_user_orders(user["id"], closed_only=False)
    closed = await get_user_orders(user["id"], closed_only=True)

    if not active and not closed:
        await message.answer(
            "📖 <b>История заказов</b>\n\n"
            "У вас пока нет заказов — загляните в 🌷 Каталог!",
            reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
            parse_mode="HTML",
        )
        return

    lines = ["📖 <b>История заказов</b>\n"]

    if active:
        lines.append("<b>Активные:</b>")
        for order in active:
            status = format_order_status(order)
            lines.append(
                f"🔹 <b>#{order['id']}</b> · {order['created_at'][:10]}\n"
                f"   💰 {format_rub(order['total_amount'])} · {status}\n"
            )

    if closed:
        lines.append("\n<b>🔒 Закрытые:</b>")
        for order in closed:
            status = format_order_status(order)
            lines.append(
                f"🔹 <b>#{order['id']}</b> · {order['created_at'][:10]}\n"
                f"   💰 {format_rub(order['total_amount'])} · {status}\n"
            )

    await message.answer(
        "\n".join(lines),
        reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
        parse_mode="HTML",
    )
