from __future__ import annotations

from aiogram.types import User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get_user_by_tg(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def register_user(session: AsyncSession, tg_user: TgUser) -> User:
    user = await get_user_by_tg(session, tg_user.id)
    if user is None:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            is_registered=True,
        )
        session.add(user)
        await session.flush()
        return user
    user.username = tg_user.username
    user.first_name = tg_user.first_name
    user.is_registered = True
    user.blocked_bot = False
    await session.flush()
    return user


async def ban_user(session: AsyncSession, telegram_id: int, banned: bool = True) -> User:
    user = await get_user_by_tg(session, telegram_id)
    if user is None:
        user = User(telegram_id=telegram_id, is_registered=False, is_banned=banned)
        session.add(user)
    else:
        user.is_banned = banned
    await session.flush()
    return user
