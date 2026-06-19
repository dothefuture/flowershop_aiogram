"""Клиент LAVA.RU — выставление счетов и проверка webhook."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

import aiohttp

from services.lava_config import lava_api_url, load_lava_config

logger = logging.getLogger(__name__)


def _serialize_payload(payload: dict[str, Any]) -> bytes:
    """JSON в том же виде, что требует документация LAVA (data-raw)."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sign_payload(raw: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def verify_webhook_signature(
    invoice_id: str, amount: str, pay_time: str, signature: str
) -> bool:
    cfg = load_lava_config()
    if not cfg.secret_key_2:
        return False
    expected = hashlib.md5(
        f"{invoice_id}:{amount}:{pay_time}:{cfg.secret_key_2}".encode()
    ).hexdigest()
    return expected == signature


async def create_payment_invoice(
    payment_ref: str | int,
    amount: float,
    *,
    comment: str = "",
) -> dict[str, Any] | None:
    """Создаёт счёт LAVA и возвращает {invoice_id, payment_url}."""
    cfg = load_lava_config()
    if not cfg.enabled:
        logger.warning("LAVA не настроена — задайте LAVA_SHOP_ID и LAVA_SECRET_KEY")
        return None

    payload: dict[str, Any] = {
        "shopId": cfg.shop_id,
        "sum": round(float(amount), 2),
        "orderId": str(payment_ref),
        "comment": (comment or f"Оплата {payment_ref}")[:255],
    }
    if cfg.hook_url:
        payload["hookUrl"] = cfg.hook_url

    raw = _serialize_payload(payload)
    signature = _sign_payload(raw, cfg.secret_key)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Signature": signature,
    }

    url = lava_api_url()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=raw,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text) if text else {}
                except json.JSONDecodeError:
                    logger.warning(
                        "LAVA create invoice: не JSON (HTTP %s): %s",
                        resp.status,
                        text[:300],
                    )
                    return None

                if resp.status != 200:
                    logger.warning("LAVA create invoice HTTP %s: %s", resp.status, data)
                    return None

                if isinstance(data, dict) and data.get("status_check") is False:
                    logger.warning("LAVA status_check=false: %s", data)
                    return None

                inner = data.get("data") if isinstance(data, dict) else None
                if not isinstance(inner, dict):
                    inner = data if isinstance(data, dict) else {}

                invoice_id = inner.get("id") or inner.get("invoice_id")
                payment_url = (
                    inner.get("url")
                    or inner.get("paymentUrl")
                    or inner.get("payment_url")
                )
                if payment_url:
                    return {
                        "invoice_id": str(invoice_id) if invoice_id else "",
                        "payment_url": payment_url,
                    }
                logger.warning("LAVA: нет url в ответе (%s): %s", url, data)
    except Exception:
        logger.exception("LAVA create invoice error (%s)", url)
    return None
