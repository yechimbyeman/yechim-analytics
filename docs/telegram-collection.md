# Telegram collection plan

## Initial backfill
- Use Telegram client API through a dedicated server-side Telethon collector authenticated by the owner's Telegram account.
- Import the requested local date interval (initial scope: 2026-01-01 through 2026-11-20).
- Preserve stable user IDs, message IDs, timestamps, reply links, topic/thread identifiers, edits/deletions where observable, reactions and available publication counters.
- Use idempotent upserts keyed by (source_id, external_message_id).

## Live collection
- Maintain an incremental cursor and periodically reconcile recent history.
- Refresh publication counters as Telegram exposes them; keep timestamped snapshots.
- Do not represent unavailable historical view counts as zero: store null.

## Classification rules
- Exclude staff and bots by stable Telegram user ID, not username.
- Keep staff-authored posts in publication analytics.
- Count customer messages separately from inferred customer requests.
- Group follow-ups about the same issue only when supported by reply/thread context or explicit classification; retain links to every source message.
- Replies to a company publication belong to its discussion thread and remain discoverable from both the post and the commenter profile.

## Operational safeguards
- Store Telegram session material only as server secrets or protected volume files, never in Git.
- Respect Telegram API limits; use retry/backoff and resumable imports.
- Log import checkpoints and failures without logging message bodies or credentials.
