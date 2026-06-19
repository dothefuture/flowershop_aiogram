"""
Профиль: баланс, профили доставки, заказы.
"""

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import (
    create_balance_topup,
    create_profile,
    delete_profile,
    format_order_status,
    get_or_create_user,
    get_profile,
    get_user_balance,
    get_user_orders,
    get_user_profiles,
    set_user_default_profile,
    update_profile_field,
    update_topup_payment,
)
from keyboards.main import main_menu_kb
from keyboards.payment import payment_kb, topup_amount_kb, topup_custom_kb
from keyboards.profile import (
    orders_empty_kb,
    profile_detail_kb,
    profile_edit_fields_kb,
    profiles_empty_kb,
    profiles_menu_kb,
    profile_back_kb,
)
from services.yandex_delivery import format_yandex_status
from services.lava import create_payment_invoice
from states import ProfileStates
from texts import BTN_EXIT, ORDERS_EMPTY, TOPUP_CUSTOM, TOPUP_SELECT
from utils.auth import is_admin
from utils.callback_ui import show_subpage
from utils.pricing import format_rub
from utils.telegram_profile import (
    profile_detail_text,
    profiles_list_text,
    send_profile_hub,
)
from utils.ui_format import frame_block, frame_close, frame_line, frame_open
from utils.welcome import send_main_menu

router = Router(name="profile")

PHONE_PATTERN = re.compile(r"^\+?[\d\s\-\(\)]{7,20}$")


async def _default_profile(user: dict) -> dict | None:
    pid = user.get("default_profile_id")
    if not pid:
        return None
    profile = await get_profile(pid)
    if profile and profile["user_id"] == user["id"]:
        return profile
    return None


def _orders_text(active: list, closed: list) -> str:
    lines: list[str] = []
    if active:
        lines.append("<b>🌿 Активные</b>")
        for order in active:
            lines.extend(
                [
                    frame_line(f"#{order['id']} · {order['created_at'][:10]}"),
                    frame_line(
                        f"{format_rub(order['total_amount'])} · "
                        f"{format_order_status(order)}"
                    ),
                ]
            )
            if order.get("yandex_status"):
                lines.append(
                    frame_line(
                        "🚕 " + format_yandex_status(order["yandex_status"])
                    )
                )
            lines.append("")
    if closed:
        lines.append("<b>🍂 Закрытые</b>")
        for order in closed:
            lines.extend(
                [
                    frame_line(f"#{order['id']} · {order['created_at'][:10]}"),
                    frame_line(
                        f"{format_rub(order['total_amount'])} · "
                        f"{format_order_status(order)}"
                    ),
                    "",
                ]
            )
    body = "\n".join(line for line in lines if line is not None)
    return (
        frame_open("История заказов", emoji="📖")
        + "\n\n"
        + body
        + "\n"
        + frame_close()
    )


@router.message(F.text == "💳 Счета")
@router.message(F.text == "💳 Биллинг")
@router.message(F.text == "📖 История заказов")
async def legacy_menu_redirect(message: Message) -> None:
    await show_profile_hub(message)


@router.message(F.text == "👤 Профиль")
@router.message(F.text == "👤 Профили")
async def show_profile_hub(message: Message) -> None:
    user = await get_or_create_user(
        message.from_user.id, username=message.from_user.username
    )
    balance = await get_user_balance(user["id"])
    default = await _default_profile(user)
    await send_profile_hub(
        message, message.from_user, balance, default_profile=default
    )


@router.callback_query(F.data == "profile:hub")
async def profile_hub(callback: CallbackQuery) -> None:
    user = await get_or_create_user(callback.from_user.id)
    balance = await get_user_balance(user["id"])
    default = await _default_profile(user)
    await send_profile_hub(
        callback.message,
        callback.from_user,
        balance,
        default_profile=default,
        edit=True,
    )
    await callback.answer()


@router.callback_query(F.data == "profile:home")
async def profile_go_home(callback: CallbackQuery) -> None:
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await send_main_menu(callback.message, user=callback.from_user)
    await callback.answer()


@router.callback_query(F.data == "profile:cart")
async def profile_go_cart(callback: CallbackQuery) -> None:
    from handlers.cart import _show_cart

    await _show_cart(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "profile:profiles")
@router.callback_query(F.data == "profile:addresses")
async def profile_profiles(callback: CallbackQuery) -> None:
    user = await get_or_create_user(callback.from_user.id)
    profiles = await get_user_profiles(user["id"])
    default_id = user.get("default_profile_id")
    text = profiles_list_text(has_profiles=bool(profiles))
    kb = (
        profiles_menu_kb(profiles, default_id)
        if profiles
        else profiles_empty_kb()
    )
    await show_subpage(callback, text, kb)
    await callback.answer()


@router.callback_query(F.data == "profile:orders")
async def profile_orders(callback: CallbackQuery) -> None:
    user = await get_or_create_user(callback.from_user.id)
    active = await get_user_orders(user["id"], closed_only=False)
    closed = await get_user_orders(user["id"], closed_only=True)
    if not active and not closed:
        await show_subpage(callback, ORDERS_EMPTY, orders_empty_kb())
    else:
        await show_subpage(callback, _orders_text(active, closed), profile_back_kb())
    await callback.answer()


@router.callback_query(F.data == "profile:list")
async def profile_list(callback: CallbackQuery) -> None:
    await profile_profiles(callback)


@router.callback_query(F.data.startswith("profile:default:"))
async def profile_set_default(callback: CallbackQuery) -> None:
    profile_id = int(callback.data.split(":")[-1])
    profile = await get_profile(profile_id)
    if not profile:
        await callback.answer("Профиль не найден", show_alert=True)
        return
    user = await get_or_create_user(callback.from_user.id)
    if profile["user_id"] != user["id"]:
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await set_user_default_profile(user["id"], profile_id)
    await show_subpage(
        callback,
        profile_detail_text(profile, is_default=True),
        profile_detail_kb(profile_id, is_default=True),
    )
    await callback.answer("⭐ Основной профиль для заказов")


@router.callback_query(F.data.startswith("profile:view:"))
async def profile_view(callback: CallbackQuery) -> None:
    profile_id = int(callback.data.split(":")[-1])
    profile = await get_profile(profile_id)
    if not profile:
        await callback.answer("Профиль не найден", show_alert=True)
        return
    user = await get_or_create_user(callback.from_user.id)
    is_default = profile_id == user.get("default_profile_id")
    await show_subpage(
        callback,
        profile_detail_text(profile, is_default=is_default),
        profile_detail_kb(profile_id, is_default=is_default),
    )
    await callback.answer()


@router.callback_query(F.data == "profile:add")
async def profile_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileStates.title)
    await callback.message.answer(
        frame_block(
            "Новый профиль",
            ["Введите <b>название</b>", "<i>Дом, Работа, Мама…</i>"],
            emoji="➕",
        ),
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
    user = await get_or_create_user(message.from_user.id)
    await message.answer(
        f"✅ Профиль «{data['title']}» создан!",
        reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
    )
    await message.answer(
        profiles_list_text(has_profiles=True),
        reply_markup=profiles_menu_kb(profiles, user.get("default_profile_id")),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("profile:edit:"))
async def profile_edit_menu(callback: CallbackQuery) -> None:
    profile_id = int(callback.data.split(":")[-1])
    await show_subpage(
        callback,
        frame_block("Редактирование", ["Выберите поле для изменения"], emoji="✏️"),
        profile_edit_fields_kb(profile_id),
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
    user = await get_or_create_user(message.from_user.id)
    is_default = profile_id == user.get("default_profile_id")
    await message.answer(
        "✅ Профиль обновлён.",
        reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
    )
    if profile:
        await message.answer(
            profile_detail_text(profile, is_default=is_default),
            reply_markup=profile_detail_kb(profile_id, is_default=is_default),
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
    text = profiles_list_text(has_profiles=bool(profiles))
    kb = (
        profiles_menu_kb(profiles, user.get("default_profile_id"))
        if profiles
        else profiles_empty_kb()
    )
    await show_subpage(
        callback,
        "🗑 Профиль удалён.\n\n" + text,
        kb,
    )
    await callback.answer()


# ── Пополнение баланса ────────────────────────────────────────────────────────


async def _create_topup_invoice(
    message: Message, user_db_id: int, amount: float
) -> bool:
    if amount < 100:
        await message.answer(
            f"Минимальная сумма — 100 ₽\n"
            f"Введите другую сумму или {BTN_EXIT.lower()}:",
            reply_markup=topup_custom_kb(),
            parse_mode="HTML",
        )
        return False
    if amount > 100_000:
        await message.answer(
            f"Максимальная сумма — 100 000 ₽\n"
            f"Введите другую сумму или {BTN_EXIT.lower()}:",
            reply_markup=topup_custom_kb(),
            parse_mode="HTML",
        )
        return False

    topup_id = await create_balance_topup(user_db_id, amount)
    payment_ref = f"balance-{topup_id}"
    invoice = await create_payment_invoice(
        payment_ref,
        amount,
        comment=f"Пополнение баланса #{topup_id}",
    )

    if invoice and invoice.get("payment_url"):
        await update_topup_payment(
            topup_id,
            lava_invoice_id=invoice.get("invoice_id", ""),
            payment_url=invoice["payment_url"],
        )
        await message.answer(
            f"💰 <b>Пополнение на {format_rub(amount)}</b>\n\n"
            "Нажмите кнопку ниже для оплаты через LAVA.",
            reply_markup=payment_kb(
                invoice["payment_url"], label="💳 Оплатить пополнение"
            ),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "Не удалось создать счёт LAVA. Проверьте настройки или "
            "напишите в 💬 Поддержку.",
            reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
            parse_mode="HTML",
        )
    return True


@router.callback_query(F.data == "profile:topup")
async def profile_topup_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await get_or_create_user(callback.from_user.id)
    balance = await get_user_balance(user["id"])
    text = (
        frame_open("Пополнение баланса", emoji="💰")
        + "\n\n"
        + frame_line(f"На счету: <b>{format_rub(balance)}</b>")
        + "\n\n"
        + frame_line("Выберите сумму:")
        + "\n\n"
        + frame_close()
    )
    await callback.message.answer(
        text,
        reply_markup=topup_amount_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:topup:"))
async def profile_topup_amount(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data.split(":")[-1]
    user = await get_or_create_user(callback.from_user.id)

    if action == "custom":
        await state.set_state(ProfileStates.topup_amount)
        await callback.message.answer(
            TOPUP_CUSTOM,
            reply_markup=topup_custom_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    amount = float(action)
    await _create_topup_invoice(callback.message, user["id"], amount)
    await callback.answer()


@router.callback_query(F.data == "profile:topup:cancel")
async def profile_topup_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await get_or_create_user(callback.from_user.id)
    balance = await get_user_balance(user["id"])
    await callback.message.answer(
        f"Пополнение отменено.\n💰 Баланс: <b>{format_rub(balance)}</b>",
        reply_markup=main_menu_kb(is_admin=is_admin(callback.from_user.id)),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ProfileStates.topup_amount, F.text == BTN_EXIT)
async def profile_topup_exit(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = await get_or_create_user(message.from_user.id)
    balance = await get_user_balance(user["id"])
    await message.answer(
        f"Пополнение отменено.\n💰 Баланс: <b>{format_rub(balance)}</b>",
        reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
        parse_mode="HTML",
    )


@router.message(ProfileStates.topup_amount)
async def profile_topup_custom(message: Message, state: FSMContext) -> None:
    raw = message.text.strip().replace(",", ".").replace(" ", "")
    try:
        amount = float(raw)
    except ValueError:
        await message.answer(
            "Введите число, например: 1500\n"
            f"Или {BTN_EXIT.lower()}:",
            reply_markup=topup_custom_kb(),
        )
        return

    user = await get_or_create_user(message.from_user.id)
    if await _create_topup_invoice(message, user["id"], amount):
        await state.clear()
