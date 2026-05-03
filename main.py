from __future__ import annotations

import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.config import get_settings
from app.db.session import create_db_schema
from app.handlers import admin, giveaways, user
from app.jobs.scheduler import init_scheduler, restore_active_giveaways


async def run_webhook(dp: Dispatcher, bot: Bot) -> None:
    settings = get_settings()
    assert settings.webhook_full_url is not None

    await bot.set_webhook(settings.webhook_full_url, drop_pending_updates=False)

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=settings.webhook_path)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.webapp_host, settings.webapp_port)
    await site.start()
    logging.info("Webhook started on %s:%s%s", settings.webapp_host, settings.webapp_port, settings.webhook_path)
    await asyncio.Event().wait()


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = get_settings()

    await create_db_schema()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = RedisStorage.from_url(settings.redis_url)
    dp = Dispatcher(storage=storage)
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(giveaways.router)

    scheduler = init_scheduler(bot, settings)
    scheduler.start()
    await restore_active_giveaways()

    if settings.webhook_full_url:
        await run_webhook(dp, bot)
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Polling started")
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
