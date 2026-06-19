"""
Оформление заказа — профиль, подтверждение, оплата LAVA или балансом.
"""

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from cart_storage import build_cart_details, cart_is_empty, clear_cart
from database import (
    add_user_balance,
    create_order,
    create_profile,
    deduct_user_balance,
    get_billing_by_order,
    get_or_create_user,
    get_profile,
    get_user_balance,
    get_user_profiles,
    mark_billing_paid,
    update_billing_payment,
    update_user_contacts,
)
from keyboards.cart import cancel_fsm_kb, confirm_order_kb, order_payment_kb
from keyboards.main import main_menu_kb
from keyboards.payment import payment_kb
from keyboards.profile import checkout_profile_kb
from services.lava import create_payment_invoice
from services.payment_flow import on_payment_success
from utils.auth import is_admin
from states import OrderStates
from texts import (
    BTN_CANCEL,
    ORDER_CANCELLED,
    ORDER_CONFIRM_HEADER,
    ORDER_PAYMENT_SELECT,
    ORDER_SELECT_PROFILE,
    ORDER_STEP_ADDRESS,
    ORDER_STEP_NAME,
    ORDER_STEP_PHONE,
    ORDER_STEP_PROFILE_TITLE,
    ORDER_SUCCESS_LAVA,
    ORDER_SUCCESS_PAYMENT,
)
from utils.pricing import format_rub
from utils.ui_format import frame_close, frame_line, frame_open

router = Router(name="order")

PHONE_PATTERN = re.compile(r"^\+?[\d\s\-\(\)]{7,20}$")


async def _show_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    items = data["cart_items"]
    total = data["cart_total"]

    lines = [
        ORDER_CONFIRM_HEADER,
        "",
        frame_line(f"📋 {data.get('profile_title', '—')}"),
        frame_line(f"👤 {data['name']}"),
        frame_line(f"📞 {data['phone']}"),
        frame_line(f"📍 {data['address']}"),
        "",
        frame_line("<b>🌸 Состав:</b>"),
    ]
    for item in items:
        lines.append(
            frame_line(
                f"{item['product_name']} — {item['quantity']} шт. × "
                f"{format_rub(item['price'])}"
            )
        )
    lines.extend(
        [
            "",
            frame_line(f"💐 Итого: <b>{format_rub(total)}</b>"),
            "",
            frame_close(),
            "",
            "<i>После подтверждения выберите способ оплаты. "
            "Доставка Яндекс — только после оплаты.</i>",
        ]
    )

    await state.set_state(OrderStates.confirm)
    await message.answer(
        "\n".join(lines),
        reply_markup=confirm_order_kb(),
        parse_mode="HTML",
    )


async def begin_checkout(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id

    if cart_is_empty(user_id):
        await callback.answer("Корзина пуста!", show_alert=True)
        return

    items, total = await build_cart_details(user_id)
    if not items:
        await callback.answer("Нет доступных товаров в корзине", show_alert=True)
        return

    await state.update_data(cart_items=items, cart_total=total)
    user = await get_or_create_user(user_id)
    profiles = await get_user_profiles(user["id"])
    default_id = user.get("default_profile_id")

    if default_id:
        profile = await get_profile(default_id)
        if profile and profile["user_id"] == user["id"]:
            await state.update_data(
                profile_id=profile["id"],
                profile_title=profile["title"],
                name=profile["name"],
                phone=profile["phone"],
                address=profile["address"],
                save_new_profile=False,
            )
            await callback.message.edit_reply_markup(reply_markup=None)
            await _show_confirm(callback.message, state)
            await callback.answer()
            return

    await state.set_state(OrderStates.select_profile)
    await callback.message.answer(
        ORDER_SELECT_PROFILE,
        reply_markup=checkout_profile_kb(profiles, default_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(OrderStates.select_profile, F.data.startswith("order:profile:"))
async def select_checkout_profile(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data.split(":")[-1]

    if action == "cancel":
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            ORDER_CANCELLED,
            reply_markup=main_menu_kb(is_admin=is_admin(callback.from_user.id)),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    if action == "new":
        await state.update_data(profile_id=None, save_new_profile=True)
        await state.set_state(OrderStates.profile_title)
        await callback.message.answer(
            ORDER_STEP_PROFILE_TITLE,
            reply_markup=cancel_fsm_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    profile_id = int(action)
    profile = await get_profile(profile_id)
    if not profile:
        await callback.answer("Профиль не найден", show_alert=True)
        return

    await state.update_data(
        profile_id=profile_id,
        profile_title=profile["title"],
        name=profile["name"],
        phone=profile["phone"],
        address=profile["address"],
        save_new_profile=False,
    )
    await callback.message.edit_reply_markup(reply_markup=None)
    await _show_confirm(callback.message, state)
    await callback.answer()


@router.message(OrderStates.profile_title, F.text == BTN_CANCEL)
@router.message(OrderStates.name, F.text == BTN_CANCEL)
@router.message(OrderStates.phone, F.text == BTN_CANCEL)
@router.message(OrderStates.address, F.text == BTN_CANCEL)
async def cancel_order_fsm(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        ORDER_CANCELLED,
        reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
        parse_mode="HTML",
    )


@router.message(OrderStates.profile_title)
async def process_profile_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if len(title) < 2:
        await message.answer("Название слишком короткое:")
        return
    await state.update_data(profile_title=title)
    await state.set_state(OrderStates.name)
    await message.answer(ORDER_STEP_NAME, parse_mode="HTML")


@router.message(OrderStates.name)
async def process_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Введите корректное имя:")
        return

    await state.update_data(name=name)
    await state.set_state(OrderStates.phone)
    await message.answer(ORDER_STEP_PHONE, parse_mode="HTML")


@router.message(OrderStates.phone)
async def process_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if not PHONE_PATTERN.match(phone):
        await message.answer(
            "Некорректный номер. Введите телефон, например: +7 900 123-45-67"
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(OrderStates.address)
    await message.answer(ORDER_STEP_ADDRESS, parse_mode="HTML")


@router.message(OrderStates.address)
async def process_address(message: Message, state: FSMContext) -> None:
    address = message.text.strip()
    if len(address) < 5:
        await message.answer("Адрес слишком короткий. Укажите полный адрес доставки:")
        return

    await state.update_data(address=address)
    await _show_confirm(message, state)


@router.callback_query(OrderStates.confirm, F.data == "order:cancel")
async def cancel_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        ORDER_CANCELLED,
        reply_markup=main_menu_kb(is_admin=is_admin(callback.from_user.id)),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(OrderStates.confirm, F.data == "order:confirm")
async def confirm_order(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    telegram_id = callback.from_user.id
    user = await get_or_create_user(telegram_id, username=callback.from_user.username)

    profile_id = data.get("profile_id")
    if data.get("save_new_profile"):
        profile_id = await create_profile(
            user_id=user["id"],
            title=data.get("profile_title", "Новый"),
            name=data["name"],
            phone=data["phone"],
            address=data["address"],
        )

    order_id = await create_order(
        user_id=user["id"],
        items=data["cart_items"],
        name=data["name"],
        phone=data["phone"],
        address=data["address"],
        profile_id=profile_id,
    )

    await update_user_contacts(
        telegram_id, data["name"], data["phone"], data["address"]
    )
    clear_cart(telegram_id)

    balance = await get_user_balance(user["id"])
    total = data["cart_total"]

    await state.set_state(OrderStates.payment)
    await state.update_data(pending_order_id=order_id, cart_total=total)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        ORDER_SUCCESS_PAYMENT.format(order_id=order_id)
        + "\n\n"
        + ORDER_PAYMENT_SELECT.format(total=format_rub(total), balance=format_rub(balance)),
        reply_markup=order_payment_kb(order_id, balance, total),
        parse_mode="HTML",
    )
    await callback.answer("Заказ создан!")


@router.callback_query(F.data == "order:pay:balance:low")
async def pay_balance_insufficient(callback: CallbackQuery) -> None:
    await callback.answer(
        "Недостаточно средств. Пополните баланс в 👤 Профиль.",
        show_alert=True,
    )


@router.callback_query(F.data.startswith("order:pay:lava:"))
async def pay_order_lava(callback: CallbackQuery, state: FSMContext) -> None:
    order_id = int(callback.data.split(":")[-1])
    data = await state.get_data()
    total = data.get("cart_total", 0)

    invoice = await create_payment_invoice(
        order_id,
        total,
        comment=f"Заказ #{order_id} — Цветочный рай",
    )

    reply_markup = main_menu_kb(is_admin=is_admin(callback.from_user.id))
    if invoice and invoice.get("payment_url"):
        await update_billing_payment(
            order_id,
            lava_invoice_id=invoice.get("invoice_id", ""),
            payment_url=invoice["payment_url"],
        )
        reply_markup = payment_kb(invoice["payment_url"])
        hint = "Нажмите кнопку ниже для оплаты через LAVA."
    else:
        hint = (
            "Ссылка на оплату временно недоступна. "
            "Напишите в 💬 Поддержку."
        )

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        ORDER_SUCCESS_LAVA.format(order_id=order_id, payment_hint=hint),
        reply_markup=reply_markup,
        parse_mode="HTML",
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("order:pay:balance:"))
async def pay_order_balance(callback: CallbackQuery, state: FSMContext) -> None:
    order_id = int(callback.data.split(":")[-1])
    data = await state.get_data()
    total = float(data.get("cart_total", 0))

    user = await get_or_create_user(
        callback.from_user.id, username=callback.from_user.username
    )

    billing = await get_billing_by_order(order_id)
    if billing and billing["status"] == "paid":
        await callback.answer("Заказ уже оплачен", show_alert=True)
        await state.clear()
        return

    if not await deduct_user_balance(user["id"], total):
        await callback.answer("Недостаточно средств на балансе", show_alert=True)
        return

    if not await mark_billing_paid(order_id, payment_method="balance"):
        await add_user_balance(user["id"], total)
        await callback.answer("Не удалось провести оплату", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"✅ Заказ #{order_id} оплачен с баланса на {format_rub(total)}!",
        reply_markup=main_menu_kb(is_admin=is_admin(callback.from_user.id)),
        parse_mode="HTML",
    )
    await on_payment_success(callback.bot, order_id)
    await state.clear()
    await callback.answer("Оплачено!")
