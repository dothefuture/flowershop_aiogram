"""
Уведомления администратору и клиентам.
"""

from aiogram import Bot

from database import ORDER_STATUSES
from utils.auth import get_admin_ids
from texts import (
    ADMIN_NEW_ORDER,
    CUSTOMER_ORDER_CANCELLED,
    CUSTOMER_ORDER_DELIVERED,
    CUSTOMER_STATUS_CHANGED,
)
from utils.formatting import format_telegram_client
from utils.pricing import format_rub


async def notify_admin_new_order(
    bot: Bot,
    order_id: int,
    name: str,
    phone: str,
    address: str,
    items: list[dict],
    total: float,
    *,
    client_username: str | None = None,
    paid: bool = False,
    yandex_info: str = "",
) -> None:
    """Отправляет администраторам уведомление о заказе."""
    items_text = "\n".join(
        f"• {item['product_name']} — {item['quantity']} × {format_rub(item['price'])}"
        for item in items
    )
    header = "🔔 <b>Оплаченный заказ" if paid else "🔔 <b>Новый заказ"
    text = ADMIN_NEW_ORDER.format(
        header=header,
        order_id=order_id,
        client_tag=format_telegram_client(client_username),
        name=name,
        phone=phone,
        address=address,
        items=items_text,
        total=total,
        extra=f"\n{yandex_info}" if yandex_info else "",
    )
    try:
        for admin_id in get_admin_ids():
            await bot.send_message(admin_id, text, parse_mode="HTML")
    except Exception:
        pass


async def notify_payment_received(
    bot: Bot,
    telegram_id: int,
    order_id: int,
    *,
    yandex_info: str = "",
) -> None:
    from texts import PAYMENT_SUCCESS

    text = PAYMENT_SUCCESS.format(order_id=order_id, yandex_info=yandex_info)
    try:
        await bot.send_message(telegram_id, text, parse_mode="HTML")
    except Exception:
        pass


async def notify_customer_status_change(
    bot: Bot,
    telegram_id: int,
    order_id: int,
    new_status: str,
) -> None:
    """Уведомляет клиента об изменении статуса заказа (не закрытие)."""
    status_label = ORDER_STATUSES.get(new_status, new_status)
    text = CUSTOMER_STATUS_CHANGED.format(
        order_id=order_id,
        status=status_label,
    )
    try:
        await bot.send_message(telegram_id, text, parse_mode="HTML")
    except Exception:
        pass


async def notify_customer_order_closed(
    bot: Bot,
    telegram_id: int,
    order_id: int,
    reason: str,
) -> None:
    """Уведомляет клиента о закрытии заказа (доставлен / отменён)."""
    if reason == "delivered":
        text = CUSTOMER_ORDER_DELIVERED.format(order_id=order_id)
    else:
        text = CUSTOMER_ORDER_CANCELLED.format(order_id=order_id)
    try:
        await bot.send_message(telegram_id, text, parse_mode="HTML")
    except Exception:
        pass


async def notify_yandex_status_change(
    bot: Bot,
    telegram_id: int,
    order_id: int,
    yandex_status: str,
) -> None:
    from services.yandex_delivery import format_yandex_status
    from texts import YANDEX_STATUS_NOTIFY

    text = YANDEX_STATUS_NOTIFY.format(
        order_id=order_id,
        yandex_status=format_yandex_status(yandex_status),
    )
    try:
        await bot.send_message(telegram_id, text, parse_mode="HTML")
    except Exception:
        pass
