"""Клиент API Яндекс Доставки (Express / Cargo)."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from services.yandex_config import YANDEX_API_BASE, load_yandex_config

logger = logging.getLogger(__name__)

# Человекочитаемые статусы Яндекс Доставки
YANDEX_STATUS_LABELS: dict[str, str] = {
    "new": "🆕 Заявка создана",
    "estimating": "⏳ Расчёт стоимости",
    "ready_for_approval": "✅ Ожидает подтверждения",
    "accepted": "📋 Принята",
    "performer_lookup": "🔍 Поиск курьера",
    "performer_draft": "🔍 Подбор курьера",
    "performer_found": "🚕 Курьер найден",
    "pickup_arrived": "📦 Курьер у отправителя",
    "ready_for_pickup_confirmation": "📦 Ожидание передачи",
    "pickuped": "🌸 Заказ забран курьером",
    "delivery_arrived": "🏠 Курьер у получателя",
    "ready_for_delivery_confirmation": "🏠 Ожидание вручения",
    "pay_waiting": "💳 Ожидание оплаты",
    "delivered": "✅ Доставлен",
    "delivered_finish": "✅ Доставка завершена",
    "returning": "↩️ Возврат",
    "return_arrived": "↩️ Курьер на возврате",
    "returned": "↩️ Возвращён",
    "returned_finish": "↩️ Возврат завершён",
    "cancelled": "❌ Отменён",
    "cancelled_by_taxi": "❌ Отменён службой",
    "cancelled_with_payment": "❌ Отменён (платно)",
    "cancelled_with_items_on_hands": "❌ Отменён (товар у курьера)",
    "failed": "❌ Ошибка доставки",
    "estimating_failed": "❌ Не удалось рассчитать",
    "performer_not_found": "❌ Курьер не найден",
}


def format_yandex_status(status: str | None) -> str:
    if not status:
        return "— не привязан —"
    return YANDEX_STATUS_LABELS.get(status, status)


# Статусы → действие для бота: in_progress | close_delivered | close_cancelled
YANDEX_CLOSE_DELIVERED = {"delivered", "delivered_finish"}
YANDEX_CLOSE_CANCELLED = {
    "cancelled",
    "cancelled_by_taxi",
    "cancelled_with_payment",
    "cancelled_with_items_on_hands",
    "failed",
    "estimating_failed",
    "performer_not_found",
    "returned",
    "returned_finish",
}
YANDEX_IN_PROGRESS = {
    "accepted",
    "performer_lookup",
    "performer_draft",
    "performer_found",
    "pickup_arrived",
    "ready_for_pickup_confirmation",
    "pickuped",
    "delivery_arrived",
    "ready_for_delivery_confirmation",
    "pay_waiting",
    "returning",
    "return_arrived",
    "ready_for_return_confirmation",
}


class YandexDeliveryClient:
    """HTTP-клиент Яндекс Доставки."""

    def __init__(self, token: str) -> None:
        self._token = token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept-Language": "ru",
            "Content-Type": "application/json",
        }

    async def get_claim_info(self, claim_id: str) -> dict[str, Any] | None:
        url = f"{YANDEX_API_BASE}/claims/info"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params={"claim_id": claim_id},
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    body = await resp.text()
                    logger.warning(
                        "Yandex claims/info %s: HTTP %s — %s",
                        claim_id,
                        resp.status,
                        body[:200],
                    )
        except Exception as exc:
            logger.exception("Yandex API error for %s: %s", claim_id, exc)
        return None


def get_yandex_client() -> YandexDeliveryClient | None:
    cfg = load_yandex_config()
    if not cfg.enabled:
        return None
    return YandexDeliveryClient(cfg.token)
