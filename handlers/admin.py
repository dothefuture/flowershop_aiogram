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
    close_order,
    delete_order,
    delete_product,
    format_order_status,
    get_all_billing,
    get_all_orders,
    get_all_products,
    get_billing_stats,
    get_order,
    get_order_items,
    get_product,
    get_seasonal_settings,
    set_setting,
    set_product_discount,
    toggle_product_active,
    toggle_product_seasonal,
    update_order_status,
    update_product_field,
)
from utils.auth import is_admin
from keyboards.admin import (
    admin_discount_kb,
    admin_edit_fields_kb,
    admin_menu_kb,
    admin_order_status_kb,
    admin_orders_kb,
    admin_product_actions_kb,
    admin_products_kb,
    admin_seasonal_kb,
)
from keyboards.main import main_menu_kb
from notifications import (
    notify_customer_order_closed,
    notify_customer_status_change,
)
from states import AdminAddProductStates, AdminDiscountStates, AdminEditProductStates, AdminSeasonalStates
from texts import ADMIN_PANEL, ADMIN_PRODUCTS_HEADER
from utils.formatting import format_telegram_client
from utils.pricing import effective_price, format_price_line, format_rub

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


@router.callback_query(F.data == "admin:seasonal")
async def admin_seasonal_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.clear()
    settings = await get_seasonal_settings()
    enabled = settings["enabled"] == "1"
    await callback.message.edit_text(
        f"🍂 <b>Сезонный раздел «{settings['title']}»</b>\n\n"
        f"Статус: {'✅ включён' if enabled else '⛔ выключён'}\n"
        f"Цвет выделения: <code>{settings['color']}</code>",
        reply_markup=admin_seasonal_kb(settings["color"], enabled),
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
        f"🍂 <b>Сезонный раздел «{settings['title']}»</b>\n\n"
        f"Статус: {'✅ включён' if enabled else '⛔ выключён'}\n"
        f"Цвет выделения: <code>{settings['color']}</code>",
        reply_markup=admin_seasonal_kb(settings["color"], enabled),
        parse_mode="HTML",
    )
    await callback.answer("Обновлено")


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


@router.callback_query(F.data.startswith("admin:seasonal_toggle:"))
async def admin_product_seasonal_toggle(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    product_id = int(callback.data.split(":")[-1])
    new_val = await toggle_product_seasonal(product_id)
    msg = "добавлен в сезонное" if new_val else "убран из сезонного"
    await callback.answer(f"Товар {msg}", show_alert=True)
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
        f"Статус: {status}\n",
        "<b>Позиции:</b>",
    ]
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
