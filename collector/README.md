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
- Set `TELEGRAM_CHAT_IDS` to comma-separated numeric group IDs. Current YECHIM sources: `-1002100556847,-1001177712598`. The unrelated `EMAN Materials Chat` (`-1001471696050`) is deliberately not imported.
- Set `TELEGRAM_STAFF_IDS` to comma-separated manager/owner IDs: `6232977465,1896060752,7108824215`.
- Set `TELEGRAM_BOT_IDS` to known technical bot IDs: `1437923662`. Bot and staff messages remain stored for audit/publication analysis but are excluded from customer-request analytics.
- The legacy `TELEGRAM_CHAT_ID` remains supported for local single-chat runs; GitHub Actions uses `TELEGRAM_CHAT_IDS`.
- Import dates are timezone-aware. Defaults are 2026-01-01 00:00 through 2026-11-21 00:00 at UTC+05:00, so 20 November is included.
- The first pass stores all group messages as message records. Publication identification and historical post-view snapshots need a separate reconciliation pass; Telegram does not expose historical view counts for every old post.
- Bot messages are tagged automatically. Managers are excluded from customer-request analytics by the stable ID list, but their authored posts remain in the message table for publication analysis.
