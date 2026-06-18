"""Клавиатуры бота."""

from keyboards.main import main_menu_kb
from keyboards.catalog import product_card_kb
from keyboards.cart import cart_kb, confirm_order_kb, cancel_fsm_kb
from keyboards.admin import (
    admin_menu_kb,
    admin_products_kb,
    admin_product_actions_kb,
    admin_edit_fields_kb,
    admin_orders_kb,
    admin_order_status_kb,
)

__all__ = [
    "main_menu_kb",
    "product_card_kb",
    "cart_kb",
    "confirm_order_kb",
    "cancel_fsm_kb",
    "admin_menu_kb",
    "admin_products_kb",
    "admin_product_actions_kb",
    "admin_edit_fields_kb",
    "admin_orders_kb",
    "admin_order_status_kb",
]
