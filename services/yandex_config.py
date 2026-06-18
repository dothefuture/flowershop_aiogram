"""Настройки Яндекс Доставки."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

YANDEX_API_BASE = "https://b2b.taxi.yandex.net/b2b/cargo/integration/v2"


@dataclass(frozen=True)
class YandexConfig:
    token: str
    poll_interval: int
    enabled: bool


def load_yandex_config() -> YandexConfig:
    token = os.getenv("YANDEX_DELIVERY_TOKEN", "").strip()
    interval_raw = os.getenv("YANDEX_POLL_INTERVAL", "60").strip()
    interval = int(interval_raw) if interval_raw.isdigit() else 60
    return YandexConfig(
        token=token,
        poll_interval=max(30, interval),
        enabled=bool(token),
    )
