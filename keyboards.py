from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def user_home_kb(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Активные розыгрыши", callback_data="active")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"), InlineKeyboardButton(text="📜 Правила", callback_data="rules")],
    ])


def profile_rules_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"), InlineKeyboardButton(text="📜 Правила", callback_data="rules")],
    ])


def auto_drop_kb(bot_username: str, giveaway_id: int) -> InlineKeyboardMarkup:
    deep = f"https://t.me/{bot_username}?start=drop_{giveaway_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧸 Зарегаться / участвовать", url=deep)],
        [InlineKeyboardButton(text="👤 Профиль", url=f"https://t.me/{bot_username}?start=profile"), InlineKeyboardButton(text="📜 Правила", url=f"https://t.me/{bot_username}?start=rules")],
    ])


def manual_giveaway_kb(giveaway_id: int, count: int, bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎁 Участвовать · {count}", callback_data=f"join:{giveaway_id}")],
        [InlineKeyboardButton(text="👤 Профиль", url=f"https://t.me/{bot_username}?start=profile"), InlineKeyboardButton(text="📜 Условия", url=f"https://t.me/{bot_username}?start=rules")],
    ])


def after_join_kb(channel_id: int | str | None = None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_home_kb(auto_enabled: bool = True) -> InlineKeyboardMarkup:
    auto_text = "🟢 Авто-дропы" if auto_enabled else "🔴 Авто-дропы"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Создать розыгрыш", callback_data="admin:create")],
        [InlineKeyboardButton(text=auto_text, callback_data="admin:auto")],
        [InlineKeyboardButton(text="📦 Подарки", callback_data="admin:gifts"), InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin:close")],
    ])


def admin_auto_kb(enabled: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Включить" if not enabled else "🔴 Выключить", callback_data="admin:auto:toggle")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:home")],
    ])


def admin_preview_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data="admin:publish")],
        [InlineKeyboardButton(text="✏️ Заполнить заново", callback_data="admin:create"), InlineKeyboardButton(text="❌ Отменить", callback_data="admin:cancel")],
    ])


def admin_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="admin:cancel")],
    ])


def result_kb(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Новые розыгрыши", url=f"https://t.me/{bot_username}")],
    ])
