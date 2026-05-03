from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.config import get_settings
from app.db.models import EntrySource, Giveaway, GiveawayStatus, GiveawayType
from app.db.session import session_scope
from app.keyboards import auto_drop_kb
from app.services.giveaway_service import (
    add_entry,
    count_entries,
    create_auto_giveaway,
    find_active_auto_by_comment,
    get_giveaway,
    update_manual_markup,
)
from app.services.user_service import get_user_by_tg
from app.services.runtime import auto_drops_enabled
from app.texts import auto_drop_text, joined_text

router = Router(name="giveaways")
settings = get_settings()


def _origin_channel_message_id(message: Message) -> int | None:
    origin = getattr(message, "forward_origin", None)
    if origin and getattr(origin, "type", None) == "channel":
        return getattr(origin, "message_id", None)
    return None


def _root_id_from_comment(message: Message) -> int | None:
    if message.reply_to_message:
        return message.reply_to_message.message_id
    return None


@router.message(F.chat.id == settings.discussion_chat_id, F.is_automatic_forward == True)  # noqa: E712
async def auto_forwarded_channel_post(message: Message) -> None:
    if not auto_drops_enabled():
        return
    async with session_scope() as session:
        existing = await session.execute(
            select(Giveaway).where(
                Giveaway.type == GiveawayType.AUTO.value,
                Giveaway.status == GiveawayStatus.ACTIVE.value,
                Giveaway.discussion_chat_id == str(message.chat.id),
                Giveaway.discussion_root_message_id == message.message_id,
            )
        )
        if existing.scalar_one_or_none():
            return
        giveaway = await create_auto_giveaway(
            session,
            settings,
            channel_message_id=_origin_channel_message_id(message),
            discussion_root_message_id=message.message_id,
            discussion_message_thread_id=message.message_thread_id,
        )
        sent = await message.reply(
            auto_drop_text(giveaway.title, giveaway.prize_name, giveaway.ends_at, giveaway.min_participants),
            reply_markup=auto_drop_kb(settings.bot_username, giveaway.id),
            parse_mode="HTML",
        )
        giveaway.announcement_message_id = sent.message_id


@router.message(F.chat.id == settings.discussion_chat_id)
async def collect_comment_entry(message: Message) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return
    if getattr(message, "is_automatic_forward", False):
        return

    root_id = _root_id_from_comment(message)
    thread_id = message.message_thread_id

    async with session_scope() as session:
        giveaway = await find_active_auto_by_comment(session, message.chat.id, root_id, thread_id)
        if giveaway is None:
            return
        user = await get_user_by_tg(session, message.from_user.id)
        result = await add_entry(
            session,
            message.bot,
            settings,
            giveaway=giveaway,
            user=user,
            telegram_id=message.from_user.id,
            comment_message_id=message.message_id,
            source=EntrySource.COMMENT,
        )
        # Не спамим в чат ответами на каждый коммент. Участие видно в итогах.


@router.callback_query(F.data.startswith("join:"))
async def join_manual_giveaway(callback: CallbackQuery) -> None:
    giveaway_id = int(callback.data.split(":", 1)[1])
    async with session_scope() as session:
        giveaway = await get_giveaway(session, giveaway_id)
        if giveaway is None:
            await callback.answer("Розыгрыш не найден.", show_alert=True)
            return
        user = await get_user_by_tg(session, callback.from_user.id)
        result = await add_entry(
            session,
            callback.bot,
            settings,
            giveaway=giveaway,
            user=user,
            telegram_id=callback.from_user.id,
            comment_message_id=None,
            source=EntrySource.BUTTON,
        )
        if not result.ok:
            await callback.answer(result.reason, show_alert=True)
            return
        await update_manual_markup(callback.bot, settings, giveaway, result.count)
        await callback.answer("Ты участвуешь.", show_alert=False)
        try:
            await callback.from_user.send_message(
                joined_text(giveaway.title, result.entry_number or result.count, giveaway.ends_at),
                parse_mode="HTML",
            )
        except Exception:
            pass
