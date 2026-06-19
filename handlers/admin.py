"""
Административная панель: товары, скидки, сезонное, заказы, биллинг.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import (
    BILLING_STATUSES,
    ORDER_STATUSES,
    add_product,
    add_support_message,
    close_order,
    delete_order,
    delete_product,
    format_order_status,
    get_all_billing,
    get_all_orders,
    get_all_products,
    get_all_telegram_ids,
    get_billing_stats,
    get_open_support_threads,
    get_order,
    get_order_items,
    get_product,
    get_seasonal_settings,
    get_support_thread_by_user,
    mark_support_read,
    set_order_yandex_claim,
    set_product_seasonal,
    set_setting,
    set_product_discount,
    toggle_product_active,
    update_order_status,
    update_product_field,
)
from utils.auth import is_admin
from keyboards.admin import (
    admin_ai_confirm_kb,
    admin_broadcast_confirm_kb,
    admin_discount_kb,
    admin_edit_fields_kb,
    admin_menu_kb,
    admin_order_status_kb,
    admin_orders_kb,
    admin_product_actions_kb,
    admin_products_kb,
    admin_seasonal_kb,
    admin_seasonal_pick_kb,
    admin_seasonal_products_kb,
    admin_support_threads_kb,
    admin_welcome_kb,
)
from keyboards.main import main_menu_kb
from notifications import (
    notify_customer_order_closed,
    notify_customer_status_change,
)
from states import (
    AdminAddProductStates,
    AdminAIStates,
    AdminBroadcastStates,
    AdminDiscountStates,
    AdminEditProductStates,
    AdminSeasonalStates,
    AdminSupportStates,
    AdminWelcomeStates,
    AdminYandexStates,
)
from texts import ADMIN_PANEL, ADMIN_PRODUCTS_HEADER, BROADCAST_DONE, BROADCAST_PREVIEW, SUPPORT_ADMIN_REPLY_SENT
from utils.formatting import format_telegram_client
from utils.pricing import effective_price, format_price_line, format_rub
from services.yandex_delivery import format_yandex_status, get_yandex_client
from services.ai_text import AIError, enhance_product_description

router = Router(name="admin")


def _product_detail_text(product: dict) -> str:
    status = "✅ В каталоге" if product["is_active"] else "👁‍🗨 Скрыт"
    seasonal = "🍂 Сезонное" if product.get("is_seasonal") else "Обычный"
    discount = int(product.get("discount_percent") or 0)
    price_line = format_price_line(product["price"], discount)
    discount_info = (
        f"\n🏷 Скидка: <b>{discount}%</b> → "
        f"цена: <b>{format_rub(effective_price(product['price'], discount))}</b>"
        if discount > 0
        else "\n🏷 Скидка не установлена"
    )
    return (
        f"📦 <b>{product['name']}</b>\n\n"
        f"{product['description']}\n\n"
        f"{price_line}\n"
        f"{discount_info}\n"
        f"Раздел: {seasonal}\n"
        f"Статус: {status}"
    )


async def open_admin_panel(message: Message) -> None:
    """Открывает админ-панель (кнопка или команда)."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer(ADMIN_PANEL, reply_markup=admin_menu_kb(), parse_mode="HTML")


@router.message(F.text == "🔧 Админ-панель")
async def btn_admin(message: Message) -> None:
    await open_admin_panel(message)


@router.message(F.text == "/admin")
async def cmd_admin(message: Message) -> None:
    await open_admin_panel(message)


@router.callback_query(F.data == "admin:menu")
async def admin_menu(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.message.edit_text(
        ADMIN_PANEL, reply_markup=admin_menu_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:noop")
async def admin_noop(callback: CallbackQuery) -> None:
    await callback.answer()


# ── Сезонное ────────────────────────────────────────────────────────────────


def _seasonal_menu_text(settings: dict[str, str]) -> str:
    enabled = settings["enabled"] == "1"
    emoji = settings.get("emoji", "🍂")
    return (
        f"<b>Сезонный раздел</b> «{settings['title']}»\n\n"
        f"Статус: {'✅ включён' if enabled else '⛔ выключён'}\n"
        f"Название: <b>{settings['title']}</b>\n"
        f"Эмодзи в каталоге: {emoji}\n"
        f"Цвет выделения: <code>{settings['color']}</code>"
    )


@router.callback_query(F.data == "admin:seasonal")
async def admin_seasonal_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.clear()
    settings = await get_seasonal_settings()
    enabled = settings["enabled"] == "1"
    await callback.message.edit_text(
        _seasonal_menu_text(settings),
        reply_markup=admin_seasonal_kb(
            settings["color"],
            enabled,
            settings.get("emoji", "🍂"),
            settings["title"],
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin:seasonal_enabled")
async def admin_seasonal_toggle(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    settings = await get_seasonal_settings()
    new_val = "0" if settings["enabled"] == "1" else "1"
    await set_setting("seasonal_enabled", new_val)
    settings = await get_seasonal_settings()
    enabled = settings["enabled"] == "1"
    await callback.message.edit_text(
        _seasonal_menu_text(settings),
        reply_markup=admin_seasonal_kb(
            settings["color"],
            enabled,
            settings.get("emoji", "🍂"),
            settings["title"],
        ),
        parse_mode="HTML",
    )
    await callback.answer("Обновлено")


@router.callback_query(F.data == "admin:seasonal_title")
async def admin_seasonal_title_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    settings = await get_seasonal_settings()
    await state.set_state(AdminSeasonalStates.title)
    await callback.message.answer(
        "Введите <b>название сезонного раздела</b>\n"
        f"<i>Текущее: {settings['title']}</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminSeasonalStates.title)
async def admin_seasonal_title_value(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    title = message.text.strip()
    if len(title) < 2:
        await message.answer("Название слишком короткое.")
        return
    await set_setting("seasonal_title", title[:40])
    await state.clear()
    await message.answer(
        f"✅ Название сезонного раздела: <b>{title[:40]}</b>",
        reply_markup=main_menu_kb(is_admin=True),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:seasonal_emoji")
async def admin_seasonal_emoji_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.set_state(AdminSeasonalStates.emoji)
    await callback.message.answer(
        "Отправьте <b>один эмодзи</b> для сезонного раздела\n"
        "<i>Например: 🍂 🌸 ❄️</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminSeasonalStates.emoji)
async def admin_seasonal_emoji_value(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    emoji = message.text.strip()
    if not emoji or len(emoji) > 8:
        await message.answer("❌ Отправьте один эмодзи")
        return
    await set_setting("seasonal_emoji", emoji[:4])
    await state.clear()
    await message.answer(
        f"✅ Эмодзи сезонного раздела: {emoji[:4]}",
        reply_markup=main_menu_kb(is_admin=True),
    )


@router.callback_query(F.data == "admin:seasonal_color")
async def admin_seasonal_color_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.set_state(AdminSeasonalStates.color)
    await callback.message.answer(
        "🎨 Введите цвет в формате HEX (например <code>#FF6B35</code>):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminSeasonalStates.color)
async def admin_seasonal_color_value(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    color = message.text.strip()
    if not color.startswith("#") or len(color) not in (4, 7):
        await message.answer("❌ Некорректный HEX. Пример: #FF6B35")
        return
    await set_setting("seasonal_color", color)
    await state.clear()
    await message.answer(
        f"✅ Цвет сезонного раздела: {color}",
        reply_markup=main_menu_kb(is_admin=True),
    )


@router.callback_query(F.data == "admin:seasonal_products")
async def admin_seasonal_products(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    products = await get_all_products()
    seasonal = [p for p in products if p.get("is_seasonal")]
    settings = await get_seasonal_settings()
    emoji = settings.get("emoji", "🍂")
    await callback.message.edit_text(
        f"{emoji} <b>Товары сезонного раздела</b>\n\n"
        f"Нажмите ❌ чтобы убрать, ➕ чтобы добавить:",
        reply_markup=admin_seasonal_products_kb(seasonal),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin:seasonal_pick")
async def admin_seasonal_pick(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    products = await get_all_products()
    available = [p for p in products if not p.get("is_seasonal")]
    await callback.message.edit_text(
        "➕ <b>Добавить в сезонное</b>\n\nВыберите товар:",
        reply_markup=admin_seasonal_pick_kb(available),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:seasonal_add:"))
async def admin_seasonal_add_product(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    product_id = int(callback.data.split(":")[-1])
    await set_product_seasonal(product_id, True)
    await callback.answer("Добавлено в сезонное", show_alert=True)
    products = await get_all_products()
    seasonal = [p for p in products if p.get("is_seasonal")]
    settings = await get_seasonal_settings()
    emoji = settings.get("emoji", "🍂")
    await callback.message.edit_text(
        f"{emoji} <b>Товары сезонного раздела</b>\n\n"
        f"Нажмите ❌ чтобы убрать, ➕ чтобы добавить:",
        reply_markup=admin_seasonal_products_kb(seasonal),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:seasonal_rm:"))
async def admin_seasonal_remove_product(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    product_id = int(callback.data.split(":")[-1])
    await set_product_seasonal(product_id, False)
    await callback.answer("Убрано из сезонного", show_alert=True)
    products = await get_all_products()
    seasonal = [p for p in products if p.get("is_seasonal")]
    settings = await get_seasonal_settings()
    emoji = settings.get("emoji", "🍂")
    await callback.message.edit_text(
        f"{emoji} <b>Товары сезонного раздела</b>\n\n"
        f"Нажмите ❌ чтобы убрать, ➕ чтобы добавить:",
        reply_markup=admin_seasonal_products_kb(seasonal),
        parse_mode="HTML",
    )


# ── Товары ────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "admin:products")
async def admin_products_list(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.clear()
    products = await get_all_products()
    await callback.message.edit_text(
        ADMIN_PRODUCTS_HEADER.format(count=len(products)),
        reply_markup=admin_products_kb(products),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:product:"))
async def admin_product_detail(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    product_id = int(callback.data.split(":")[-1])
    product = await get_product(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return
    discount = int(product.get("discount_percent") or 0)
    await callback.message.edit_text(
        _product_detail_text(product),
        reply_markup=admin_product_actions_kb(
            product_id,
            bool(product["is_active"]),
            discount,
            bool(product.get("is_seasonal")),
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin:add_product")
async def admin_add_product_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.set_state(AdminAddProductStates.name)
    await callback.message.answer(
        "➕ <b>Добавление товара</b>\n\nВведите <b>название</b>:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminAddProductStates.name)
async def admin_add_name(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Название слишком короткое:")
        return
    await state.update_data(name=name)
    await state.set_state(AdminAddProductStates.description)
    await message.answer("Введите <b>описание</b> товара:", parse_mode="HTML")


@router.message(AdminAddProductStates.description)
async def admin_add_description(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    description = message.text.strip()
    if len(description) < 5:
        await message.answer("Описание слишком короткое:")
        return
    await state.update_data(description=description)
    await state.set_state(AdminAddProductStates.price)
    await message.answer("Введите <b>цену</b> (число):", parse_mode="HTML")


@router.message(AdminAddProductStates.price)
async def admin_add_price(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip().replace(",", ".")
    try:
        price = float(raw)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Некорректная цена.")
        return
    await state.update_data(price=price)
    await state.set_state(AdminAddProductStates.photo)
    await message.answer("Отправьте <b>фотографию</b> товара:", parse_mode="HTML")


@router.message(AdminAddProductStates.photo, F.photo)
async def admin_add_photo(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    product_id = await add_product(
        name=data["name"],
        description=data["description"],
        price=data["price"],
        photo_file_id=photo_id,
    )
    await state.clear()
    await message.answer(
        f"✅ Товар «{data['name']}» добавлен (ID: {product_id}).",
        reply_markup=main_menu_kb(is_admin=True),
    )


@router.message(AdminAddProductStates.photo)
async def admin_add_photo_invalid(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("❌ Отправьте фото.")


@router.callback_query(F.data.startswith("admin:edit:"))
async def admin_edit_start(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    product_id = int(callback.data.split(":")[-1])
    await callback.message.edit_text(
        "✏️ <b>Редактирование товара</b>\n\nВыберите поле:",
        reply_markup=admin_edit_fields_kb(product_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:edit_field:"))
async def admin_edit_field_select(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    parts = callback.data.split(":")
    product_id, field = int(parts[2]), parts[3]
    field_labels = {
        "name": "название",
        "description": "описание",
        "price": "цену",
        "photo_file_id": "новое фото",
    }
    await state.update_data(edit_product_id=product_id, edit_field=field)
    await state.set_state(AdminEditProductStates.edit_value)
    hint = field_labels.get(field, field)
    if field == "photo_file_id":
        await callback.message.answer(f"Отправьте {hint}:")
    else:
        await callback.message.answer(f"Введите новое значение — {hint}:")
    await callback.answer()


@router.message(AdminEditProductStates.edit_value, F.photo)
async def admin_edit_photo(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    if data.get("edit_field") != "photo_file_id":
        await message.answer("Сейчас ожидается текст.")
        return
    await update_product_field(data["edit_product_id"], "photo_file_id", message.photo[-1].file_id)
    await state.clear()
    await message.answer("✅ Фото обновлено.", reply_markup=main_menu_kb(is_admin=True))


@router.message(AdminEditProductStates.edit_value)
async def admin_edit_value(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    product_id, field = data["edit_product_id"], data["edit_field"]
    value = message.text.strip()
    if field == "photo_file_id":
        await message.answer("Отправьте изображение.")
        return
    if field == "price":
        try:
            value = float(value.replace(",", "."))
            if value <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Некорректная цена.")
            return
    if field in ("name", "description") and len(value) < 2:
        await message.answer("Слишком короткое значение.")
        return
    await update_product_field(product_id, field, value)
    await state.clear()
    await message.answer("✅ Товар обновлён.", reply_markup=main_menu_kb(is_admin=True))


@router.callback_query(F.data.startswith("admin:discount:"))
async def admin_discount_menu(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    product_id = int(callback.data.split(":")[-1])
    product = await get_product(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return
    discount = int(product.get("discount_percent") or 0)
    await callback.message.edit_text(
        f"🏷 <b>Скидка на «{product['name']}»</b>\n\n"
        f"Базовая цена: <b>{format_rub(product['price'])}</b>\n"
        f"Текущая скидка: <b>{discount}%</b>",
        reply_markup=admin_discount_kb(product_id, discount),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:set_discount:"))
async def admin_set_discount(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    parts = callback.data.split(":")
    product_id, percent = int(parts[2]), int(parts[3])
    await set_product_discount(product_id, percent)
    product = await get_product(product_id)
    discount = int(product.get("discount_percent") or 0)
    await callback.answer(
        "Скидка снята" if percent == 0 else f"Скидка {percent}%",
        show_alert=True,
    )
    await callback.message.edit_text(
        _product_detail_text(product),
        reply_markup=admin_product_actions_kb(
            product_id,
            bool(product["is_active"]),
            discount,
            bool(product.get("is_seasonal")),
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:custom_discount:"))
async def admin_custom_discount_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    product_id = int(callback.data.split(":")[-1])
    await state.update_data(discount_product_id=product_id)
    await state.set_state(AdminDiscountStates.enter_percent)
    await callback.message.answer("Введите процент скидки (1–99):")
    await callback.answer()


@router.message(AdminDiscountStates.enter_percent)
async def admin_custom_discount_value(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    try:
        percent = int(message.text.strip().replace("%", ""))
        if not 1 <= percent <= 99:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое число от 1 до 99.")
        return
    data = await state.get_data()
    await set_product_discount(data["discount_product_id"], percent)
    await state.clear()
    product = await get_product(data["discount_product_id"])
    await message.answer(
        f"✅ Скидка {percent}% для «{product['name']}».",
        reply_markup=main_menu_kb(is_admin=True),
    )


@router.callback_query(F.data.startswith("admin:toggle:"))
async def admin_toggle_product(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    product_id = int(callback.data.split(":")[-1])
    new_active = await toggle_product_active(product_id)
    status = "показан в каталоге" if new_active else "скрыт"
    await callback.answer(f"Товар {status}", show_alert=True)
    product = await get_product(product_id)
    discount = int(product.get("discount_percent") or 0)
    await callback.message.edit_text(
        _product_detail_text(product),
        reply_markup=admin_product_actions_kb(
            product_id,
            bool(product["is_active"]),
            discount,
            bool(product.get("is_seasonal")),
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:delete:"))
async def admin_delete_product(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    product_id = int(callback.data.split(":")[-1])
    product = await get_product(product_id)
    if product:
        await delete_product(product_id)
    products = await get_all_products()
    await callback.message.edit_text(
        f"🗑 Товар удалён.\n\n" + ADMIN_PRODUCTS_HEADER.format(count=len(products)),
        reply_markup=admin_products_kb(products),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Заказы ────────────────────────────────────────────────────────────────


def _order_detail_text(order_id: int, order: dict, items: list) -> str:
    status = format_order_status(order)
    lines = [
        f"📋 <b>Заказ #{order_id}</b>\n",
        f"👤 {order['name']} | 📞 {order['phone']}",
        f"📍 {order['address']}",
        f"💬 Клиент TG: {format_telegram_client(order.get('username'), html=True)}",
        f"📅 {order['created_at'][:16]}",
        f"Статус: {status}",
    ]
    if order.get("yandex_claim_id"):
        lines.append(
            f"🚕 Яндекс: <code>{order['yandex_claim_id']}</code>\n"
            f"   {format_yandex_status(order.get('yandex_status'))}"
        )
    lines.append("\n<b>Позиции:</b>")
    for item in items:
        lines.append(
            f"• {item['product_name']} — {item['quantity']} × {format_rub(item['price'])}"
        )
    lines.append(f"\n💰 <b>Итого: {format_rub(order['total_amount'])}</b>")
    return "\n".join(lines)


@router.callback_query(F.data == "admin:orders")
async def admin_orders_list(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.clear()
    orders = await get_all_orders(closed_only=False)
    await callback.message.edit_text(
        f"📋 <b>Активные заказы</b> ({len(orders)})",
        reply_markup=admin_orders_kb(orders),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin:orders_closed")
async def admin_orders_closed_list(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.clear()
    orders = await get_all_orders(closed_only=True)
    await callback.message.edit_text(
        f"🔒 <b>Закрытые заказы</b> ({len(orders)})",
        reply_markup=admin_orders_kb(orders),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:order:"))
async def admin_order_detail(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    order_id = int(callback.data.split(":")[-1])
    order = await get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    items = await get_order_items(order_id)
    await callback.message.edit_text(
        _order_detail_text(order_id, order, items),
        reply_markup=admin_order_status_kb(order_id, order),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:order_status:"))
async def admin_change_order_status(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    parts = callback.data.split(":")
    order_id, new_status = int(parts[2]), parts[3]
    order = await get_order(order_id)
    if not order or order["status"] == "closed":
        await callback.answer("Заказ закрыт — изменить нельзя", show_alert=True)
        return
    old_status = order["status"]
    await update_order_status(order_id, new_status)
    if new_status != old_status:
        await notify_customer_status_change(
            bot=callback.bot,
            telegram_id=order["telegram_id"],
            order_id=order_id,
            new_status=new_status,
        )
    order = await get_order(order_id)
    items = await get_order_items(order_id)
    await callback.message.edit_text(
        _order_detail_text(order_id, order, items),
        reply_markup=admin_order_status_kb(order_id, order),
        parse_mode="HTML",
    )
    await callback.answer(f"Статус: {ORDER_STATUSES.get(new_status, new_status)}")


@router.callback_query(F.data.startswith("admin:order_close:"))
async def admin_close_order(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    parts = callback.data.split(":")
    order_id, reason = int(parts[2]), parts[3]
    order = await get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    if order["status"] == "closed":
        await callback.answer("Заказ уже закрыт", show_alert=True)
        return

    await close_order(order_id, reason)
    await notify_customer_order_closed(
        bot=callback.bot,
        telegram_id=order["telegram_id"],
        order_id=order_id,
        reason=reason,
    )

    order = await get_order(order_id)
    items = await get_order_items(order_id)
    label = format_order_status(order)
    await callback.message.edit_text(
        _order_detail_text(order_id, order, items),
        reply_markup=admin_order_status_kb(order_id, order),
        parse_mode="HTML",
    )
    await callback.answer(f"Заказ закрыт: {label}", show_alert=True)


@router.callback_query(F.data.startswith("admin:delete_order:"))
async def admin_delete_order_handler(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    order_id = int(callback.data.split(":")[-1])
    order = await get_order(order_id)
    await delete_order(order_id)
    closed = order and order["status"] == "closed"
    orders = await get_all_orders(closed_only=closed)
    title = "🔒 Закрытые заказы" if closed else "📋 Активные заказы"
    await callback.message.edit_text(
        f"🗑 Заказ #{order_id} удалён.\n\n{title} ({len(orders)})",
        reply_markup=admin_orders_kb(orders),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Биллинг ────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "admin:billing")
async def admin_billing(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.clear()
    stats = await get_billing_stats()
    records = await get_all_billing()
    lines = [
        "💳 <b>Счета и оплата</b>\n",
        "<i>Оплата при получении курьеру. «Оплачен» — после доставки.</i>\n",
        f"✅ Оплачено: <b>{format_rub(stats['paid'])}</b>",
        f"⏳ К оплате: <b>{format_rub(stats['pending'])}</b>",
        f"📊 Всего счетов: <b>{int(stats['total_count'])}</b>\n",
    ]
    for rec in records[:15]:
        status = BILLING_STATUSES.get(rec["status"], rec["status"])
        client = format_telegram_client(rec.get("username"))
        lines.append(
            f"• #{rec['id']} · заказ #{rec['order_id']} · "
            f"{format_rub(rec['amount'])} · {status} · {client}"
        )
    if len(records) > 15:
        lines.append(f"\n<i>…и ещё {len(records) - 15}</i>")

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin:menu")]
            ]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Яндекс Доставка ────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("admin:yandex_link:"))
async def admin_yandex_link_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    order_id = int(callback.data.split(":")[-1])
    await state.update_data(yandex_order_id=order_id)
    await state.set_state(AdminYandexStates.claim_id)
    await callback.message.answer(
        f"🚕 Введите <b>claim_id</b> заявки Яндекс Доставки для заказа #{order_id}:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminYandexStates.claim_id)
async def admin_yandex_link_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    claim_id = message.text.strip()
    if len(claim_id) < 8:
        await message.answer("❌ Некорректный claim_id. Попробуйте снова:")
        return
    data = await state.get_data()
    order_id = data["yandex_order_id"]
    await set_order_yandex_claim(order_id, claim_id)

    client = get_yandex_client()
    yandex_label = "—"
    if client:
        info = await client.get_claim_info(claim_id)
        if info and info.get("status"):
            from database import update_order_yandex

            await update_order_yandex(order_id, info["status"], info.get("updated_ts", ""))
            yandex_label = format_yandex_status(info["status"])

    await state.clear()
    await message.answer(
        f"✅ Заказ #{order_id} привязан к Яндекс: <code>{claim_id}</code>\n"
        f"Статус: {yandex_label}\n\n"
        "<i>Статус будет обновляться автоматически.</i>",
        reply_markup=main_menu_kb(is_admin=True),
        parse_mode="HTML",
    )


# ── Рассылка ────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.set_state(AdminBroadcastStates.message)
    await callback.message.answer(
        "📢 <b>Рассылка</b>\n\nВведите текст сообщения для всех пользователей:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminBroadcastStates.message)
async def admin_broadcast_preview(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    text = message.text.strip()
    if len(text) < 2:
        await message.answer("Слишком короткое сообщение.")
        return
    recipients = await get_all_telegram_ids()
    await state.update_data(broadcast_text=text)
    await state.set_state(AdminBroadcastStates.confirm)
    await message.answer(
        BROADCAST_PREVIEW.format(count=len(recipients), message=text),
        reply_markup=admin_broadcast_confirm_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:broadcast:cancel")
async def admin_broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Рассылка отменена.")
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast:send")
async def admin_broadcast_send(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    import asyncio

    data = await state.get_data()
    text = data.get("broadcast_text", "")
    await state.clear()
    recipients = await get_all_telegram_ids()
    ok, fail = 0, 0
    for tg_id in recipients:
        try:
            await callback.bot.send_message(tg_id, text, parse_mode="HTML")
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)

    await callback.message.edit_text(
        BROADCAST_DONE.format(ok=ok, fail=fail),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Поддержка (админ) ────────────────────────────────────────────────────────


@router.callback_query(F.data == "admin:support")
async def admin_support_list(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.clear()
    threads = await get_open_support_threads()
    await callback.message.edit_text(
        "💬 <b>Поддержка</b>\n\nВыберите диалог для ответа:",
        reply_markup=admin_support_threads_kb(threads),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:support_reply:"))
async def admin_support_reply_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    user_db_id = int(callback.data.split(":")[-1])
    thread = await get_support_thread_by_user(user_db_id)
    if not thread:
        await callback.answer("Диалог не найден", show_alert=True)
        return
    await mark_support_read(thread["id"])
    await state.set_state(AdminSupportStates.reply)
    await state.update_data(
        support_thread_id=thread["id"],
        support_telegram_id=thread["telegram_id"],
    )
    tag = format_telegram_client(thread.get("username"))
    await callback.message.answer(
        f"💬 Ответ клиенту {tag}\n\nВведите сообщение (или /cancel для отмены):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminSupportStates.reply, F.text == "/cancel")
async def admin_support_reply_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Ответ отменён.", reply_markup=main_menu_kb(is_admin=True))


@router.message(AdminSupportStates.reply, F.text)
async def admin_support_reply_send(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    thread_id = data["support_thread_id"]
    telegram_id = data["support_telegram_id"]
    text = message.text.strip()
    await add_support_message(thread_id, "admin", text)
    try:
        await message.bot.send_message(
            telegram_id,
            f"💬 <b>Ответ поддержки:</b>\n\n{text}",
            parse_mode="HTML",
        )
    except Exception:
        await message.answer("❌ Не удалось доставить сообщение клиенту.")
        return
    await message.answer(
        SUPPORT_ADMIN_REPLY_SENT, reply_markup=main_menu_kb(is_admin=True)
    )
    await state.clear()


# ── Главное меню ──────────────────────────────────────────────────────────────


@router.callback_query(F.data == "admin:welcome")
async def admin_welcome_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.clear()
    from utils.welcome import get_welcome_text

    text = await get_welcome_text()
    preview = text if len(text) <= 200 else text[:200] + "…"
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\n"
        "Настройка приветствия при /start и кнопке «На главную».\n\n"
        f"<b>Текущий текст:</b>\n{preview}",
        reply_markup=admin_welcome_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin:welcome_photo")
async def admin_welcome_photo_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.set_state(AdminWelcomeStates.photo)
    await callback.message.answer(
        "🖼 Отправьте <b>новую картинку</b> для главного меню:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminWelcomeStates.photo, F.photo)
async def admin_welcome_photo_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    photo_id = message.photo[-1].file_id
    await set_setting("welcome_photo_file_id", photo_id)
    await state.clear()
    await message.answer(
        "✅ Картинка главного меню обновлена. Проверьте /start",
        reply_markup=main_menu_kb(is_admin=True),
    )


@router.callback_query(F.data == "admin:welcome_text")
async def admin_welcome_text_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    from texts import WELCOME

    await state.set_state(AdminWelcomeStates.text)
    await callback.message.answer(
        "📝 Отправьте <b>новый текст</b> главного меню.\n\n"
        "Поддерживается HTML: <code>&lt;b&gt;</code>, <code>&lt;i&gt;</code>\n\n"
        f"<i>Пример по умолчанию:</i>\n{WELCOME}",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminWelcomeStates.text)
async def admin_welcome_text_save(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    text = message.text.strip()
    if len(text) < 5:
        await message.answer("Текст слишком короткий.")
        return
    await set_setting("welcome_text", text[:2000])
    await state.clear()
    await message.answer(
        "✅ Текст главного меню обновлён. Проверьте /start",
        reply_markup=main_menu_kb(is_admin=True),
    )


@router.message(AdminWelcomeStates.photo)
async def admin_welcome_photo_invalid(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("❌ Отправьте изображение (фото).")


# ── AI описание товара ────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("admin:ai_desc:"))
async def admin_ai_desc_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    product_id = int(callback.data.split(":")[-1])
    await state.update_data(ai_product_id=product_id)
    await state.set_state(AdminAIStates.hint)
    await callback.message.answer(
        "✨ <b>AI-описание</b>\n\n"
        "Введите пожелание для AI (или «-» без дополнений):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminAIStates.hint)
async def admin_ai_desc_generate(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    product_id = data["ai_product_id"]
    product = await get_product(product_id)
    if not product:
        await state.clear()
        await message.answer("Товар не найден.")
        return

    hint = message.text.strip()
    if hint == "-":
        hint = ""

    await message.answer(
        "⏳ Cursor AI дописывает описание…\n"
        "<i>Обычно 30–120 секунд.</i>",
        parse_mode="HTML",
    )
    try:
        new_desc = await enhance_product_description(
            product["name"],
            product["description"],
            product["price"],
            extra_hint=hint,
        )
    except AIError as exc:
        await message.answer(
            f"❌ {exc}",
            reply_markup=main_menu_kb(is_admin=True),
            parse_mode="HTML",
        )
        await state.clear()
        return

    await state.update_data(ai_new_description=new_desc)
    await state.set_state(AdminAIStates.confirm)
    await message.answer(
        f"✨ <b>Новое описание:</b>\n\n{new_desc}",
        reply_markup=admin_ai_confirm_kb(product_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:ai_apply:"))
async def admin_ai_desc_apply(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    product_id = int(callback.data.split(":")[-1])
    data = await state.get_data()
    new_desc = data.get("ai_new_description")
    if not new_desc:
        await callback.answer("Нет текста для сохранения", show_alert=True)
        return
    await update_product_field(product_id, "description", new_desc)
    await state.clear()
    await callback.message.edit_text(
        "✏️ <b>Редактирование товара</b>\n\n"
        "✅ Описание обновлено через AI.\n"
        "Выберите поле:",
        reply_markup=admin_edit_fields_kb(product_id),
        parse_mode="HTML",
    )
    await callback.answer("Описание обновлено")
