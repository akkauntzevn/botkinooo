"""
Handles Telegram's "join request" (so'rov / zayavka) flow for sponsor
channels that have "Approve new members" turned ON.

Without this, a user who sends a join request stays NOT a member
until a human manually approves it in Telegram — so
`check_missing_subscriptions()` keeps blocking them even though
they've already clicked "join". This module auto-approves any
join request that comes from a channel we actually track as an
active sponsor, so the flow becomes instant and needs no manual
admin action.

REQUIRES: the bot must be an admin in that sponsor channel with
rights to manage/approve join requests (this is a normal admin
right in Telegram, same one a human moderator would need).
"""
from __future__ import annotations

from aiogram import Router, Bot
from aiogram.types import ChatJoinRequest

from database import Database

router = Router(name="join_requests")


@router.chat_join_request()
async def auto_approve_sponsor_requests(request: ChatJoinRequest, bot: Bot, db: Database):
    sponsors = await db.list_active_sponsors()
    sponsor_ids = {s["chat_id"] for s in sponsors}

    if request.chat.id not in sponsor_ids:
        # Not one of our mandatory-subscription channels — leave it for a
        # human to review, we have no business auto-approving it.
        return

    try:
        await request.approve()
    except Exception:
        # Bot isn't admin there yet / lost rights — nothing else to do,
        # and we must not crash the update loop over one bad chat.
        return

    try:
        await bot.send_message(
            request.from_user.id,
            "✅ So'rovingiz qabul qilindi!\n"
            "Endi \"✅ Tekshirish\" tugmasini yoki kino kodini qayta yuboring.",
        )
    except Exception:
        # User may never have opened a DM with the bot yet (rare in the
        # normal flow, since they get here via our own join buttons) —
        # safe to ignore.
        pass
