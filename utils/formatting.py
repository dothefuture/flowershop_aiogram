"""Форматирование имён и контактов Telegram."""


def format_telegram_tag(username: str | None) -> str:
    """@username или подпись, если тега нет."""
    if username:
        return f"@{username}"
    return "без @username"


def format_telegram_client(username: str | None, *, html: bool = False) -> str:
    """Строка «Клиент TG» для админки."""
    if username:
        tag = f"@{username}"
        if html:
            return f'<a href="https://t.me/{username}">{tag}</a>'
        return tag
    return "без @username"
