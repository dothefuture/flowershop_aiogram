"""
Telegram-бот «Магазин цветов» на aiogram 3.x + Mini App каталог.

Запуск:
    1. pip install -r requirements.txt
    2. Скопируйте .env.example в .env и заполните переменные
    3. python app.py
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot_setup import setup_bot
from config import load_config
from database import init_db
from handlers import register_handlers
from webserver import start_web_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()

    logger.info("Инициализация базы данных…")
    await init_db()

    web_runner = await start_web_server(port=config.webapp_port)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await setup_bot(bot, config)
    dp = Dispatcher(storage=MemoryStorage())
    register_handlers(dp)

    logger.info("Бот запущен. Mini App: %s", config.webapp_url)
    try:
        await dp.start_polling(bot)
    finally:
        await web_runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен.")
