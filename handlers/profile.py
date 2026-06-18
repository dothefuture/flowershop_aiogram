"""
Профили доставки — создание, просмотр, редактирование и удаление.
"""

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import (
    create_profile,
    delete_profile,
    get_or_create_user,
    get_profile,
    get_user_profiles,
    update_profile_field,
)
from utils.auth import is_admin
from keyboards.main import main_menu_kb
from keyboards.profile import profile_detail_kb, profile_edit_fields_kb, profiles_menu_kb
from states import ProfileStates
from texts import PROFILE_EMPTY

router = Router(name="profile")

PHONE_PATTERN = re.compile(r"^\+?[\d\s\-\(\)]{7,20}$")


def _profile_text(profile: dict) -> str:
    return (
        f"📋 <b>{profile['title']}</b>\n\n"
        f"👤 Имя: <b>{profile['name']}</b>\n"
        f"📞 Телефон: <b>{profile['phone']}</b>\n"
        f"📍 Адрес: <b>{profile['address']}</b>"
    )


@router.message(F.text == "👤 Профили")
async def show_profiles(message: Message) -> None:
    """Список профилей пользователя."""
    user = await get_or_create_user(message.from_user.id)
    profiles = await get_user_profiles(user["id"])

    if not profiles:
        await message.answer(
            PROFILE_EMPTY,
            reply_markup=profiles_menu_kb([]),
            parse_mode="HTML",
        )
        return

    await message.answer(
        "👤 <b>Ваши профили доставки</b>\n\n"
        "Выберите профиль для просмотра или редактирования:",
        reply_markup=profiles_menu_kb(profiles),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "profile:list")
async def profile_list(callback: CallbackQuery) -> None:
    user = await get_or_create_user(callback.from_user.id)
    profiles = await get_user_profiles(user["id"])
    text = (
        PROFILE_EMPTY
        if not profiles
        else "👤 <b>Ваши профили доставки</b>\n\nВыберите профиль:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=profiles_menu_kb(profiles),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:view:"))
async def profile_view(callback: CallbackQuery) -> None:
    profile_id = int(callback.data.split(":")[-1])
    profile = await get_profile(profile_id)
    if not profile:
        await callback.answer("Профиль не найден", show_alert=True)
        return

    await callback.message.edit_text(
        _profile_text(profile),
        reply_markup=profile_detail_kb(profile_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "profile:add")
async def profile_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileStates.title)
    await callback.message.answer(
        "➕ <b>Новый профиль</b>\n\nВведите <b>название</b> (Дом, Работа…):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ProfileStates.title)
async def profile_add_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if len(title) < 2:
        await message.answer("Название слишком короткое:")
        return
    await state.update_data(title=title)
    await state.set_state(ProfileStates.name)
    await message.answer("Введите <b>имя получателя</b>:", parse_mode="HTML")


@router.message(ProfileStates.name)
async def profile_add_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя слишком короткое:")
        return
    await state.update_data(name=name)
    await state.set_state(ProfileStates.phone)
    await message.answer("Введите <b>телефон</b>:", parse_mode="HTML")


@router.message(ProfileStates.phone)
async def profile_add_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if not PHONE_PATTERN.match(phone):
        await message.answer("Некорректный номер. Пример: +7 900 123-45-67")
        return
    await state.update_data(phone=phone)
    await state.set_state(ProfileStates.address)
    await message.answer("Введите <b>адрес доставки</b>:", parse_mode="HTML")


@router.message(ProfileStates.address)
async def profile_add_address(message: Message, state: FSMContext) -> None:
    address = message.text.strip()
    if len(address) < 5:
        await message.answer("Адрес слишком короткий:")
        return

    data = await state.get_data()
    user = await get_or_create_user(message.from_user.id)
    profile_id = await create_profile(
        user_id=user["id"],
        title=data["title"],
        name=data["name"],
        phone=data["phone"],
        address=address,
    )
    await state.clear()

    profiles = await get_user_profiles(user["id"])
    await message.answer(
        f"✅ Профиль «{data['title']}» создан!",
        reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
    )
    await message.answer(
        "👤 <b>Ваши профили</b>",
        reply_markup=profiles_menu_kb(profiles),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("profile:edit:"))
async def profile_edit_menu(callback: CallbackQuery) -> None:
    profile_id = int(callback.data.split(":")[-1])
    await callback.message.edit_text(
        "✏️ <b>Редактирование профиля</b>\n\nВыберите поле:",
        reply_markup=profile_edit_fields_kb(profile_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:edit_field:"))
async def profile_edit_field_select(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    profile_id = int(parts[2])
    field = parts[3]
    labels = {
        "title": "название профиля",
        "name": "имя",
        "phone": "телефон",
        "address": "адрес",
    }
    await state.update_data(edit_profile_id=profile_id, edit_field=field)
    await state.set_state(ProfileStates.edit_value)
    await callback.message.answer(f"Введите новое значение — {labels[field]}:")
    await callback.answer()


@router.message(ProfileStates.edit_value)
async def profile_edit_value(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    profile_id = data["edit_profile_id"]
    field = data["edit_field"]
    value = message.text.strip()

    if field == "phone" and not PHONE_PATTERN.match(value):
        await message.answer("Некорректный номер.")
        return
    if field in ("title", "name") and len(value) < 2:
        await message.answer("Слишком короткое значение.")
        return
    if field == "address" and len(value) < 5:
        await message.answer("Адрес слишком короткий.")
        return

    await update_profile_field(profile_id, field, value)
    await state.clear()
    profile = await get_profile(profile_id)
    await message.answer(
        "✅ Профиль обновлён.",
        reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
    )
    if profile:
        await message.answer(
            _profile_text(profile),
            reply_markup=profile_detail_kb(profile_id),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("profile:delete:"))
async def profile_delete(callback: CallbackQuery) -> None:
    profile_id = int(callback.data.split(":")[-1])
    profile = await get_profile(profile_id)
    if profile:
        await delete_profile(profile_id)

    user = await get_or_create_user(callback.from_user.id)
    profiles = await get_user_profiles(user["id"])
    await callback.message.edit_text(
        f"🗑 Профиль «{profile['title'] if profile else profile_id}» удалён.\n\n"
        + ("👤 <b>Ваши профили</b>" if profiles else PROFILE_EMPTY),
        reply_markup=profiles_menu_kb(profiles),
        parse_mode="HTML",
    )
    await callback.answer()
