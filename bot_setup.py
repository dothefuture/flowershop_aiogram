"""Настройка бота при запуске: команды и кнопка Mini App."""

from aiogram import Bot
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo

from config import Config


async def setup_bot(bot: Bot, config: Config) -> None:
    """Регистрирует команды и кнопку каталога слева от поля ввода."""
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Перезапуск и главное меню"),
            BotCommand(command="s", description="Быстрый старт"),
        ]
    )
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🌸 Каталог",
            web_app=WebAppInfo(url=config.webapp_url),
        )
    )
