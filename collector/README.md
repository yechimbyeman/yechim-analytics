# Telegram collector

## What it does
- Connects as the account owner through Telegram's client API (Telethon).
- Reads the configured supergroup history for the requested interval.
- Upserts members and messages into the YECHIM Analytics Supabase schema.
- Records stable Telegram user IDs, reply/thread references, reactions and available view/forward counts.
- Marks bot IDs automatically and staff IDs supplied by the owner as exclusions.
- Can be safely re-run: writes are idempotent on Telegram chat/message IDs.

## Local setup (Windows PowerShell)
From the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r collector/requirements.txt
Copy-Item .env.example .env.local
```

Fill the Telegram and Supabase variables in the local `.env.local` file. Do not send secrets in chat and do not commit this file.

Run:

```powershell
python collector/telegram_import.py
```

On first run, Telethon asks for the phone number, Telegram login code and (if enabled) the account's two-step verification password in the local terminal. The resulting `telegram_session_yechim.session` file is a credential: keep it private and never upload it.

## Important
- `SUPABASE_SERVICE_ROLE_KEY` bypasses RLS. Keep it only on the trusted local machine; never use it in Next.js browser code.
- Put the Telegram numeric chat ID in `TELEGRAM_CHAT_ID` (or a public @username if the group has one).
- Add known manager IDs as comma-separated numeric IDs in `TELEGRAM_STAFF_IDS`. Usernames can change; IDs are the exclusion key.
- Import dates are timezone-aware. Defaults are 2026-01-01 00:00 through 2026-11-21 00:00 at UTC+05:00, so 20 November is included.
- The first pass stores all group messages as message records. Publication identification and historical post-view snapshots need a separate reconciliation pass; Telegram does not expose historical view counts for every old post.
- Bot messages are tagged automatically. Managers are excluded from customer-request analytics by the stable ID list, but their authored posts remain in the message table for publication analysis.
