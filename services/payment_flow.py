"""Обработка успешной оплаты заказов и пополнения баланса."""

from __future__ import annotations

import logging

from aiogram import Bot

from database import get_order, get_order_items, get_topup_with_user, mark_billing_paid, mark_topup_paid
from notifications import notify_admin_new_order, notify_payment_received
from services.yandex_dispatch import YandexDispatchError, create_yandex_claim_for_order
from utils.pricing import format_rub

logger = logging.getLogger(__name__)


async def on_payment_success(bot: Bot, order_id: int) -> None:
    """После оплаты заказа: Яндекс Доставка и уведомления."""
    order = await get_order(order_id)
    if not order:
        logger.warning("Payment for unknown order #%s", order_id)
        return

    await mark_billing_paid(order_id)

    try:
        claim_id = await create_yandex_claim_for_order(order_id)
        yandex_msg = f"🚕 Заявка Яндекс создана: <code>{claim_id}</code>"
    except YandexDispatchError as exc:
        logger.warning("Yandex dispatch failed for #%s: %s", order_id, exc)
        yandex_msg = f"⚠️ Яндекс: {exc} — привяжите вручную в админке."

    await notify_payment_received(
        bot=bot,
        telegram_id=order["telegram_id"],
        order_id=order_id,
        yandex_info=yandex_msg,
    )

    items = await get_order_items(order_id)
    await notify_admin_new_order(
        bot=bot,
        order_id=order_id,
        name=order["name"],
        phone=order["phone"],
        address=order["address"],
        items=items,
        total=order["total_amount"],
        client_username=order.get("username"),
        paid=True,
        yandex_info=yandex_msg,
    )


async def on_topup_success(bot: Bot, topup_id: int) -> None:
    """После оплаты пополнения баланса через LAVA."""
    if not await mark_topup_paid(topup_id):
        return

    topup = await get_topup_with_user(topup_id)
    if not topup:
        return

    from database import get_user_balance

    balance = await get_user_balance(topup["user_id"])
    try:
        await bot.send_message(
            topup["telegram_id"],
            f"✅ <b>Баланс пополнен на {format_rub(topup['amount'])}</b>\n\n"
            f"💰 Текущий баланс: <b>{format_rub(balance)}</b>",
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Failed to notify user about topup #%s", topup_id)
