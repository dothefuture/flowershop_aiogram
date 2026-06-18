"""Загрузка конфигурации из переменных окружения (.env)."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Настройки приложения."""

    bot_token: str
    admin_ids: tuple[int, ...]
    webapp_url: str
    webapp_port: int


def _parse_admin_ids() -> tuple[int, ...]:
    """ADMIN_IDS=111,222 или устаревший ADMIN_ID=111."""
    ids_raw = os.getenv("ADMIN_IDS", "").strip()
    if ids_raw:
        ids = []
        for part in ids_raw.split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))
        if ids:
            return tuple(ids)

    admin_raw = os.getenv("ADMIN_ID", "").strip()
    if admin_raw.isdigit():
        return (int(admin_raw),)

    raise ValueError(
        "ADMIN_IDS не задан. Укажите ID через запятую, например: ADMIN_IDS=123,456"
    )


def load_config() -> Config:
    """Читает и валидирует конфигурацию из .env файла."""
    token = os.getenv("BOT_TOKEN", "").strip()
    webapp_url = os.getenv("WEBAPP_URL", "http://127.0.0.1:8080").strip()
    webapp_port_raw = os.getenv("WEBAPP_PORT", "8080").strip()

    if not token:
        raise ValueError(
            "BOT_TOKEN не задан. Скопируйте .env.example в .env и укажите токен бота."
        )
    if not webapp_port_raw.isdigit():
        raise ValueError("WEBAPP_PORT должен быть числом.")

    return Config(
        bot_token=token,
        admin_ids=_parse_admin_ids(),
        webapp_url=webapp_url.rstrip("/"),
        webapp_port=int(webapp_port_raw),
    )
