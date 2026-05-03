from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

from app.config import Settings
from app.db.models import DeliveryStatus, GiveawayWinner


async def send_gift_to_user(bot: Bot, settings: Settings, winner: GiveawayWinner, user_id: int, gift_id: str | None) -> None:
    if not gift_id:
        winner.delivery_status = DeliveryStatus.MANUAL_REQUIRED.value
        winner.delivery_error = "gift_id is empty; manual delivery required"
        return

    try:
        await bot.send_gift(
            user_id=user_id,
            gift_id=gift_id,
            text=settings.gift_text,
        )
    except TelegramForbiddenError as exc:
        winner.delivery_status = DeliveryStatus.FAILED.value
        winner.delivery_error = f"user blocked bot or forbidden: {exc}"
    except TelegramAPIError as exc:
        winner.delivery_status = DeliveryStatus.FAILED.value
        winner.delivery_error = str(exc)
    else:
        winner.delivery_status = DeliveryStatus.SENT.value
        winner.delivery_error = None


async def format_available_gifts(bot: Bot, limit: int = 30) -> str:
    gifts = await bot.get_available_gifts()
    rows: list[str] = []
    for gift in gifts.gifts[:limit]:
        star_count = getattr(gift, "star_count", "?")
        total_count = getattr(gift, "total_count", None)
        remaining_count = getattr(gift, "remaining_count", None)
        extra = ""
        if remaining_count is not None:
            extra = f" · left {remaining_count}"
        elif total_count is not None:
            extra = f" · total {total_count}"
        rows.append(f"<code>{gift.id}</code> — ⭐ {star_count}{extra}")
    if not rows:
        return "Доступных подарков нет."
    return "<b>Доступные gifts</b>\n\n" + "\n".join(rows)
