"""
Работа с SQLite через aiosqlite.
Инициализация таблиц, CRUD для пользователей, профилей, товаров, заказов и биллинга.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import aiosqlite

DB_PATH = "flower_shop.db"

ORDER_STATUSES = {
    "new": "🆕 Новый",
    "in_progress": "🔄 В работе",
    "closed": "🔒 Закрыт",
}

CLOSED_REASONS = {
    "delivered": "✅ Доставлен",
    "cancelled": "❌ Отменён",
}

ORDER_STATUS_KEYS = list(ORDER_STATUSES.keys())
ACTIVE_ORDER_STATUSES = ("new", "in_progress")
CLOSURE_ACTIONS = ("delivered", "cancelled")

BILLING_STATUSES = {
    "pending": "⏳ К оплате при получении",
    "paid": "✅ Оплачен (заказ доставлен)",
}

DEFAULT_SETTINGS = {
    "seasonal_color": "#FF6B35",
    "seasonal_title": "СЕЗОННОЕ",
    "seasonal_enabled": "1",
}


async def init_db() -> None:
    """Создаёт таблицы при первом запуске и добавляет демо-товары."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                name TEXT,
                phone TEXT,
                address TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT 'Основной',
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                photo_file_id TEXT NOT NULL,
                discount_percent INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_seasonal INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                profile_id INTEGER,
                total_amount REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                closed_reason TEXT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (profile_id) REFERENCES user_profiles(id)
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS billing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                paid_at TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )

        await _migrate_schema(db)
        await _ensure_settings(db)
        await db.commit()

        cursor = await db.execute("SELECT COUNT(*) FROM products")
        row = await cursor.fetchone()
        if row and row[0] == 0:
            now = datetime.now().isoformat()
            demo_products = [
                (
                    "Букет «Нежность»",
                    "Нежный букет из розовых роз и белых хризантем. "
                    "Идеален для романтического подарка.",
                    2500.0,
                    "",
                    15,
                    1,
                    1,
                    now,
                ),
                (
                    "Букет «Солнечный»",
                    "Яркий букет из жёлтых тюльпанов и оранжевых гербер. "
                    "Поднимет настроение!",
                    1800.0,
                    "",
                    0,
                    1,
                    0,
                    now,
                ),
                (
                    "Букет «Классика»",
                    "Классический букет из 25 красных роз в элегантной упаковке.",
                    3200.0,
                    "",
                    10,
                    1,
                    0,
                    now,
                ),
            ]
            await db.executemany(
                """
                INSERT INTO products
                    (name, description, price, photo_file_id,
                     discount_percent, is_active, is_seasonal, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                demo_products,
            )
            await db.commit()


async def _migrate_schema(db: aiosqlite.Connection) -> None:
    """Добавляет новые колонки в существующие таблицы."""
    cursor = await db.execute("PRAGMA table_info(products)")
    product_cols = {row[1] for row in await cursor.fetchall()}
    if "discount_percent" not in product_cols:
        await db.execute(
            "ALTER TABLE products ADD COLUMN discount_percent INTEGER NOT NULL DEFAULT 0"
        )
    if "is_seasonal" not in product_cols:
        await db.execute(
            "ALTER TABLE products ADD COLUMN is_seasonal INTEGER NOT NULL DEFAULT 0"
        )

    cursor = await db.execute("PRAGMA table_info(users)")
    user_cols = {row[1] for row in await cursor.fetchall()}
    if "username" not in user_cols:
        await db.execute("ALTER TABLE users ADD COLUMN username TEXT")

    cursor = await db.execute("PRAGMA table_info(orders)")
    order_cols = {row[1] for row in await cursor.fetchall()}
    if "profile_id" not in order_cols:
        await db.execute("ALTER TABLE orders ADD COLUMN profile_id INTEGER")
    if "closed_reason" not in order_cols:
        await db.execute("ALTER TABLE orders ADD COLUMN closed_reason TEXT")

    # Миграция старых статусов delivered/cancelled → closed
    await db.execute(
        """
        UPDATE orders SET status = 'closed', closed_reason = 'delivered'
        WHERE status = 'delivered'
        """
    )
    await db.execute(
        """
        UPDATE orders SET status = 'closed', closed_reason = 'cancelled'
        WHERE status = 'cancelled'
        """
    )

    # Миграция контактов users → user_profiles
    cursor = await db.execute("SELECT COUNT(*) FROM user_profiles")
    if (await cursor.fetchone())[0] == 0:
        cursor = await db.execute(
            """
            SELECT id, name, phone, address, created_at FROM users
            WHERE name IS NOT NULL AND phone IS NOT NULL AND address IS NOT NULL
            """
        )
        for row in await cursor.fetchall():
            await db.execute(
                """
                INSERT INTO user_profiles (user_id, title, name, phone, address, created_at)
                VALUES (?, 'Основной', ?, ?, ?, ?)
                """,
                (row[0], row[1], row[2], row[3], row[4]),
            )


async def _ensure_settings(db: aiosqlite.Connection) -> None:
    for key, value in DEFAULT_SETTINGS.items():
        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        if not await cursor.fetchone():
            await db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)", (key, value)
            )


# ── Настройки ────────────────────────────────────────────────────────────────


async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await db.commit()


async def get_seasonal_settings() -> dict[str, str]:
    return {
        "color": await get_setting("seasonal_color", DEFAULT_SETTINGS["seasonal_color"]),
        "title": await get_setting("seasonal_title", DEFAULT_SETTINGS["seasonal_title"]),
        "enabled": await get_setting("seasonal_enabled", "1"),
    }


# ── Пользователи ──────────────────────────────────────────────────────────────


async def get_or_create_user(
    telegram_id: int, username: str | None = None
) -> dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        user = await cursor.fetchone()
        if user:
            user_dict = dict(user)
            if username is not None and user_dict.get("username") != username:
                await db.execute(
                    "UPDATE users SET username = ? WHERE telegram_id = ?",
                    (username, telegram_id),
                )
                await db.commit()
                user_dict["username"] = username
            return user_dict

        now = datetime.now().isoformat()
        cursor = await db.execute(
            "INSERT INTO users (telegram_id, username, created_at) VALUES (?, ?, ?)",
            (telegram_id, username, now),
        )
        await db.commit()
        user_id = cursor.lastrowid
        return {
            "id": user_id,
            "telegram_id": telegram_id,
            "username": username,
            "name": None,
            "phone": None,
            "address": None,
            "created_at": now,
        }


async def sync_user_username(telegram_id: int, username: str | None) -> None:
    """Обновляет @username пользователя при каждом входе."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET username = ? WHERE telegram_id = ?",
            (username, telegram_id),
        )
        await db.commit()


async def update_user_contacts(
    telegram_id: int, name: str, phone: str, address: str
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users SET name = ?, phone = ?, address = ?
            WHERE telegram_id = ?
            """,
            (name, phone, address, telegram_id),
        )
        await db.commit()


async def get_user_by_telegram_id(telegram_id: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


# ── Профили ────────────────────────────────────────────────────────────────


async def get_user_profiles(user_id: int) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM user_profiles WHERE user_id = ? ORDER BY id",
            (user_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_profile(profile_id: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM user_profiles WHERE id = ?", (profile_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_profile(
    user_id: int, title: str, name: str, phone: str, address: str
) -> int:
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO user_profiles (user_id, title, name, phone, address, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, title, name, phone, address, now),
        )
        await db.commit()
        return cursor.lastrowid


async def update_profile_field(profile_id: int, field: str, value: Any) -> None:
    allowed = {"title", "name", "phone", "address"}
    if field not in allowed:
        raise ValueError(f"Недопустимое поле: {field}")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE user_profiles SET {field} = ? WHERE id = ?", (value, profile_id)
        )
        await db.commit()


async def delete_profile(profile_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM user_profiles WHERE id = ?", (profile_id,))
        await db.commit()


# ── Товары ────────────────────────────────────────────────────────────────────


async def get_active_products(*, include_seasonal_only: bool = False) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if include_seasonal_only:
            cursor = await db.execute(
                """
                SELECT * FROM products
                WHERE is_active = 1 AND is_seasonal = 1
                ORDER BY id
                """
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM products WHERE is_active = 1 ORDER BY is_seasonal DESC, id"
            )
        return [dict(r) for r in await cursor.fetchall()]


async def get_all_products() -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM products ORDER BY id")
        return [dict(r) for r in await cursor.fetchall()]


async def get_product(product_id: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def add_product(
    name: str,
    description: str,
    price: float,
    photo_file_id: str,
    *,
    is_seasonal: bool = False,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now().isoformat()
        cursor = await db.execute(
            """
            INSERT INTO products
                (name, description, price, photo_file_id,
                 discount_percent, is_active, is_seasonal, created_at)
            VALUES (?, ?, ?, ?, 0, 1, ?, ?)
            """,
            (name, description, price, photo_file_id, int(is_seasonal), now),
        )
        await db.commit()
        return cursor.lastrowid


async def update_product_field(product_id: int, field: str, value: Any) -> None:
    allowed = {
        "name",
        "description",
        "price",
        "photo_file_id",
        "discount_percent",
        "is_seasonal",
    }
    if field not in allowed:
        raise ValueError(f"Недопустимое поле: {field}")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE products SET {field} = ? WHERE id = ?", (value, product_id)
        )
        await db.commit()


async def set_product_discount(product_id: int, discount_percent: int) -> None:
    if not 0 <= discount_percent <= 99:
        raise ValueError("Скидка должна быть от 0 до 99%")
    await update_product_field(product_id, "discount_percent", discount_percent)


async def toggle_product_active(product_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT is_active FROM products WHERE id = ?", (product_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError("Товар не найден")
        new_value = 0 if row[0] else 1
        await db.execute(
            "UPDATE products SET is_active = ? WHERE id = ?", (new_value, product_id)
        )
        await db.commit()
        return bool(new_value)


async def toggle_product_seasonal(product_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT is_seasonal FROM products WHERE id = ?", (product_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError("Товар не найден")
        new_value = 0 if row[0] else 1
        await db.execute(
            "UPDATE products SET is_seasonal = ? WHERE id = ?", (new_value, product_id)
        )
        await db.commit()
        return bool(new_value)


async def delete_product(product_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()


# ── Заказы ────────────────────────────────────────────────────────────────────


async def create_order(
    user_id: int,
    items: list[dict[str, Any]],
    name: str,
    phone: str,
    address: str,
    profile_id: int | None = None,
) -> int:
    total = sum(item["price"] * item["quantity"] for item in items)
    now = datetime.now().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO orders
                (user_id, profile_id, total_amount, status, name, phone, address, created_at)
            VALUES (?, ?, ?, 'new', ?, ?, ?, ?)
            """,
            (user_id, profile_id, total, name, phone, address, now),
        )
        order_id = cursor.lastrowid

        for item in items:
            await db.execute(
                """
                INSERT INTO order_items (order_id, product_id, product_name, price, quantity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item["product_id"],
                    item["product_name"],
                    item["price"],
                    item["quantity"],
                ),
            )

        await db.execute(
            """
            INSERT INTO billing (order_id, user_id, amount, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (order_id, user_id, total, now),
        )
        await db.commit()
        return order_id


def format_order_status(order: dict[str, Any]) -> str:
    if order["status"] == "closed" and order.get("closed_reason"):
        return CLOSED_REASONS.get(order["closed_reason"], order["closed_reason"])
    return ORDER_STATUSES.get(order["status"], order["status"])


async def get_user_orders(user_id: int, *, closed_only: bool = False) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if closed_only:
            cursor = await db.execute(
                """
                SELECT * FROM orders
                WHERE user_id = ? AND status = 'closed'
                ORDER BY id DESC
                """,
                (user_id,),
            )
        else:
            cursor = await db.execute(
                """
                SELECT * FROM orders
                WHERE user_id = ? AND status != 'closed'
                ORDER BY id DESC
                """,
                (user_id,),
            )
        return [dict(r) for r in await cursor.fetchall()]


async def get_all_orders(*, closed_only: bool = False) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if closed_only:
            cursor = await db.execute(
                """
                SELECT o.*, u.telegram_id, u.username
                FROM orders o
                JOIN users u ON o.user_id = u.id
                WHERE o.status = 'closed'
                ORDER BY o.id DESC
                """
            )
        else:
            cursor = await db.execute(
                """
                SELECT o.*, u.telegram_id, u.username
                FROM orders o
                JOIN users u ON o.user_id = u.id
                WHERE o.status != 'closed'
                ORDER BY o.id DESC
                """
            )
        return [dict(r) for r in await cursor.fetchall()]


async def get_order(order_id: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT o.*, u.telegram_id, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.id = ?
            """,
            (order_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_order_items(order_id: int) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def update_order_status(order_id: int, status: str) -> None:
    if status not in ORDER_STATUS_KEYS:
        raise ValueError(f"Недопустимый статус: {status}")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status = ? WHERE id = ?", (status, order_id)
        )
        await db.commit()


async def close_order(order_id: int, reason: str) -> None:
    if reason not in CLOSURE_ACTIONS:
        raise ValueError(f"Недопустимая причина закрытия: {reason}")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE orders SET status = 'closed', closed_reason = ?
            WHERE id = ? AND status != 'closed'
            """,
            (reason, order_id),
        )
        if reason == "delivered":
            now = datetime.now().isoformat()
            await db.execute(
                """
                UPDATE billing SET status = 'paid', paid_at = ?
                WHERE order_id = ?
                """,
                (now, order_id),
            )
        await db.commit()


async def delete_order(order_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM billing WHERE order_id = ?", (order_id,))
        await db.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
        await db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        await db.commit()


# ── Биллинг ────────────────────────────────────────────────────────────────


async def get_user_billing(user_id: int) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT b.*, o.name AS order_name
            FROM billing b
            JOIN orders o ON b.order_id = o.id
            WHERE b.user_id = ?
            ORDER BY b.id DESC
            """,
            (user_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_billing_stats() -> dict[str, float]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM billing WHERE status = 'paid'"
        )
        paid = (await cursor.fetchone())[0]
        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM billing WHERE status = 'pending'"
        )
        pending = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM billing")
        total = (await cursor.fetchone())[0]
        return {"paid": paid, "pending": pending, "total_count": total}


async def get_all_billing() -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT b.*, o.name AS customer_name, u.telegram_id, u.username
            FROM billing b
            JOIN orders o ON b.order_id = o.id
            JOIN users u ON b.user_id = u.id
            ORDER BY b.id DESC
            """
        )
        return [dict(r) for r in await cursor.fetchall()]


async def clear_database() -> None:
    """Удаляет файл БД и создаёт чистую базу с демо-товарами."""
    import os

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    await init_db()
