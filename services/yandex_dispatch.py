"""Создание заявки Яндекс Доставки после оплаты."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

import aiohttp
from dotenv import load_dotenv

from database import get_order, get_order_items, set_order_yandex_claim, update_order_status
from services.yandex_config import YANDEX_API_BASE
from services.yandex_config import load_yandex_config

load_dotenv()
logger = logging.getLogger(__name__)


class YandexDispatchError(Exception):
    pass


def _shop_settings() -> tuple[str, str, str]:
    return (
        os.getenv("YANDEX_SHOP_ADDRESS", "Москва").strip(),
        os.getenv("YANDEX_SHOP_PHONE", "+79000000000").strip(),
        os.getenv("YANDEX_SHOP_NAME", "Цветочный рай").strip(),
    )


async def _api_post(path: str, body: dict[str, Any], request_id: str) -> dict[str, Any]:
    cfg = load_yandex_config()
    if not cfg.enabled:
        raise YandexDispatchError("Yandex token не настроен")

    url = f"{YANDEX_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {cfg.token}",
        "Accept-Language": "ru",
        "Content-Type": "application/json",
        "X-Idempotence-Token": request_id,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            params={"request_id": request_id},
            json=body,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            data = await resp.json(content_type=None)
            if resp.status not in (200, 202):
                raise YandexDispatchError(f"HTTP {resp.status}: {data}")
            return data if isinstance(data, dict) else {}


async def create_yandex_claim_for_order(order_id: int) -> str:
    """Создаёт и подтверждает заявку Яндекс для оплаченного заказа."""
    order = await get_order(order_id)
    if not order:
        raise YandexDispatchError("Заказ не найден")
    if order.get("yandex_claim_id"):
        return order["yandex_claim_id"]

    items = await get_order_items(order_id)
    shop_address, shop_phone, shop_name = _shop_settings()
    titles = ", ".join(i["product_name"] for i in items[:5]) or f"Заказ #{order_id}"

    body = {
        "items": [
            {
                "title": titles[:200],
                "quantity": 1,
                "cost_value": f"{order['total_amount']:.2f}",
                "cost_currency": "RUB",
                "weight": 2.0,
            }
        ],
        "route_points": [
            {
                "point_id": 1,
                "visit_order": 1,
                "type": "source",
                "contact": {"name": shop_name, "phone": shop_phone},
                "address": {"fullname": shop_address},
            },
            {
                "point_id": 2,
                "visit_order": 2,
                "type": "destination",
                "contact": {"name": order["name"], "phone": order["phone"]},
                "address": {"fullname": order["address"]},
                "external_order_id": str(order_id),
            },
        ],
        "client_requirements": {"taxi_class": "express"},
        "comment": f"Заказ #{order_id}",
    }

    request_id = str(uuid.uuid4())
    created = await _api_post("/claims/create", body, request_id)
    claim_id = created.get("id") or created.get("claim_id")
    if not claim_id:
        raise YandexDispatchError(f"Нет claim_id в ответе: {created}")

    version = created.get("version", 1)
    accept_body = {"version": version}
    await _api_post(f"/claims/accept?claim_id={claim_id}", accept_body, str(uuid.uuid4()))

    await set_order_yandex_claim(order_id, claim_id)
    await update_order_status(order_id, "in_progress")
    logger.info("Yandex claim %s created for order #%s", claim_id, order_id)
    return claim_id
