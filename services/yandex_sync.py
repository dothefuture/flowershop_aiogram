"""Фоновая синхронизация статусов заказов с Яндекс Доставкой."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from database import (
    close_order,
    get_orders_for_yandex_sync,
    update_order_status,
    update_order_yandex,
)
from notifications import (
    notify_customer_order_closed,
    notify_customer_status_change,
    notify_yandex_status_change,
)
from services.yandex_config import load_yandex_config
from services.yandex_delivery import (
    YANDEX_CLOSE_CANCELLED,
    YANDEX_CLOSE_DELIVERED,
    YANDEX_IN_PROGRESS,
    get_yandex_client,
)

logger = logging.getLogger(__name__)


async def sync_single_order(bot: Bot, order: dict, client) -> None:
    claim_id = order.get("yandex_claim_id")
    if not claim_id:
        return

    info = await client.get_claim_info(claim_id)
    if not info:
        return

    yandex_status = info.get("status") or info.get("current_status")
    if not yandex_status:
        return

    old_yandex = order.get("yandex_status")
    if yandex_status == old_yandex and order["status"] != "new":
        return

    updated_ts = info.get("updated_ts") or ""
    await update_order_yandex(order["id"], yandex_status, updated_ts)

    order_id = order["id"]
    telegram_id = order["telegram_id"]
    bot_status = order["status"]

    if yandex_status in YANDEX_CLOSE_DELIVERED and bot_status != "closed":
        await close_order(order_id, "delivered")
        await notify_customer_order_closed(bot, telegram_id, order_id, "delivered")
        logger.info("Order #%s closed (Yandex delivered)", order_id)
        return

    if yandex_status in YANDEX_CLOSE_CANCELLED and bot_status != "closed":
        await close_order(order_id, "cancelled")
        await notify_customer_order_closed(bot, telegram_id, order_id, "cancelled")
        logger.info("Order #%s closed (Yandex cancelled)", order_id)
        return

    if yandex_status in YANDEX_IN_PROGRESS and bot_status == "new":
        await update_order_status(order_id, "in_progress")
        await notify_customer_status_change(
            bot, telegram_id, order_id, "in_progress"
        )

    if yandex_status != old_yandex:
        await notify_yandex_status_change(
            bot, telegram_id, order_id, yandex_status
        )


async def yandex_sync_loop(bot: Bot) -> None:
    """Периодически опрашивает Яндекс API для активных заказов."""
    cfg = load_yandex_config()
    if not cfg.enabled:
        logger.info("Yandex Delivery: токен не задан, синхронизация отключена")
        return

    client = get_yandex_client()
    if not client:
        return

    logger.info("Yandex Delivery: синхронизация каждые %s сек", cfg.poll_interval)
    while True:
        try:
            orders = await get_orders_for_yandex_sync()
            for order in orders:
                await sync_single_order(bot, order, client)
                await asyncio.sleep(0.3)
        except Exception:
            logger.exception("Yandex sync loop error")
        await asyncio.sleep(cfg.poll_interval)
