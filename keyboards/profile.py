"""
Клавиатуры профиля: доставка, заказы.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from texts import BTN_CANCEL


def profile_hub_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Пополнить баланс",
                    callback_data="profile:topup",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Профили доставки",
                    callback_data="profile:profiles",
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
                    text="🏠 На главную",
                    callback_data="profile:home",
                )
            ],
        ]
    )


def profiles_menu_kb(
    profiles: list[dict], default_profile_id: int | None = None
) -> InlineKeyboardMarkup:
    rows = []
    for p in profiles:
        star = "⭐ " if p["id"] == default_profile_id else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{star}{p['title']}: {p['name']}",
                    callback_data=f"profile:view:{p['id']}",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="➕ Новый профиль", callback_data="profile:add")]
    )
    rows.append(
        [InlineKeyboardButton(text="◀️ В профиль", callback_data="profile:hub")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profiles_empty_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Заполнить профиль",
                    callback_data="profile:add",
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ В профиль",
                    callback_data="profile:hub",
                )
            ],
        ]
    )


def profile_detail_kb(profile_id: int, *, is_default: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data=f"profile:edit:{profile_id}",
            )
        ],
    ]
    if not is_default:
        rows.append(
            [
                InlineKeyboardButton(
                    text="⭐ Сделать основным",
                    callback_data=f"profile:default:{profile_id}",
                )
            ]
        )
    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"profile:delete:{profile_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ К профилям",
                    callback_data="profile:profiles",
                )
            ],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


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


def orders_empty_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 В корзину",
                    callback_data="profile:cart",
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="profile:hub",
                )
            ],
        ]
    )


def checkout_profile_kb(
    profiles: list[dict], default_profile_id: int | None = None
) -> InlineKeyboardMarkup:
    rows = []
    for p in profiles:
        star = "⭐ " if p["id"] == default_profile_id else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{star}{p['title']}: {p['name']}",
                    callback_data=f"order:profile:{p['id']}",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="➕ Новый профиль", callback_data="order:profile:new")]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=BTN_CANCEL,
                callback_data="order:profile:cancel",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
