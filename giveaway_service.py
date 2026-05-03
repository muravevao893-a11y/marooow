from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Iterable

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.db.models import (
    DeliveryStatus,
    EntrySource,
    Giveaway,
    GiveawayEntry,
    GiveawayStatus,
    GiveawayType,
    GiveawayWinner,
    User,
    utcnow,
)
from app.keyboards import manual_giveaway_kb, result_kb
from app.services.gift_service import send_gift_to_user
from app.services.subscription_service import is_subscribed
from app.texts import finish_no_winners_text, finish_winners_text, manual_giveaway_text


class JoinResult:
    def __init__(self, ok: bool, reason: str, count: int = 0, entry_number: int | None = None, giveaway: Giveaway | None = None) -> None:
        self.ok = ok
        self.reason = reason
        self.count = count
        self.entry_number = entry_number
        self.giveaway = giveaway


async def create_manual_giveaway(
    session: AsyncSession,
    settings: Settings,
    *,
    title: str,
    description: str | None,
    prize_name: str,
    gift_id: str | None,
    winners_count: int,
    duration_minutes: int,
    image_file_id: str | None,
    created_by: int,
) -> Giveaway:
    now = utcnow()
    giveaway = Giveaway(
        type=GiveawayType.MANUAL.value,
        status=GiveawayStatus.ACTIVE.value,
        title=title,
        description=description,
        prize_name=prize_name,
        gift_id=gift_id,
        winners_count=winners_count,
        image_file_id=image_file_id,
        channel_id=str(settings.channel_id),
        require_subscription=settings.require_subscription,
        created_by=created_by,
        starts_at=now,
        ends_at=now + timedelta(minutes=duration_minutes),
    )
    session.add(giveaway)
    await session.flush()
    return giveaway


async def publish_manual_giveaway(bot: Bot, session: AsyncSession, settings: Settings, giveaway: Giveaway) -> Giveaway:
    text = manual_giveaway_text(
        giveaway.title,
        giveaway.description,
        giveaway.prize_name,
        giveaway.winners_count,
        giveaway.ends_at,
        count=0,
    )
    kb = manual_giveaway_kb(giveaway.id, 0, settings.bot_username)
    if giveaway.image_file_id:
        msg = await bot.send_photo(settings.channel_id, giveaway.image_file_id, caption=text, reply_markup=kb, parse_mode="HTML")
    else:
        msg = await bot.send_message(settings.channel_id, text, reply_markup=kb, parse_mode="HTML")
    giveaway.channel_message_id = msg.message_id
    await session.flush()
    return giveaway


async def create_auto_giveaway(
    session: AsyncSession,
    settings: Settings,
    *,
    channel_message_id: int | None,
    discussion_root_message_id: int,
    discussion_message_thread_id: int | None,
) -> Giveaway:
    now = utcnow()
    giveaway = Giveaway(
        type=GiveawayType.AUTO.value,
        status=GiveawayStatus.ACTIVE.value,
        title=settings.auto_drop_title,
        description=None,
        prize_name=settings.auto_drop_prize,
        gift_id=settings.auto_drop_gift_id,
        winners_count=settings.auto_drop_winners,
        channel_id=str(settings.channel_id),
        channel_message_id=channel_message_id,
        discussion_chat_id=str(settings.discussion_chat_id),
        discussion_root_message_id=discussion_root_message_id,
        discussion_message_thread_id=discussion_message_thread_id,
        min_participants=settings.auto_drop_min_participants,
        require_subscription=settings.require_subscription,
        starts_at=now,
        ends_at=now + timedelta(seconds=settings.auto_drop_duration_seconds),
    )
    session.add(giveaway)
    await session.flush()
    return giveaway


async def count_entries(session: AsyncSession, giveaway_id: int) -> int:
    result = await session.execute(
        select(func.count(GiveawayEntry.id)).where(
            GiveawayEntry.giveaway_id == giveaway_id,
            GiveawayEntry.is_valid.is_(True),
        )
    )
    return int(result.scalar_one())


async def get_giveaway(session: AsyncSession, giveaway_id: int) -> Giveaway | None:
    result = await session.execute(select(Giveaway).where(Giveaway.id == giveaway_id))
    return result.scalar_one_or_none()


async def find_active_auto_by_comment(session: AsyncSession, discussion_chat_id: int | str, root_message_id: int | None, thread_id: int | None) -> Giveaway | None:
    clauses = [
        Giveaway.status == GiveawayStatus.ACTIVE.value,
        Giveaway.type == GiveawayType.AUTO.value,
        Giveaway.discussion_chat_id == str(discussion_chat_id),
    ]
    if root_message_id is not None:
        result = await session.execute(
            select(Giveaway).where(*clauses, Giveaway.discussion_root_message_id == root_message_id).order_by(Giveaway.id.desc())
        )
        giveaway = result.scalar_one_or_none()
        if giveaway:
            return giveaway
    if thread_id is not None:
        result = await session.execute(
            select(Giveaway).where(*clauses, Giveaway.discussion_message_thread_id == thread_id).order_by(Giveaway.id.desc())
        )
        return result.scalar_one_or_none()
    return None


async def add_entry(
    session: AsyncSession,
    bot: Bot,
    settings: Settings,
    *,
    giveaway: Giveaway,
    user: User | None,
    telegram_id: int,
    comment_message_id: int | None,
    source: EntrySource,
) -> JoinResult:
    if giveaway.status != GiveawayStatus.ACTIVE.value:
        return JoinResult(False, "Розыгрыш уже закрыт.", giveaway=giveaway)
    if giveaway.ends_at <= utcnow():
        return JoinResult(False, "Розыгрыш уже закончился.", giveaway=giveaway)
    if user is None or not user.is_registered:
        return JoinResult(False, "Сначала открой бота и нажми Start.", giveaway=giveaway)
    if user.is_banned:
        return JoinResult(False, "Ты в бане.", giveaway=giveaway)
    if giveaway.require_subscription:
        subscribed = await is_subscribed(bot, settings.channel_id, telegram_id)
        if not subscribed:
            return JoinResult(False, "Нужно подписаться на канал.", giveaway=giveaway)

    existing = await session.execute(
        select(GiveawayEntry.id).where(
            GiveawayEntry.giveaway_id == giveaway.id,
            GiveawayEntry.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        count = await count_entries(session, giveaway.id)
        return JoinResult(False, "Ты уже участвуешь.", count=count, giveaway=giveaway)

    entry = GiveawayEntry(
        giveaway_id=giveaway.id,
        user_id=user.id,
        telegram_id=telegram_id,
        comment_message_id=comment_message_id,
        source=source.value,
        is_valid=True,
    )
    session.add(entry)
    await session.flush()

    user.entries_count += 1
    count = await count_entries(session, giveaway.id)
    return JoinResult(True, "ok", count=count, entry_number=count, giveaway=giveaway)


async def select_random_entries(session: AsyncSession, giveaway_id: int, limit: int) -> list[GiveawayEntry]:
    result = await session.execute(
        select(GiveawayEntry)
        .options(selectinload(GiveawayEntry.user))
        .where(GiveawayEntry.giveaway_id == giveaway_id, GiveawayEntry.is_valid.is_(True))
    )
    entries = list(result.scalars().all())
    if not entries:
        return []
    rng = secrets.SystemRandom()
    rng.shuffle(entries)
    return entries[: max(0, min(limit, len(entries)))]


async def finish_giveaway(session: AsyncSession, bot: Bot, settings: Settings, giveaway_id: int) -> Giveaway | None:
    result = await session.execute(
        select(Giveaway)
        .options(selectinload(Giveaway.entries).selectinload(GiveawayEntry.user), selectinload(Giveaway.winners))
        .where(Giveaway.id == giveaway_id)
    )
    giveaway = result.scalar_one_or_none()
    if giveaway is None or giveaway.status != GiveawayStatus.ACTIVE.value:
        return giveaway

    participants = await count_entries(session, giveaway.id)
    giveaway.status = GiveawayStatus.FINISHED.value
    giveaway.finished_at = utcnow()

    if participants < giveaway.min_participants:
        await post_result(bot, settings, giveaway, finish_no_winners_text(giveaway.title, participants, giveaway.min_participants))
        await session.flush()
        return giveaway

    selected = await select_random_entries(session, giveaway.id, giveaway.winners_count)
    winner_rows: list[tuple[int, str | None, str | None]] = []

    for entry in selected:
        winner = GiveawayWinner(
            giveaway_id=giveaway.id,
            user_id=entry.user.id,
            gift_id=giveaway.gift_id,
            delivery_status=DeliveryStatus.PENDING.value,
        )
        session.add(winner)
        entry.user.wins_count += 1
        await session.flush()
        await send_gift_to_user(bot, settings, winner, entry.telegram_id, giveaway.gift_id)
        winner_rows.append((entry.telegram_id, entry.user.username, entry.user.first_name))

    await post_result(bot, settings, giveaway, finish_winners_text(giveaway.title, giveaway.prize_name, participants, winner_rows))
    await session.flush()
    return giveaway


async def post_result(bot: Bot, settings: Settings, giveaway: Giveaway, text: str) -> None:
    try:
        if giveaway.type == GiveawayType.AUTO.value and giveaway.discussion_chat_id and giveaway.discussion_root_message_id:
            await bot.send_message(
                int(giveaway.discussion_chat_id),
                text,
                parse_mode="HTML",
                reply_to_message_id=giveaway.discussion_root_message_id,
                reply_markup=result_kb(settings.bot_username),
            )
        else:
            await bot.send_message(
                settings.channel_id,
                text,
                parse_mode="HTML",
                reply_to_message_id=giveaway.channel_message_id,
                reply_markup=result_kb(settings.bot_username),
            )
    except TelegramAPIError:
        # Never break finishing logic because Telegram refused a result post.
        return


async def update_manual_markup(bot: Bot, settings: Settings, giveaway: Giveaway, count: int) -> None:
    if not giveaway.channel_message_id:
        return
    try:
        await bot.edit_message_reply_markup(
            chat_id=settings.channel_id,
            message_id=giveaway.channel_message_id,
            reply_markup=manual_giveaway_kb(giveaway.id, count, settings.bot_username),
        )
    except TelegramAPIError:
        return


async def active_giveaway_ids(session: AsyncSession) -> list[tuple[int, float]]:
    now = utcnow()
    result = await session.execute(select(Giveaway.id, Giveaway.ends_at).where(Giveaway.status == GiveawayStatus.ACTIVE.value))
    rows = result.all()
    return [(gid, max(0.0, (ends_at - now).total_seconds())) for gid, ends_at in rows]
