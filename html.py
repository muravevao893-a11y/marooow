from __future__ import annotations

from html import escape


def h(text: object) -> str:
    return escape(str(text), quote=False)


def user_link(telegram_id: int, title: str | None = None, username: str | None = None) -> str:
    if username:
        return f"@{h(username)}"
    shown = title or str(telegram_id)
    return f'<a href="tg://user?id={telegram_id}">{h(shown)}</a>'
