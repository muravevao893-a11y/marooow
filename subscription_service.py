from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError


ACTIVE_STATUSES = {"creator", "administrator", "member"}


async def is_subscribed(bot: Bot, channel_id: int | str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(channel_id, user_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return False
    return member.status in ACTIVE_STATUSES
