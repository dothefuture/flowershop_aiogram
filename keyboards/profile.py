"""
Клавиатуры профиля: адреса, заказы, счета.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def profile_hub_kb() -> InlineKeyboardMarkup:
    """Главное меню раздела «Профиль»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Адреса доставки",
                    callback_data="profile:addresses",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📖 История заказов",
                    callback_data="profile:orders",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💳 Счета",
                    callback_data="profile:billing",
                )
            ],
        ]
    )


def profiles_menu_kb(profiles: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"📋 {p['title']}: {p['name']}",
                callback_data=f"profile:view:{p['id']}",
            )
        ]
        for p in profiles
    ]
    rows.append(
        [InlineKeyboardButton(text="➕ Новый профиль", callback_data="profile:add")]
    )
    rows.append(
        [InlineKeyboardButton(text="◀️ В профиль", callback_data="profile:hub")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_detail_kb(profile_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=f"profile:edit:{profile_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"profile:delete:{profile_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ К адресам",
                    callback_data="profile:addresses",
                )
            ],
        ]
    )


def profile_edit_fields_kb(profile_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏷 Название",
                    callback_data=f"profile:edit_field:{profile_id}:title",
                ),
                InlineKeyboardButton(
                    text="👤 Имя",
                    callback_data=f"profile:edit_field:{profile_id}:name",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📞 Телефон",
                    callback_data=f"profile:edit_field:{profile_id}:phone",
                ),
                InlineKeyboardButton(
                    text="📍 Адрес",
                    callback_data=f"profile:edit_field:{profile_id}:address",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data=f"profile:view:{profile_id}",
                )
            ],
        ]
    )


def profile_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В профиль", callback_data="profile:hub")]
        ]
    )


def checkout_profile_kb(profiles: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"📋 {p['title']}: {p['name']}",
                callback_data=f"order:profile:{p['id']}",
            )
        ]
        for p in profiles
    ]
    rows.append(
        [InlineKeyboardButton(text="➕ Новый профиль", callback_data="order:profile:new")]
    )
    rows.append(
        [InlineKeyboardButton(text="❌ Отмена", callback_data="order:profile:cancel")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
