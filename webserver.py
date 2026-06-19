"""
HTTP-сервер: Mini App, LAVA webhook.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from aiohttp import web

from database import get_billing_by_order, get_topup
from services.lava import verify_webhook_signature
from services.payment_flow import on_payment_success, on_topup_success
from utils.pricing import effective_price

if TYPE_CHECKING:
    from aiogram import Bot

from database import get_active_products, get_seasonal_settings

logger = logging.getLogger(__name__)

WEBAPP_DIR = Path(__file__).resolve().parent / "webapp"
PLACEHOLDER_PHOTO = "https://picsum.photos/seed/flower/600/400"

_webhook_bot: Bot | None = None


def set_webhook_bot(bot: Bot) -> None:
    global _webhook_bot
    _webhook_bot = bot


def _product_json(product: dict) -> dict:
    discount = int(product.get("discount_percent") or 0)
    return {
        "id": product["id"],
        "name": product["name"],
        "description": product["description"],
        "price": product["price"],
        "discount_percent": discount,
        "final_price": effective_price(product["price"], discount),
        "photo_url": product["photo_file_id"] or PLACEHOLDER_PHOTO,
        "is_seasonal": bool(product.get("is_seasonal")),
    }


async def api_products(_request: web.Request) -> web.Response:
    products = await get_active_products()
    seasonal = await get_seasonal_settings()
    payload = {
        "seasonal": {
            "title": seasonal["title"],
            "color": seasonal["color"],
            "emoji": seasonal.get("emoji", "🍂"),
            "enabled": seasonal["enabled"] == "1",
        },
        "products": [_product_json(p) for p in products],
    }
    return web.json_response(payload)


async def api_health(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def lava_webhook(request: web.Request) -> web.Response:
    """Webhook LAVA.RU после успешной оплаты."""
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="bad json")

    invoice_id = str(data.get("invoice_id", ""))
    order_id_raw = data.get("order_id")
    amount = str(data.get("amount", ""))
    pay_time = str(data.get("pay_time", ""))
    signature = str(data.get("signature", ""))
    status = str(data.get("status", "")).lower()

    if signature and not verify_webhook_signature(
        invoice_id, amount, pay_time, signature
    ):
        logger.warning("LAVA webhook: invalid signature order=%s", order_id_raw)
        return web.Response(status=403, text="invalid signature")

    if status not in ("success", "paid", "completed", "1"):
        return web.Response(text="ignored")

    if order_id_raw is None or order_id_raw == "":
        return web.Response(status=400, text="no order_id")

    ref = str(order_id_raw)

    if ref.startswith("balance-"):
        try:
            topup_id = int(ref.split("-", 1)[1])
        except ValueError:
            return web.Response(status=400, text="bad topup id")

        topup = await get_topup(topup_id)
        if not topup or topup["status"] == "paid":
            return web.Response(text="OK")

        if _webhook_bot:
            await on_topup_success(_webhook_bot, topup_id)
        else:
            logger.error("Webhook bot not set — topup #%s", topup_id)
        return web.Response(text="OK")

    try:
        order_id = int(ref)
    except ValueError:
        return web.Response(status=400, text="bad order_id")

    billing = await get_billing_by_order(order_id)
    if not billing or billing["status"] == "paid":
        return web.Response(text="OK")

    if _webhook_bot:
        await on_payment_success(_webhook_bot, order_id)
    else:
        logger.error("Webhook bot not set — payment for order #%s", order_id)

    return web.Response(text="OK")


async def index_handler(_request: web.Request) -> web.Response:
    index_path = WEBAPP_DIR / "index.html"
    if not index_path.exists():
        return web.Response(text="Mini App not found", status=404)
    return web.FileResponse(index_path)


def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/products", api_products)
    app.router.add_get("/api/health", api_health)
    app.router.add_post("/webhook/lava", lava_webhook)
    app.router.add_get("/", index_handler)

    if WEBAPP_DIR.exists():
        app.router.add_static("/static/", WEBAPP_DIR / "static", show_index=False)

    return app


async def start_web_server(host: str = "0.0.0.0", port: int = 8080) -> web.AppRunner:
    app = create_web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    logger.info("Mini App сервер: http://%s:%s", host, port)
    return runner
