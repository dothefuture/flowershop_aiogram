"""
Клавиатуры административной панели.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import ORDER_STATUSES, format_order_status
from utils.pricing import effective_price


def _product_label(product: dict) -> str:
    """Краткая подпись товара в списке."""
    active = "✅" if product["is_active"] else "👁‍🗨"
    seasonal = " 🍂" if product.get("is_seasonal") else ""
    discount = int(product.get("discount_percent") or 0)
    tag = " 🏷" if discount > 0 else ""
    price = effective_price(product["price"], discount)
    return f"{active}{seasonal}{tag} {product['name']} — {price:.0f} ₽"


def admin_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Товары",
                    callback_data="admin:products",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Сезонное",
                    callback_data="admin:seasonal",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Активные заказы",
                    callback_data="admin:orders",
                ),
                InlineKeyboardButton(
                    text="🔒 Закрытые",
                    callback_data="admin:orders_closed",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💳 Счета",
                    callback_data="admin:billing",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="admin:welcome",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Рассылка",
                    callback_data="admin:broadcast",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Поддержка",
                    callback_data="admin:support",
                )
            ],
        ]
    )


def admin_products_kb(products: list[dict]) -> InlineKeyboardMarkup:
    """Список товаров для управления."""
    rows = [
        [
            InlineKeyboardButton(
                text=_product_label(p),
                callback_data=f"admin:product:{p['id']}",
            )
        ]
        for p in products
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="➕ Добавить товар",
                callback_data="admin:add_product",
            )
        ]
    )
    rows.append(
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin:menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_product_actions_kb(
    product_id: int, is_active: bool, discount: int, is_seasonal: bool
) -> InlineKeyboardMarkup:
    """Действия над конкретным товаром."""
    hide_text = "👁‍🗨 Скрыть из каталога" if is_active else "✅ Показать в каталоге"
    discount_text = (
        f"🏷 Скидка: {discount}% (изменить)"
        if discount > 0
        else "🏷 Установить скидку"
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=f"admin:edit:{product_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=discount_text,
                    callback_data=f"admin:discount:{product_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=hide_text,
                    callback_data=f"admin:toggle:{product_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"admin:delete:{product_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ К списку",
                    callback_data="admin:products",
                )
            ],
        ]
    )


def admin_edit_fields_kb(product_id: int) -> InlineKeyboardMarkup:
    """Выбор поля для редактирования товара."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Название",
                    callback_data=f"admin:edit_field:{product_id}:name",
                ),
                InlineKeyboardButton(
                    text="📄 Описание",
                    callback_data=f"admin:edit_field:{product_id}:description",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✨ AI: описание",
                    callback_data=f"admin:ai_desc:{product_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Цена",
                    callback_data=f"admin:edit_field:{product_id}:price",
                ),
                InlineKeyboardButton(
                    text="🖼 Фото",
                    callback_data=f"admin:edit_field:{product_id}:photo_file_id",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data=f"admin:product:{product_id}",
                )
            ],
        ]
    )


def admin_discount_kb(product_id: int, current_discount: int) -> InlineKeyboardMarkup:
    """Быстрые пресеты скидки и снятие."""
    presets = [5, 10, 15, 20, 25, 30]
    rows: list[list[InlineKeyboardButton]] = []

    for i in range(0, len(presets), 3):
        chunk = presets[i : i + 3]
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{'• ' if p == current_discount else ''}{p}%",
                    callback_data=f"admin:set_discount:{product_id}:{p}",
                )
                for p in chunk
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="✏️ Свой процент",
                callback_data=f"admin:custom_discount:{product_id}",
            )
        ]
    )
    if current_discount > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    text="❌ Снять скидку",
                    callback_data=f"admin:set_discount:{product_id}:0",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"admin:product:{product_id}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_orders_kb(orders: list[dict]) -> InlineKeyboardMarkup:
    """Список заказов для администратора."""
    rows = []
    for o in orders:
        status_label = format_order_status(o)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"#{o['id']} — {o['total_amount']:.0f} ₽ — {status_label}",
                    callback_data=f"admin:order:{o['id']}",
                )
            ]
        )
    if not rows:
        rows.append(
            [
                InlineKeyboardButton(
                    text="— заказов нет —",
                    callback_data="admin:noop",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin:menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_order_status_kb(order_id: int, order: dict) -> InlineKeyboardMarkup:
    """Кнопки смены статуса заказа (только для активных)."""
    current_status = order["status"]
    rows: list[list[InlineKeyboardButton]] = []

    if current_status != "closed":
        if current_status != "in_progress":
            rows.append(
                [
                    InlineKeyboardButton(
                        text="🔄 В работе",
                        callback_data=f"admin:order_status:{order_id}:in_progress",
                    )
                ]
            )
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Доставлен",
                    callback_data=f"admin:order_close:{order_id}:delivered",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="❌ Отменён",
                    callback_data=f"admin:order_close:{order_id}:cancelled",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="🚕 Привязать Яндекс",
                    callback_data=f"admin:yandex_link:{order_id}",
                )
            ]
        )
    else:
        label = format_order_status(order)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🔒 {label} — нельзя изменить",
                    callback_data="admin:noop",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🗑 Удалить заказ",
                callback_data=f"admin:delete_order:{order_id}",
            )
        ]
    )
    back_cb = (
        "admin:orders_closed" if current_status == "closed" else "admin:orders"
    )
    rows.append(
        [InlineKeyboardButton(text="◀️ К списку", callback_data=back_cb)]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_welcome_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🖼 Картинка",
                    callback_data="admin:welcome_photo",
                ),
                InlineKeyboardButton(
                    text="📝 Текст",
                    callback_data="admin:welcome_text",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="admin:menu",
                )
            ],
        ]
    )


def admin_seasonal_kb(color: str, enabled: bool, emoji: str, title: str) -> InlineKeyboardMarkup:
    """Настройки сезонного раздела."""
    toggle = "⛔ Выключить раздел" if enabled else "✅ Включить раздел"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Название: {title[:20]}",
                    callback_data="admin:seasonal_title",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Эмодзи: {emoji}",
                    callback_data="admin:seasonal_emoji",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🎨 Цвет: {color}",
                    callback_data="admin:seasonal_color",
                )
            ],
            [
                InlineKeyboardButton(
                    text=toggle,
                    callback_data="admin:seasonal_enabled",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Товары сезонного",
                    callback_data="admin:seasonal_products",
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="admin:menu",
                )
            ],
        ]
    )


def admin_seasonal_products_kb(products: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for p in products:
        name = p["name"]
        if len(name) > 28:
            name = name[:27] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"❌ {name}",
                    callback_data=f"admin:seasonal_rm:{p['id']}",
                )
            ]
        )
    if not rows:
        rows.append(
            [
                InlineKeyboardButton(
                    text="— пока пусто —",
                    callback_data="admin:noop",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="➕ Добавить товар",
                callback_data="admin:seasonal_pick",
            )
        ]
    )
    rows.append(
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin:seasonal")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_seasonal_pick_kb(products: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for p in products:
        if p.get("is_seasonal"):
            continue
        name = p["name"]
        if not p.get("is_active"):
            name = f"👁 {name}"
        if len(name) > 30:
            name = name[:29] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text=name,
                    callback_data=f"admin:seasonal_add:{p['id']}",
                )
            ]
        )
    if not rows:
        rows.append(
            [InlineKeyboardButton(text="— все уже в сезонном —", callback_data="admin:noop")]
        )
    rows.append(
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin:seasonal_products")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_broadcast_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Отправить всем",
                    callback_data="admin:broadcast:send",
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="admin:broadcast:cancel",
                ),
            ]
        ]
    )


def admin_support_threads_kb(threads: list[dict]) -> InlineKeyboardMarkup:
    from utils.formatting import format_telegram_client

    rows = []
    for t in threads:
        tag = format_telegram_client(t.get("username"))
        unread = f" ({t['unread_admin']} нов.)" if t.get("unread_admin") else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"💬 {tag}{unread}",
                    callback_data=f"admin:support_reply:{t['user_id']}",
                )
            ]
        )
    if not rows:
        rows.append(
            [InlineKeyboardButton(text="— обращений нет —", callback_data="admin:noop")]
        )
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_ai_confirm_kb(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Применить",
                    callback_data=f"admin:ai_apply:{product_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"admin:product:{product_id}",
                ),
            ]
        ]
    )
