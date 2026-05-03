from __future__ import annotations

from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.session import session_scope
from app.services.giveaway_service import active_giveaway_ids, finish_giveaway
from app.utils.time import now_utc

_scheduler: AsyncIOScheduler | None = None
_bot: Bot | None = None
_settings: Settings | None = None


async def _finish_job(giveaway_id: int) -> None:
    if _bot is None or _settings is None:
        return
    async with session_scope() as session:
        await finish_giveaway(session, _bot, _settings, giveaway_id)


def init_scheduler(bot: Bot, settings: Settings) -> AsyncIOScheduler:
    global _scheduler, _bot, _settings
    _bot = bot
    _settings = settings
    _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler


def schedule_giveaway_finish(giveaway_id: int, run_at: datetime) -> None:
    if _scheduler is None:
        return
    run_at = run_at if run_at > now_utc() else now_utc() + timedelta(seconds=2)
    _scheduler.add_job(
        _finish_job,
        trigger="date",
        run_date=run_at,
        args=[giveaway_id],
        id=f"finish_giveaway:{giveaway_id}",
        replace_existing=True,
        misfire_grace_time=3600,
    )


async def restore_active_giveaways() -> None:
    async with session_scope() as session:
        rows = await active_giveaway_ids(session)
    for giveaway_id, seconds_left in rows:
        schedule_giveaway_finish(giveaway_id, now_utc() + timedelta(seconds=seconds_left))
