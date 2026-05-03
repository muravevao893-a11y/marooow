from __future__ import annotations

from datetime import datetime

from app.utils.html import h, user_link
from app.utils.time import fmt_dt

BRAND = "&amp;marooow"


def start_text(first_name: str | None, entries: int, wins: int) -> str:
    name = h(first_name or "ты")
    return (
        f"<b>{BRAND}</b>\n\n"
        f"{name}, профиль создан.\n\n"
        f"Теперь твои комменты под постами участвуют в дропах, если ты подписан на канал.\n\n"
        f"<b>Профиль</b>\n"
        f"Участий: <b>{entries}</b>\n"
        f"Побед: <b>{wins}</b>"
    )


def profile_text(telegram_id: int, username: str | None, first_name: str | None, entries: int, wins: int, banned: bool) -> str:
    status = "бан" if banned else "активен"
    handle = f"@{h(username)}" if username else "—"
    return (
        f"<b>{BRAND} profile</b>\n\n"
        f"ID: <code>{telegram_id}</code>\n"
        f"Ник: {handle}\n"
        f"Имя: {h(first_name or '—')}\n"
        f"Участий: <b>{entries}</b>\n"
        f"Побед: <b>{wins}</b>\n"
        f"Статус: <b>{status}</b>"
    )


def rules_text() -> str:
    return (
        f"<b>{BRAND} rules</b>\n\n"
        "— один аккаунт = один шанс\n"
        "— нужен профиль в боте\n"
        "— нужна подписка на канал\n"
        "— спам и мультиакки улетают в бан\n"
        "— если подарок не получилось отправить сразу, админ проверит выдачу вручную"
    )


def auto_drop_text(title: str, prize: str, ends_at: datetime, min_participants: int) -> str:
    min_line = f"\nМинимум участников: <b>{min_participants}</b>" if min_participants > 1 else ""
    return (
        f"<b>{BRAND} drop</b>\n\n"
        f"🧸 <b>{h(title)}</b>\n\n"
        "Оставь любой коммент под этим постом.\n"
        "Победит рандомный зарегистрированный участник.\n\n"
        f"Приз: <b>{h(prize)}</b>\n"
        f"Финиш: <b>{fmt_dt(ends_at)}</b>{min_line}\n\n"
        "Не нажал Start в боте — не участвуешь."
    )


def manual_giveaway_text(title: str, description: str | None, prize: str, winners: int, ends_at: datetime, count: int) -> str:
    desc = f"\n{h(description)}\n" if description else "\n"
    return (
        f"<b>{BRAND}</b>\n\n"
        f"🎁 <b>{h(title)}</b>\n"
        f"{desc}\n"
        f"Приз: <b>{h(prize)}</b>\n"
        f"Победителей: <b>{winners}</b>\n"
        f"Участников сейчас: <b>{count}</b>\n"
        f"Финиш: <b>{fmt_dt(ends_at)}</b>\n\n"
        "Условия:\n"
        "— профиль в боте\n"
        "— подписка на канал\n"
        "— участие через кнопку"
    )


def already_joined_text(title: str) -> str:
    return f"Ты уже участвуешь в «{h(title)}»."


def joined_text(title: str, number: int, ends_at: datetime) -> str:
    return (
        "Ты в розыгрыше.\n\n"
        f"Розыгрыш: <b>{h(title)}</b>\n"
        f"Твой номер: <b>#{number}</b>\n"
        f"Итоги: <b>{fmt_dt(ends_at)}</b>"
    )


def finish_no_winners_text(title: str, participants: int, min_participants: int) -> str:
    return (
        f"🏁 <b>{BRAND} drop завершен</b>\n\n"
        f"Розыгрыш: <b>{h(title)}</b>\n"
        f"Участников: <b>{participants}</b>\n\n"
        f"Победителей нет: нужно минимум <b>{min_participants}</b>."
    )


def finish_winners_text(title: str, prize: str, participants: int, winner_rows: list[tuple[int, str | None, str | None]]) -> str:
    lines = []
    for i, (telegram_id, username, first_name) in enumerate(winner_rows, start=1):
        lines.append(f"{i}. {user_link(telegram_id, first_name, username)}")
    winners = "\n".join(lines)
    return (
        f"🏁 <b>{BRAND} drop завершен</b>\n\n"
        f"Розыгрыш: <b>{h(title)}</b>\n"
        f"Приз: <b>{h(prize)}</b>\n"
        f"Участников: <b>{participants}</b>\n\n"
        f"<b>Победители:</b>\n{winners}\n\n"
        "Подарки отправляются автоматически или проверяются админом."
    )


def admin_home_text() -> str:
    return f"<b>{BRAND} admin</b>\n\nЧто делаем?"


def create_preview_text(title: str, prize: str, winners: int, duration_min: int, description: str | None, gift_id: str | None) -> str:
    return (
        f"<b>Предпросмотр</b>\n\n"
        f"Название: <b>{h(title)}</b>\n"
        f"Приз: <b>{h(prize)}</b>\n"
        f"Победителей: <b>{winners}</b>\n"
        f"Время: <b>{duration_min} мин.</b>\n"
        f"Gift ID: <code>{h(gift_id or 'ручная выдача')}</code>\n\n"
        f"Описание:\n{h(description or '—')}"
    )
