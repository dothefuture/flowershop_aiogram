"""
HTTP-сервер для Telegram Mini App: статика каталога и REST API.
"""

from __future__ import annotations

import logging
from pathlib import Path

from aiohttp import web

from database import get_active_products, get_seasonal_settings
from utils.pricing import effective_price

logger = logging.getLogger(__name__)

WEBAPP_DIR = Path(__file__).resolve().parent / "webapp"
PLACEHOLDER_PHOTO = "https://picsum.photos/seed/flower/600/400"


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
            "enabled": seasonal["enabled"] == "1",
        },
        "products": [_product_json(p) for p in products],
    }
    return web.json_response(payload)


async def api_health(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def index_handler(_request: web.Request) -> web.Response:
    index_path = WEBAPP_DIR / "index.html"
    if not index_path.exists():
        return web.Response(text="Mini App not found", status=404)
    return web.FileResponse(index_path)


def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/products", api_products)
    app.router.add_get("/api/health", api_health)
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
