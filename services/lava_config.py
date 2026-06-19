"""Настройки LAVA.RU."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

LAVA_API_PROD = "https://api.lava.ru/business/invoice/create"
LAVA_API_SANDBOX = "https://dev.lava.ru/business/invoice/create"


def lava_api_url() -> str:
    """Боевой api.lava.ru по умолчанию; dev.lava.ru — если LAVA_SANDBOX=1."""
    if os.getenv("LAVA_SANDBOX", "").strip().lower() in ("1", "true", "yes"):
        return LAVA_API_SANDBOX
    return os.getenv("LAVA_API_URL", LAVA_API_PROD).strip() or LAVA_API_PROD


@dataclass(frozen=True)
class LavaConfig:
    shop_id: str
    secret_key: str
    secret_key_2: str
    hook_url: str
    enabled: bool


def load_lava_config() -> LavaConfig:
    shop_id = os.getenv("LAVA_SHOP_ID", "").strip()
    secret = os.getenv("LAVA_SECRET_KEY", "").strip()
    secret2 = os.getenv("LAVA_SECRET_KEY_2", "").strip()
    hook = os.getenv("LAVA_HOOK_URL", "").strip()
    return LavaConfig(
        shop_id=shop_id,
        secret_key=secret,
        secret_key_2=secret2,
        hook_url=hook,
        enabled=bool(shop_id and secret),
    )
