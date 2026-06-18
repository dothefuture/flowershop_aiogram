"""
FSM-состояния для оформления заказов, профилей и административной панели.
"""

from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    """Многошаговое оформление заказа пользователем."""

    select_profile = State()
    profile_title = State()
    name = State()
    phone = State()
    address = State()
    confirm = State()


class ProfileStates(StatesGroup):
    """Создание и редактирование профилей доставки."""

    title = State()
    name = State()
    phone = State()
    address = State()
    edit_value = State()


class AdminAddProductStates(StatesGroup):
    """Добавление нового товара администратором."""

    name = State()
    description = State()
    price = State()
    photo = State()


class AdminEditProductStates(StatesGroup):
    """Редактирование существующего товара."""

    select_field = State()
    edit_value = State()


class AdminDiscountStates(StatesGroup):
    """Установка или снятие скидки на товар."""

    enter_percent = State()


class AdminSeasonalStates(StatesGroup):
    """Настройка сезонного раздела."""

    color = State()
