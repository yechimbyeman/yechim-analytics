"""Resumable Telegram history importer for YECHIM Analytics.

Run from the repository root:
  python -m pip install -r collector/requirements.txt
  python collector/telegram_import.py

Secrets are read from .env.local in the repository root. Never commit that file.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import create_client
from telethon import TelegramClient
from telethon.tl.types import User

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env.local")

START = datetime.fromisoformat(os.getenv("TELEGRAM_IMPORT_FROM", "2026-01-01T00:00:00+05:00"))
END = datetime.fromisoformat(os.getenv("TELEGRAM_IMPORT_TO", "2026-11-21T00:00:00+05:00"))
if START.tzinfo is None or END.tzinfo is None:
    raise SystemExit("TELEGRAM_IMPORT_FROM/TO must include timezone, e.g. +05:00")

def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing {name} in .env.local")
    return value

def parse_ids(value: str) -> set[str]:
    return {part.strip() for part in value.split(",") if part.strip()}

def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).isoformat() if dt else None

async def main() -> None:
    api_id = int(required("TELEGRAM_API_ID"))
    api_hash = required("TELEGRAM_API_HASH")
    chat_ref = required("TELEGRAM_CHAT_ID")
    supabase_url = required("NEXT_PUBLIC_SUPABASE_URL")
    service_key = required("SUPABASE_SERVICE_ROLE_KEY")
    staff_ids = parse_ids(os.getenv("TELEGRAM_STAFF_IDS", ""))
    bot_ids: set[str] = set()

    db = create_client(supabase_url, service_key)
    client = TelegramClient(str(ROOT / "telegram_session_yechim"), api_id, api_hash)

    await client.start()
    try:
        chat = await client.get_entity(int(chat_ref) if chat_ref.lstrip("-").isdigit() else chat_ref)
        chat_id = str(getattr(chat, "id"))
        chat_title = getattr(chat, "title", None) or getattr(chat, "username", None) or chat_id

        source_result = db.table("sources").upsert({
            "platform": "telegram",
            "external_source_id": chat_id,
            "title": chat_title,
            "source_type": "supergroup",
            "is_active": True,
        }, on_conflict="platform,external_source_id").execute()
        source_id = source_result.data[0]["id"]

        print(f"Chat: {chat_title} ({chat_id})")
        print(f"Import interval: {START.isoformat()} → {END.isoformat()}")
        print("Telegram session is local. Follow the Telegram login prompt if this is the first run.")

        member_cache: dict[str, str] = {}
        imported = 0
        skipped = 0

        async for msg in client.iter_messages(chat, reverse=True, offset_date=START):
            sent_at = msg.date
            if sent_at is None:
                skipped += 1
                continue
            # Telegram message dates are UTC; compare against timezone-aware boundaries.
            if sent_at < START.astimezone(timezone.utc):
                continue
            if sent_at >= END.astimezone(timezone.utc):
                break

            sender = await msg.get_sender()
            sender_id = str(getattr(sender, "id", "")) if sender else ""
            is_bot = bool(getattr(sender, "bot", False))
            if is_bot and sender_id:
                bot_ids.add(sender_id)

            member_id = None
            if sender_id:
                if sender_id not in member_cache:
                    first = getattr(sender, "first_name", "") or ""
                    last = getattr(sender, "last_name", "") or ""
                    display_name = " ".join(x for x in (first, last) if x).strip() or None
                    username = getattr(sender, "username", None)
                    row = db.table("chat_members").upsert({
                        "source_id": source_id,
                        "external_user_id": sender_id,
                        "username": username,
                        "display_name": display_name,
                        "is_bot": is_bot,
                        "is_staff": sender_id in staff_ids,
                        "first_seen_at": iso(sent_at),
                        "last_seen_at": iso(sent_at),
                    }, on_conflict="source_id,external_user_id").execute()
                    member_cache[sender_id] = row.data[0]["id"]
                member_id = member_cache[sender_id]

            reply_id = getattr(msg, "reply_to_msg_id", None)
            reactions: dict[str, Any] = {}
            reaction_obj = getattr(msg, "reactions", None)
            if reaction_obj and getattr(reaction_obj, "results", None):
                for reaction in reaction_obj.results:
                    key = getattr(getattr(reaction, "reaction", None), "emoticon", None) or str(getattr(reaction, "reaction", "unknown"))
                    reactions[key] = getattr(reaction, "count", 0)

            body = msg.message or ""
            record = {
                "source_id": source_id,
                "external_message_id": str(msg.id),
                "member_id": member_id,
                "message_kind": "message",
                "body": body,
                "sent_at": iso(sent_at),
                "reply_to_external_message_id": str(reply_id) if reply_id else None,
                "thread_id": str(getattr(getattr(msg, "reply_to", None), "reply_to_top_id", "") or "") or None,
                "views_count": getattr(msg, "views", None),
                "forwards_count": getattr(msg, "forwards", None),
                "reactions": reactions,
                "permalink": None,
                "raw_metadata": {
                    "is_bot": is_bot,
                    "is_staff_by_config": sender_id in staff_ids,
                    "out": bool(getattr(msg, "out", False)),
                    "post_author": getattr(msg, "post_author", None),
                    "grouped_id": str(getattr(msg, "grouped_id", "")) or None,
                },
            }
            db.table("messages").upsert(
                record, on_conflict="source_id,external_message_id"
            ).execute()
            imported += 1
            if imported % 100 == 0:
                print(f"Imported {imported} messages…")

        # Store known bot/staff exclusions, keyed by stable Telegram user ID.
        for user_id in sorted(bot_ids | staff_ids):
            kind = "staff" if user_id in staff_ids else "bot"
            db.table("exclusions").upsert({
                "source_id": source_id,
                "external_user_id": user_id,
                "exclusion_type": kind,
                "note": "Imported by Telegram collector",
            }, on_conflict="source_id,external_user_id").execute()

        print(f"Done. Imported/updated: {imported}; skipped: {skipped}")
        print("Note: Telegram API only exposes currently available publication counters; unavailable historical views remain NULL.")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped. Re-run safely; upserts make the import resumable.")
        sys.exit(130)
