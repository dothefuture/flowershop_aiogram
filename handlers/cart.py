"""Корзина — просмотр, количество и оформление."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from cart_storage import (
    add_to_cart,
    build_cart_details,
    clear_cart,
    get_cart,
    remove_from_cart,
)
from keyboards.cart import cart_kb
from texts import CART_EMPTY
from utils.pricing import format_price_short, format_rub
from utils.ui_format import frame_close, frame_line, frame_open

router = Router(name="cart")


def _format_cart_text(items: list[dict], total: float) -> str:
    if not items:
        return CART_EMPTY

    count = sum(item["quantity"] for item in items)
    lines = [frame_open("Корзина", emoji="🛒"), ""]

    for i, item in enumerate(items, 1):
        discount = item.get("discount_percent", 0)
        if discount > 0:
            price_str = format_price_short(item["original_price"], discount)
        else:
            price_str = format_rub(item["price"])

        lines.extend(
            [
                frame_line(f"🌸 <b>{i}. {item['product_name']}</b>"),
                frame_line(f"{item['quantity']} шт. × {price_str}"),
                frame_line(f"💰 {format_rub(item['subtotal'])}"),
                "",
            ]
        )

    lines.extend(
        [
            frame_line(f"📦 Позиций: <b>{count}</b>"),
            frame_line(f"💐 Итого: <b>{format_rub(total)}</b>"),
            "",
            frame_close(),
        ]
    )
    return "\n".join(lines)


async def _show_cart(message: Message, user_id: int, *, edit: bool = False) -> None:
    items, total = await build_cart_details(user_id)
    text = _format_cart_text(items, total)
    kb = cart_kb(items)

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            return
        except Exception:
            pass

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(F.text == "🛒 Корзина")
async def show_cart(message: Message) -> None:
    await _show_cart(message, message.from_user.id)


@router.callback_query(F.data == "cart:noop")
async def cart_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("cart:inc:"))
async def cart_increase(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[-1])
    add_to_cart(callback.from_user.id, product_id)
    await _show_cart(callback.message, callback.from_user.id, edit=True)
    await callback.answer("➕")


@router.callback_query(F.data.startswith("cart:dec:"))
async def cart_decrease(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[-1])
    cart = get_cart(callback.from_user.id)
    if product_id in cart:
        cart[product_id] -= 1
        if cart[product_id] <= 0:
            remove_from_cart(callback.from_user.id, product_id)
    await _show_cart(callback.message, callback.from_user.id, edit=True)
    await callback.answer("➖")


@router.callback_query(F.data == "cart:clear")
async def cart_clear_all(callback: CallbackQuery) -> None:
    clear_cart(callback.from_user.id)
    await _show_cart(callback.message, callback.from_user.id, edit=True)
    await callback.answer("Корзина очищена")


@router.callback_query(F.data == "cart:checkout")
async def start_checkout(callback: CallbackQuery, state) -> None:
    from handlers.order import begin_checkout

    await begin_checkout(callback, state)
