"""Проверка прав администратора."""

from config import load_config

_admin_ids: frozenset[int] | None = None


def get_admin_ids() -> frozenset[int]:
    global _admin_ids
    if _admin_ids is None:
        _admin_ids = frozenset(load_config().admin_ids)
    return _admin_ids


def is_admin(user_id: int) -> bool:
    return user_id in get_admin_ids()
