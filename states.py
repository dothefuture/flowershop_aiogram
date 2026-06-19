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
    payment = State()


class ProfileStates(StatesGroup):
    """Создание и редактирование профилей доставки."""

    title = State()
    name = State()
    phone = State()
    address = State()
    edit_value = State()
    topup_amount = State()


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
    emoji = State()
    title = State()


class AdminBroadcastStates(StatesGroup):
    """Рассылка сообщения всем пользователям."""

    message = State()
    confirm = State()


class SupportStates(StatesGroup):
    """Чат поддержки пользователя."""

    chatting = State()


class AdminSupportStates(StatesGroup):
    """Ответ пользователю в поддержке."""

    reply = State()


class AdminYandexStates(StatesGroup):
    """Привязка заявки Яндекс Доставки к заказу."""

    claim_id = State()


class AdminWelcomeStates(StatesGroup):
    """Главное меню — картинка и текст."""

    photo = State()
    text = State()


class AdminAIStates(StatesGroup):
    """Дополнение описания товара через AI."""

    hint = State()
    confirm = State()
