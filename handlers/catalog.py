"""
Каталог товаров — добавление в корзину, количество, пагинация.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from cart_storage import add_to_cart, get_cart_quantity, set_cart_quantity
from database import get_active_products, get_product, get_seasonal_settings
from keyboards.catalog import product_card_kb
from keyboards.main import main_menu_kb
from texts import CATALOG_EMPTY
from utils.auth import is_admin
from utils.pricing import format_price_line

router = Router(name="catalog")

PLACEHOLDER_PHOTO = "https://picsum.photos/seed/flower/600/400"


def _product_caption(
    product: dict,
    *,
    seasonal_title: str = "",
    seasonal_emoji: str = "🍂",
    qty: int = 0,
) -> str:
    discount = int(product.get("discount_percent") or 0)
    price_line = format_price_line(product["price"], discount)
    badge = " 🔥 <b>Акция!</b>" if discount > 0 else ""
    seasonal_badge = ""
    if product.get("is_seasonal") and seasonal_title:
        seasonal_badge = f"\n{seasonal_emoji} <b>{seasonal_title}</b>"

    if qty:
        cart_line = f"\n\n🛒 <b>В корзине: {qty} шт.</b>"
    else:
        cart_line = ""

    return (
        f"<b>{product['name']}</b>{badge}{seasonal_badge}\n\n"
        f"{product['description']}\n\n"
        f"{price_line}{cart_line}"
    )


async def _render_product_card(
    message: Message,
    products: list[dict],
    page: int,
    user_id: int,
    *,
    edit: bool = False,
) -> None:
    settings = await get_seasonal_settings()
    seasonal_title = settings["title"] if settings["enabled"] == "1" else ""
    seasonal_emoji = settings.get("emoji", "🍂")
    product = products[page]
    qty = get_cart_quantity(user_id, product["id"])
    photo = product["photo_file_id"] or PLACEHOLDER_PHOTO
    caption = _product_caption(
        product,
        seasonal_title=seasonal_title,
        seasonal_emoji=seasonal_emoji,
        qty=qty,
    )
    kb = product_card_kb(product["id"], page, len(products), qty)

    if edit:
        try:
            await message.edit_media(
                InputMediaPhoto(media=photo, caption=caption, parse_mode="HTML"),
                reply_markup=kb,
            )
            return
        except Exception:
            try:
                await message.edit_caption(
                    caption=caption, reply_markup=kb, parse_mode="HTML"
                )
                return
            except Exception:
                pass

    await message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.message(F.text == "🌷 Каталог")
async def show_catalog(message: Message) -> None:
    products = await get_active_products()
    if not products:
        await message.answer(
            CATALOG_EMPTY,
            reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
            parse_mode="HTML",
        )
        return
    await _render_product_card(message, products, 0, message.from_user.id)


@router.callback_query(F.data == "catalog:noop")
async def catalog_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("catalog:page:"))
async def catalog_pagination(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":")[-1])
    products = await get_active_products()
    if not products or page < 0 or page >= len(products):
        await callback.answer("Страница не найдена", show_alert=True)
        return

    await _render_product_card(
        callback.message,
        products,
        page,
        callback.from_user.id,
        edit=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("catalog:add:"))
async def catalog_add_to_cart(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[-1])
    product = await get_product(product_id)
    if not product or not product["is_active"]:
        await callback.answer("Товар недоступен", show_alert=True)
        return

    add_to_cart(callback.from_user.id, product_id, 1)
    products = await get_active_products()
    page = next((i for i, p in enumerate(products) if p["id"] == product_id), 0)
    await _render_product_card(
        callback.message,
        products,
        page,
        callback.from_user.id,
        edit=True,
    )
    await callback.answer(f"🛒 «{product['name']}» в корзине")


@router.callback_query(F.data.startswith("catalog:qty:"))
async def catalog_change_qty(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    product_id = int(parts[2])
    action = parts[3]

    product = await get_product(product_id)
    if not product or not product["is_active"]:
        await callback.answer("Товар недоступен", show_alert=True)
        return

    qty = get_cart_quantity(callback.from_user.id, product_id)
    if action == "inc":
        qty += 1
    elif action == "dec":
        qty -= 1

    set_cart_quantity(callback.from_user.id, product_id, qty)

    products = await get_active_products()
    page = next((i for i, p in enumerate(products) if p["id"] == product_id), 0)
    await _render_product_card(
        callback.message,
        products,
        page,
        callback.from_user.id,
        edit=True,
    )

    if qty:
        await callback.answer(f"🛒 В корзине: {qty} шт.")
    else:
        await callback.answer("Убрано из корзины")


@router.callback_query(F.data == "catalog:cart")
async def catalog_open_cart(callback: CallbackQuery) -> None:
    from handlers.cart import _show_cart

    await _show_cart(callback.message, callback.from_user.id)
    await callback.answer()
