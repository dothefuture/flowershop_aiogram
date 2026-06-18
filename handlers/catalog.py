"""
Каталог товаров с пагинацией, скидками, сезонным разделом.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from cart_storage import add_to_cart
from database import get_active_products, get_product, get_seasonal_settings
from keyboards.catalog import product_card_kb
from keyboards.main import main_menu_kb
from texts import CATALOG_EMPTY
from utils.auth import is_admin
from utils.pricing import format_price_line

router = Router(name="catalog")

PLACEHOLDER_PHOTO = "https://picsum.photos/seed/flower/600/400"


def _product_caption(product: dict, *, seasonal_title: str = "") -> str:
    discount = int(product.get("discount_percent") or 0)
    price_line = format_price_line(product["price"], discount)
    badge = " 🔥 <b>Акция!</b>" if discount > 0 else ""
    seasonal_badge = ""
    if product.get("is_seasonal") and seasonal_title:
        seasonal_badge = f"\n🍂 <b>{seasonal_title}</b>"
    return (
        f"<b>{product['name']}</b>{badge}{seasonal_badge}\n\n"
        f"{product['description']}\n\n"
        f"{price_line}"
    )


async def _send_product_page(message: Message, products: list[dict], page: int) -> None:
    settings = await get_seasonal_settings()
    seasonal_title = settings["title"] if settings["enabled"] == "1" else ""
    product = products[page]
    photo = product["photo_file_id"] or PLACEHOLDER_PHOTO
    await message.answer_photo(
        photo=photo,
        caption=_product_caption(product, seasonal_title=seasonal_title),
        reply_markup=product_card_kb(product["id"], page, len(products)),
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
    await _send_product_page(message, products, 0)


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

    settings = await get_seasonal_settings()
    seasonal_title = settings["title"] if settings["enabled"] == "1" else ""
    product = products[page]
    photo = product["photo_file_id"] or PLACEHOLDER_PHOTO
    caption = _product_caption(product, seasonal_title=seasonal_title)
    kb = product_card_kb(product["id"], page, len(products))

    try:
        await callback.message.edit_media(
            InputMediaPhoto(media=photo, caption=caption, parse_mode="HTML"),
            reply_markup=kb,
        )
    except Exception:
        await callback.message.edit_caption(
            caption=caption, reply_markup=kb, parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("catalog:order:"))
async def add_product_to_cart(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[-1])
    product = await get_product(product_id)
    if not product or not product["is_active"]:
        await callback.answer("Товар недоступен", show_alert=True)
        return
    add_to_cart(callback.from_user.id, product_id)
    await callback.answer(f"🌸 «{product['name']}» добавлен в корзину!")
