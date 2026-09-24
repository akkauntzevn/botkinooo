from typing import Sequence

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def sponsors_keyboard(sponsors: Sequence[dict], pending_code: str | None):
    """One button per sponsor channel + a 'I joined, check again' button."""
    builder = InlineKeyboardBuilder()
    for s in sponsors:
        if s.get("username"):
            url = f"https://t.me/{s['username']}"
        elif s.get("invite_link"):
            url = s["invite_link"]
        else:
            continue
        builder.row(InlineKeyboardButton(text=f"➕ {s['title'] or s['username']}", url=url))

    check_payload = f"checksub:{pending_code or '-'}"
    builder.row(InlineKeyboardButton(text="✅ Tekshirish / Check again", callback_data=check_payload))
    return builder.as_markup()


def admin_panel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Sponsorlar ro'yxati", callback_data="admin:list_sponsors"))
    builder.row(InlineKeyboardButton(text="🎬 Kinolar ro'yxati", callback_data="admin:list_movies"))
    return builder.as_markup()
