"""Resumable Telegram history importer for YECHIM Analytics.

Imports only the configured client-facing groups. Re-runs are idempotent.
Secrets are read from environment variables (GitHub Actions secrets/variables
or .env.local for local runs). Never commit .env.local.
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
from telethon.sessions import StringSession

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env.local")

START = datetime.fromisoformat(os.getenv("TELEGRAM_IMPORT_FROM", "2026-01-01T00:00:00+05:00"))
END = datetime.fromisoformat(os.getenv("TELEGRAM_IMPORT_TO", "2026-11-21T00:00:00+05:00"))
if START.tzinfo is None or END.tzinfo is None:
    raise SystemExit("TELEGRAM_IMPORT_FROM/TO must include timezone, e.g. +05:00")
if END <= START:
    raise SystemExit("TELEGRAM_IMPORT_TO must be later than TELEGRAM_IMPORT_FROM")


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing {name} in environment/.env.local")
    return value


def parse_ids(value: str) -> set[str]:
    return {part.strip() for part in value.split(",") if part.strip()}


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).isoformat() if dt else None


async def main() -> None:
    api_id = int(required("TELEGRAM_API_ID"))
    api_hash = required("TELEGRAM_API_HASH")
    # Multi-chat setting is preferred. Keep the singular setting for local
    # backward compatibility, but never import the non-customer EMAN Materials
    # Chat (-1001471696050) unless an owner explicitly adds it.
    chat_ids = parse_ids(os.getenv("TELEGRAM_CHAT_IDS", ""))
    if not chat_ids:
        legacy_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if legacy_chat_id:
            chat_ids = {legacy_chat_id}
    # YECHIM Analytics is intentionally scoped to Yechim Chat only.
    # Even if an old/misconfigured variable contains other chat IDs, they
    # must never be imported into analytics.
    allowed_chat_ids = {"-1002100556847"}
    chat_ids &= allowed_chat_ids
    if not chat_ids:
        raise SystemExit(
            "No allowed analytics chat configured. TELEGRAM_CHAT_IDS must include Yechim Chat (-1002100556847)."
        )

    supabase_url = required("NEXT_PUBLIC_SUPABASE_URL")
    service_key = required("SUPABASE_SERVICE_ROLE_KEY")
    staff_ids = parse_ids(os.getenv("TELEGRAM_STAFF_IDS", ""))
    configured_bot_ids = parse_ids(os.getenv("TELEGRAM_BOT_IDS", ""))

    db = create_client(supabase_url, service_key)
    client = TelegramClient(StringSession(required("TELEGRAM_SESSION_STRING")), api_id, api_hash)

    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        raise SystemExit(
            "TELEGRAM_SESSION_STRING is not authorized. Create a fresh StringSession "
            "in Codespaces and update the GitHub secret."
        )

    try:
        print(f"Configured groups: {len(chat_ids)}")
        print(f"Import interval: {START.isoformat()} → {END.isoformat()}")
        print("Authenticated with GitHub Actions secret; session is not persisted on the runner.")

        total_imported = 0
        total_skipped = 0

        for chat_ref in sorted(chat_ids):
            chat = await client.get_entity(int(chat_ref) if chat_ref.lstrip("-").isdigit() else chat_ref)
            chat_id = str(getattr(chat, "id"))
            chat_title = getattr(chat, "title", None) or getattr(chat, "username", None) or chat_id

            source_result = db.table("sources").upsert(
                {
                    "platform": "telegram",
                    "external_source_id": chat_id,
                    "title": chat_title,
                    "source_type": "supergroup",
                    "is_active": True,
                },
                on_conflict="platform,external_source_id",
            ).execute()
            source_id = source_result.data[0]["id"]

            print(f"\n=== {chat_title} ({chat_id}) ===")
            member_cache: dict[str, str] = {}
            imported = 0
            skipped = 0
            observed_bot_ids = set(configured_bot_ids)

            async for msg in client.iter_messages(chat, reverse=True, offset_date=START):
                sent_at = msg.date
                if sent_at is None:
                    skipped += 1
                    continue
                if sent_at < START.astimezone(timezone.utc):
                    continue
                if sent_at >= END.astimezone(timezone.utc):
                    break

                sender = await msg.get_sender()
                sender_id = str(getattr(sender, "id", "")) if sender else ""
                is_bot = bool(getattr(sender, "bot", False)) or sender_id in configured_bot_ids
                if is_bot and sender_id:
                    observed_bot_ids.add(sender_id)

                member_id = None
                if sender_id:
                    if sender_id not in member_cache:
                        first = getattr(sender, "first_name", "") or ""
                        last = getattr(sender, "last_name", "") or ""
                        display_name = " ".join(x for x in (first, last) if x).strip() or None
                        username = getattr(sender, "username", None)
                        row = db.table("chat_members").upsert(
                            {
                                "source_id": source_id,
                                "external_user_id": sender_id,
                                "username": username,
                                "display_name": display_name,
                                "is_bot": is_bot,
                                "is_staff": sender_id in staff_ids,
                                "first_seen_at": iso(sent_at),
                                "last_seen_at": iso(sent_at),
                            },
                            on_conflict="source_id,external_user_id",
                        ).execute()
                        member_cache[sender_id] = row.data[0]["id"]
                    member_id = member_cache[sender_id]

                reply_id = getattr(msg, "reply_to_msg_id", None)
                reactions: dict[str, Any] = {}
                reaction_obj = getattr(msg, "reactions", None)
                if reaction_obj and getattr(reaction_obj, "results", None):
                    for reaction in reaction_obj.results:
                        key = (
                            getattr(getattr(reaction, "reaction", None), "emoticon", None)
                            or str(getattr(reaction, "reaction", "unknown"))
                        )
                        reactions[key] = getattr(reaction, "count", 0)

                # Native Telegram channel posts are publications. Ordinary
                # staff messages remain messages, so manager replies are not
                # accidentally counted as advertising publications.
                is_native_post = bool(getattr(msg, "post", False))
                body = msg.message or ""
                record = {
                    "source_id": source_id,
                    "external_message_id": str(msg.id),
                    "member_id": member_id,
                    "message_kind": "publication" if is_native_post else "message",
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
                        "post": is_native_post,
                        "post_author": getattr(msg, "post_author", None),
                        "grouped_id": str(getattr(msg, "grouped_id", "")) or None,
                        "is_staff_authored_non_reply": sender_id in staff_ids and not reply_id,
                    },
                }
                db.table("messages").upsert(
                    record, on_conflict="source_id,external_message_id"
                ).execute()
                imported += 1
                if imported % 100 == 0:
                    print(f"Imported {imported} messages in {chat_title}…")

            # Exclusions are scoped to each imported source. Keep staff and
            # technical bot messages in storage, but make them ineligible for
            # customer-request counts.
            for user_id in sorted(staff_ids | observed_bot_ids):
                kind = "staff" if user_id in staff_ids else "bot"
                db.table("exclusions").upsert(
                    {
                        "source_id": source_id,
                        "external_user_id": user_id,
                        "exclusion_type": kind,
                        "note": "Configured YECHIM Telegram staff/bot exclusion",
                    },
                    on_conflict="source_id,external_user_id",
                ).execute()

            total_imported += imported
            total_skipped += skipped
            print(f"Finished {chat_title}. Imported/updated: {imported}; skipped: {skipped}")

        print(f"\nAll groups complete. Imported/updated: {total_imported}; skipped: {total_skipped}")
        print("Historical view counts unavailable from Telegram remain NULL, not zero.")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped. Re-run safely; upserts make the import resumable.")
        sys.exit(130)
