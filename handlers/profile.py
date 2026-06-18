"""
Профиль: адреса доставки, история заказов и счета.
"""

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import (
    BILLING_STATUSES,
    create_profile,
    delete_profile,
    format_order_status,
    get_or_create_user,
    get_profile,
    get_user_billing,
    get_user_orders,
    get_user_profiles,
    update_profile_field,
)
from keyboards.main import main_menu_kb
from keyboards.profile import (
    profile_back_kb,
    profile_detail_kb,
    profile_edit_fields_kb,
    profile_hub_kb,
    profiles_menu_kb,
)
from services.yandex_delivery import format_yandex_status
from states import ProfileStates
from texts import BILLING_EMPTY, BILLING_HEADER, PROFILE_EMPTY
from utils.auth import is_admin
from utils.pricing import format_rub

router = Router(name="profile")

PHONE_PATTERN = re.compile(r"^\+?[\d\s\-\(\)]{7,20}$")


def _profile_text(profile: dict) -> str:
    return (
        f"📋 <b>{profile['title']}</b>\n\n"
        f"👤 Имя: <b>{profile['name']}</b>\n"
        f"📞 Телефон: <b>{profile['phone']}</b>\n"
        f"📍 Адрес: <b>{profile['address']}</b>"
    )


def _orders_text(active: list, closed: list) -> str:
    if not active and not closed:
        return "📖 <b>История заказов</b>\n\nУ вас пока нет заказов."
    lines = ["📖 <b>История заказов</b>\n"]
    if active:
        lines.append("<b>Активные:</b>")
        for order in active:
            yandex = ""
            if order.get("yandex_status"):
                yandex = f"\n   🚕 {format_yandex_status(order['yandex_status'])}"
            lines.append(
                f"🔹 <b>#{order['id']}</b> · {order['created_at'][:10]}\n"
                f"   💰 {format_rub(order['total_amount'])} · "
                f"{format_order_status(order)}{yandex}\n"
            )
    if closed:
        lines.append("\n<b>🔒 Закрытые:</b>")
        for order in closed:
            lines.append(
                f"🔹 <b>#{order['id']}</b> · {order['created_at'][:10]}\n"
                f"   💰 {format_rub(order['total_amount'])} · "
                f"{format_order_status(order)}\n"
            )
    return "\n".join(lines)


def _billing_text(records: list) -> str:
    if not records:
        return BILLING_EMPTY
    lines = [BILLING_HEADER]
    for rec in records:
        status = BILLING_STATUSES.get(rec["status"], rec["status"])
        date = rec["created_at"][:10]
        paid = (
            f"\n   ✅ Дата оплаты: {rec['paid_at'][:10]}"
            if rec.get("paid_at")
            else ""
        )
        lines.append(
            f"🔹 <b>Счёт #{rec['id']}</b> · заказ #{rec['order_id']}\n"
            f"   💰 {format_rub(rec['amount'])} · {status}\n"
            f"   📅 Создан: {date}{paid}\n"
        )
    return "\n".join(lines)


@router.message(F.text == "💳 Счета")
@router.message(F.text == "💳 Биллинг")
@router.message(F.text == "📖 История заказов")
async def legacy_menu_redirect(message: Message) -> None:
    """Старые кнопки меню → профиль."""
    await show_profile_hub(message)


@router.message(F.text == "👤 Профиль")
@router.message(F.text == "👤 Профили")
async def show_profile_hub(message: Message) -> None:
    await get_or_create_user(message.from_user.id, username=message.from_user.username)
    await message.answer(
        "👤 <b>Личный кабинет</b>\n\nВыберите раздел:",
        reply_markup=profile_hub_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "profile:hub")
async def profile_hub(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "👤 <b>Личный кабинет</b>\n\nВыберите раздел:",
        reply_markup=profile_hub_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "profile:addresses")
async def profile_addresses(callback: CallbackQuery) -> None:
    user = await get_or_create_user(callback.from_user.id)
    profiles = await get_user_profiles(user["id"])
    text = (
        PROFILE_EMPTY
        if not profiles
        else "📋 <b>Адреса доставки</b>\n\nВыберите профиль:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=profiles_menu_kb(profiles),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "profile:orders")
async def profile_orders(callback: CallbackQuery) -> None:
    user = await get_or_create_user(callback.from_user.id)
    active = await get_user_orders(user["id"], closed_only=False)
    closed = await get_user_orders(user["id"], closed_only=True)
    await callback.message.edit_text(
        _orders_text(active, closed),
        reply_markup=profile_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "profile:billing")
async def profile_billing(callback: CallbackQuery) -> None:
    user = await get_or_create_user(callback.from_user.id)
    records = await get_user_billing(user["id"])
    await callback.message.edit_text(
        _billing_text(records),
        reply_markup=profile_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "profile:list")
async def profile_list(callback: CallbackQuery) -> None:
    await profile_addresses(callback)


@router.callback_query(F.data.startswith("profile:view:"))
async def profile_view(callback: CallbackQuery) -> None:
    profile_id = int(callback.data.split(":")[-1])
    profile = await get_profile(profile_id)
    if not profile:
        await callback.answer("Профиль не найден", show_alert=True)
        return
    await callback.message.edit_text(
        _profile_text(profile),
        reply_markup=profile_detail_kb(profile_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "profile:add")
async def profile_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileStates.title)
    await callback.message.answer(
        "➕ <b>Новый профиль</b>\n\nВведите <b>название</b> (Дом, Работа…):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ProfileStates.title)
async def profile_add_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if len(title) < 2:
        await message.answer("Название слишком короткое:")
        return
    await state.update_data(title=title)
    await state.set_state(ProfileStates.name)
    await message.answer("Введите <b>имя получателя</b>:", parse_mode="HTML")


@router.message(ProfileStates.name)
async def profile_add_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя слишком короткое:")
        return
    await state.update_data(name=name)
    await state.set_state(ProfileStates.phone)
    await message.answer("Введите <b>телефон</b>:", parse_mode="HTML")


@router.message(ProfileStates.phone)
async def profile_add_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if not PHONE_PATTERN.match(phone):
        await message.answer("Некорректный номер. Пример: +7 900 123-45-67")
        return
    await state.update_data(phone=phone)
    await state.set_state(ProfileStates.address)
    await message.answer("Введите <b>адрес доставки</b>:", parse_mode="HTML")


@router.message(ProfileStates.address)
async def profile_add_address(message: Message, state: FSMContext) -> None:
    address = message.text.strip()
    if len(address) < 5:
        await message.answer("Адрес слишком короткий:")
        return
    data = await state.get_data()
    user = await get_or_create_user(message.from_user.id)
    await create_profile(
        user_id=user["id"],
        title=data["title"],
        name=data["name"],
        phone=data["phone"],
        address=address,
    )
    await state.clear()
    profiles = await get_user_profiles(user["id"])
    await message.answer(
        f"✅ Профиль «{data['title']}» создан!",
        reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
    )
    await message.answer(
        "📋 <b>Адреса доставки</b>",
        reply_markup=profiles_menu_kb(profiles),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("profile:edit:"))
async def profile_edit_menu(callback: CallbackQuery) -> None:
    profile_id = int(callback.data.split(":")[-1])
    await callback.message.edit_text(
        "✏️ <b>Редактирование профиля</b>\n\nВыберите поле:",
        reply_markup=profile_edit_fields_kb(profile_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:edit_field:"))
async def profile_edit_field_select(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    profile_id, field = int(parts[2]), parts[3]
    labels = {
        "title": "название профиля",
        "name": "имя",
        "phone": "телефон",
        "address": "адрес",
    }
    await state.update_data(edit_profile_id=profile_id, edit_field=field)
    await state.set_state(ProfileStates.edit_value)
    await callback.message.answer(f"Введите новое значение — {labels[field]}:")
    await callback.answer()


@router.message(ProfileStates.edit_value)
async def profile_edit_value(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    profile_id, field = data["edit_profile_id"], data["edit_field"]
    value = message.text.strip()
    if field == "phone" and not PHONE_PATTERN.match(value):
        await message.answer("Некорректный номер.")
        return
    if field in ("title", "name") and len(value) < 2:
        await message.answer("Слишком короткое значение.")
        return
    if field == "address" and len(value) < 5:
        await message.answer("Адрес слишком короткий.")
        return
    await update_profile_field(profile_id, field, value)
    await state.clear()
    profile = await get_profile(profile_id)
    await message.answer(
        "✅ Профиль обновлён.",
        reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
    )
    if profile:
        await message.answer(
            _profile_text(profile),
            reply_markup=profile_detail_kb(profile_id),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("profile:delete:"))
async def profile_delete(callback: CallbackQuery) -> None:
    profile_id = int(callback.data.split(":")[-1])
    profile = await get_profile(profile_id)
    if profile:
        await delete_profile(profile_id)
    user = await get_or_create_user(callback.from_user.id)
    profiles = await get_user_profiles(user["id"])
    await callback.message.edit_text(
        f"🗑 Профиль удалён.\n\n"
        + ("📋 <b>Адреса доставки</b>" if profiles else PROFILE_EMPTY),
        reply_markup=profiles_menu_kb(profiles),
        parse_mode="HTML",
    )
    await callback.answer()
