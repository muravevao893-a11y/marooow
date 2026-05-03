from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from app.config import get_settings
from app.db.session import session_scope
from app.keyboards import profile_rules_kb, user_home_kb
from app.services.user_service import get_user_by_tg, register_user
from app.texts import profile_text, rules_text, start_text

router = Router(name="user")
settings = get_settings()


@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject) -> None:
    async with session_scope() as session:
        user = await register_user(session, message.from_user)
        text_arg = (command.args or "").strip()
        if text_arg == "rules":
            await message.answer(rules_text(), reply_markup=profile_rules_kb(), parse_mode="HTML")
            return
        if text_arg == "profile":
            await message.answer(
                profile_text(user.telegram_id, user.username, user.first_name, user.entries_count, user.wins_count, user.is_banned),
                reply_markup=profile_rules_kb(),
                parse_mode="HTML",
            )
            return
        await message.answer(
            start_text(user.first_name, user.entries_count, user.wins_count),
            reply_markup=user_home_kb(settings.bot_username),
            parse_mode="HTML",
        )


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    async with session_scope() as session:
        user = await register_user(session, message.from_user)
        await message.answer(
            profile_text(user.telegram_id, user.username, user.first_name, user.entries_count, user.wins_count, user.is_banned),
            reply_markup=profile_rules_kb(),
            parse_mode="HTML",
        )


@router.message(Command("rules"))
async def cmd_rules(message: Message) -> None:
    await message.answer(rules_text(), reply_markup=profile_rules_kb(), parse_mode="HTML")


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery) -> None:
    async with session_scope() as session:
        user = await register_user(session, callback.from_user)
        await callback.message.answer(
            profile_text(user.telegram_id, user.username, user.first_name, user.entries_count, user.wins_count, user.is_banned),
            reply_markup=profile_rules_kb(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "rules")
async def cb_rules(callback: CallbackQuery) -> None:
    await callback.message.answer(rules_text(), reply_markup=profile_rules_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "active")
async def cb_active(callback: CallbackQuery) -> None:
    await callback.answer("Активные розыгрыши смотри в канале. Тут только профиль и правила.", show_alert=True)
