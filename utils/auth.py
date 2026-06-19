"""Проверка прав администратора и начисления баланса."""

import os

from config import load_config

_admin_ids: frozenset[int] | None = None


def get_admin_ids() -> frozenset[int]:
    global _admin_ids
    if _admin_ids is None:
        _admin_ids = frozenset(load_config().admin_ids)
    return _admin_ids


def is_admin(user_id: int) -> bool:
    return user_id in get_admin_ids()


def can_credit_balance(user_id: int) -> bool:
    """Кто может начислять баланс: BALANCE_ADMIN_IDS или все ADMIN_IDS."""
    raw = os.getenv("BALANCE_ADMIN_IDS", "").strip()
    if raw:
        allowed = {
            int(part.strip())
            for part in raw.split(",")
            if part.strip().isdigit()
        }
        return user_id in allowed
    return is_admin(user_id)
