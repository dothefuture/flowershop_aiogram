"""
Клавиатуры для профилей доставки и выбора при оформлении заказа.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def profiles_menu_kb(profiles: list[dict]) -> InlineKeyboardMarkup:
    """Меню управления профилями."""
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
        [
            InlineKeyboardButton(
                text="➕ Новый профиль",
                callback_data="profile:add",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_detail_kb(profile_id: int) -> InlineKeyboardMarkup:
    """Действия над профилем."""
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
                    text="◀️ К списку",
                    callback_data="profile:list",
                )
            ],
        ]
    )


def profile_edit_fields_kb(profile_id: int) -> InlineKeyboardMarkup:
    """Выбор поля для редактирования профиля."""
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


def checkout_profile_kb(profiles: list[dict]) -> InlineKeyboardMarkup:
    """Выбор профиля при оформлении заказа."""
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
        [
            InlineKeyboardButton(
                text="➕ Новый профиль",
                callback_data="order:profile:new",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="order:profile:cancel",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
