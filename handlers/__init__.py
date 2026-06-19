"""
Регистрация всех роутеров обработчиков.
"""

from handlers.admin import router as admin_router
from handlers.admin_balance import router as admin_balance_router
from handlers.cart import router as cart_router
from handlers.catalog import router as catalog_router
from handlers.order import router as order_router
from handlers.profile import router as profile_router
from handlers.start import router as start_router
from handlers.support import router as support_router


def register_handlers(dp) -> None:
    """Подключает роутеры к диспетчеру в нужном порядке."""
    dp.include_router(start_router)
    dp.include_router(support_router)
    dp.include_router(catalog_router)
    dp.include_router(cart_router)
    dp.include_router(order_router)
    dp.include_router(profile_router)
    dp.include_router(admin_balance_router)
    dp.include_router(admin_router)
