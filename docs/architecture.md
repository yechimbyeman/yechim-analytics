# Architecture

## Product boundary
YECHIM Analytics is a private, single-owner marketing analytics workspace. Telegram is the first data source; Instagram is a future provider module.

## Data flow
1. A server-side Telegram collector authenticates as the owner's Telegram account using Telethon.
2. Initial history import stores Telegram message IDs, user IDs, timestamps, replies, threads, reactions and available counters.
3. Incremental collection ingests new messages and periodically refreshes publication metrics where Telegram exposes them.
4. Normalization stores members, messages and reply relationships.
5. Classification distinguishes customer requests from ordinary messages and assigns product/topic labels.
6. Staff and bots are excluded from customer metrics using stable Telegram user IDs, not usernames.
7. Next.js reads data through Supabase with Row Level Security.

## Semantics
- A message is not automatically a request.
- Several follow-up messages about one issue may form one request/conversation.
- Staff posts remain available for content analytics but are not counted as customer demand.
- Reply relationships and topic/thread identifiers must be preserved.
- Some group messages do not expose view counts. Store null when unavailable; never invent metrics.

## Security
- Private GitHub repository.
- Google OAuth with a single server-side ALLOWED_EMAIL check.
- Supabase RLS on all analytical tables.
- Telegram session, API hash, OAuth secrets and Supabase service-role key remain server-side and out of Git.
- Use TLS, secure cookies and database backups.

## Planned modules
- telegram: history importer and incremental collector.
- instagram: future Meta Graph API integration for eligible professional accounts.
- analytics: request classification, deduplication and aggregation.
- web: authenticated dashboard and drill-down views.
