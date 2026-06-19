"""Показ подстраниц из inline-кнопок (в т.ч. когда хаб — фото)."""

from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


async def show_subpage(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    """Открывает текстовую подстраницу; с фото-хаба отправляет новое сообщение."""
    msg = callback.message
    try:
        await msg.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    if msg.photo:
        return await msg.answer(text, reply_markup=reply_markup, parse_mode="HTML")

    try:
        await msg.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
        return msg
    except Exception:
        return await msg.answer(text, reply_markup=reply_markup, parse_mode="HTML")
