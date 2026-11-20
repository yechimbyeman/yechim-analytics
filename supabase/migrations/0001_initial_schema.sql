-- YECHIM Analytics: single-owner schema foundation.
-- No anon access. Authenticated access is additionally gated by app_access + RLS.
create extension if not exists pgcrypto;

create table public.app_access (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);

create table public.sources (
  id uuid primary key default gen_random_uuid(),
  platform text not null check (platform in ('telegram','instagram','website')),
  external_source_id text not null,
  title text,
  source_type text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  unique(platform, external_source_id)
);

create table public.chat_members (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources(id) on delete cascade,
  external_user_id text not null,
  username text,
  display_name text,
  is_bot boolean not null default false,
  is_staff boolean not null default false,
  first_seen_at timestamptz,
  last_seen_at timestamptz,
  unique(source_id, external_user_id)
);

create table public.messages (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources(id) on delete cascade,
  external_message_id text not null,
  member_id uuid references public.chat_members(id) on delete set null,
  message_kind text not null default 'message' check (message_kind in ('message','publication','comment','service')),
  body text,
  sent_at timestamptz not null,
  reply_to_external_message_id text,
  thread_id text,
  views_count bigint,
  forwards_count bigint,
  reactions jsonb not null default '{}'::jsonb,
  permalink text,
  raw_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(source_id, external_message_id)
);
create index messages_source_sent_at_idx on public.messages(source_id, sent_at desc);
create index messages_member_sent_at_idx on public.messages(member_id, sent_at desc);
create index messages_reply_idx on public.messages(source_id, reply_to_external_message_id);

create table public.request_classifications (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null unique references public.messages(id) on delete cascade,
  is_customer_request boolean not null default false,
  topic text,
  intent text,
  confidence numeric(4,3) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  request_group_key text,
  classified_at timestamptz not null default now()
);

create table public.exclusions (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources(id) on delete cascade,
  external_user_id text not null,
  exclusion_type text not null check (exclusion_type in ('staff','bot','other')),
  note text,
  created_at timestamptz not null default now(),
  unique(source_id, external_user_id)
);

create table public.publication_metrics_snapshots (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.messages(id) on delete cascade,
  captured_at timestamptz not null default now(),
  views_count bigint,
  forwards_count bigint,
  reactions jsonb not null default '{}'::jsonb
);
create index publication_snapshots_message_time_idx on public.publication_metrics_snapshots(message_id, captured_at desc);

alter table public.app_access enable row level security;
alter table public.sources enable row level security;
alter table public.chat_members enable row level security;
alter table public.messages enable row level security;
alter table public.request_classifications enable row level security;
alter table public.exclusions enable row level security;
alter table public.publication_metrics_snapshots enable row level security;

create policy app_access_owner_select on public.app_access
  for select to authenticated using (user_id = (select auth.uid()));

-- Avoid SECURITY DEFINER authorization helpers in the exposed public schema.
-- Each table is accessible only when the signed-in user has an explicit owner row.
create policy sources_owner_all on public.sources
  for all to authenticated
  using (exists (select 1 from public.app_access a where a.user_id = (select auth.uid())))
  with check (exists (select 1 from public.app_access a where a.user_id = (select auth.uid())));
create policy members_owner_all on public.chat_members
  for all to authenticated
  using (exists (select 1 from public.app_access a where a.user_id = (select auth.uid())))
  with check (exists (select 1 from public.app_access a where a.user_id = (select auth.uid())));
create policy messages_owner_all on public.messages
  for all to authenticated
  using (exists (select 1 from public.app_access a where a.user_id = (select auth.uid())))
  with check (exists (select 1 from public.app_access a where a.user_id = (select auth.uid())));
create policy classifications_owner_all on public.request_classifications
  for all to authenticated
  using (exists (select 1 from public.app_access a where a.user_id = (select auth.uid())))
  with check (exists (select 1 from public.app_access a where a.user_id = (select auth.uid())));
create policy exclusions_owner_all on public.exclusions
  for all to authenticated
  using (exists (select 1 from public.app_access a where a.user_id = (select auth.uid())))
  with check (exists (select 1 from public.app_access a where a.user_id = (select auth.uid())));
create policy snapshots_owner_all on public.publication_metrics_snapshots
  for all to authenticated
  using (exists (select 1 from public.app_access a where a.user_id = (select auth.uid())))
  with check (exists (select 1 from public.app_access a where a.user_id = (select auth.uid())));

grant usage on schema public to authenticated;
grant select on public.app_access to authenticated;
grant select, insert, update, delete on
  public.sources, public.chat_members, public.messages,
  public.request_classifications, public.exclusions,
  public.publication_metrics_snapshots to authenticated;
revoke all on public.app_access, public.sources, public.chat_members, public.messages,
  public.request_classifications, public.exclusions, public.publication_metrics_snapshots from anon;

-- Sequences are not used by these UUID-keyed tables; no sequence grants required.
