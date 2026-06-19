"""Аватар и оформление личного кабинета."""

from aiogram.types import InputMediaPhoto, Message, User

from utils.formatting import format_telegram_tag
from utils.pricing import format_rub
from utils.ui_format import frame_block, frame_close, frame_line, frame_open


def profile_hub_caption(
    user: User,
    balance: float = 0.0,
    *,
    default_profile: dict | None = None,
) -> str:
    tag = format_telegram_tag(user.username)
    lines = []
    if user.full_name:
        lines.append(f"👤 <b>{user.full_name}</b>")
    lines.append(tag)
    lines.append(f"💰 <b>{format_rub(balance)}</b>")
    if default_profile:
        lines.append(
            f"⭐ {default_profile['title']} · {default_profile['name']}"
        )
    body = frame_block("Личный кабинет", lines, emoji="🌷")
    return body


def profile_detail_text(profile: dict, *, is_default: bool = False) -> str:
    lines = [
        f"🏷 <b>{profile['title']}</b>",
        f"👤 {profile['name']}",
        f"📞 {profile['phone']}",
        f"📍 {profile['address']}",
    ]
    if is_default:
        lines.append("⭐ <i>Основной для заказов</i>")
    return frame_block("Профиль доставки", lines, emoji="📋")


def profiles_list_text(*, has_profiles: bool) -> str:
    if not has_profiles:
        return (
            frame_open("Профили доставки", emoji="📋")
            + "\n\n"
            + frame_line("Пока нет сохранённых профилей.")
            + "\n"
            + frame_line("Создайте профиль при оформлении")
            + "\n"
            + frame_line("заказа или нажмите кнопку ниже.")
            + "\n\n"
            + frame_close()
        )
    return (
        frame_open("Профили доставки", emoji="📋")
        + "\n\n"
        + frame_line("Выберите профиль для просмотра.")
        + "\n"
        + frame_line("⭐ — основной для заказов")
        + "\n\n"
        + frame_close()
    )


async def get_user_avatar_file_id(bot, user_id: int) -> str | None:
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
    except Exception:
        return None
    if not photos.total_count or not photos.photos:
        return None
    return photos.photos[0][-1].file_id


async def send_profile_hub(
    message: Message,
    user: User,
    balance: float = 0.0,
    *,
    default_profile: dict | None = None,
    edit: bool = False,
) -> None:
    from keyboards.profile import profile_hub_kb

    caption = profile_hub_caption(user, balance, default_profile=default_profile)
    kb = profile_hub_kb()
    photo_id = await get_user_avatar_file_id(message.bot, user.id)

    if edit:
        if message.photo and photo_id:
            await message.edit_media(
                media=InputMediaPhoto(
                    media=photo_id,
                    caption=caption,
                    parse_mode="HTML",
                ),
                reply_markup=kb,
            )
            return
        try:
            await message.delete()
        except Exception:
            pass
        if photo_id:
            await message.bot.send_photo(
                message.chat.id,
                photo=photo_id,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML",
            )
        else:
            await message.bot.send_message(
                message.chat.id,
                caption,
                reply_markup=kb,
                parse_mode="HTML",
            )
        return

    if photo_id:
        await message.answer_photo(
            photo=photo_id,
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML",
        )
    else:
        await message.answer(
            caption,
            reply_markup=kb,
            parse_mode="HTML",
        )
