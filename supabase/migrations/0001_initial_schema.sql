-- YECHIM Analytics: single-owner schema foundation.
create extension if not exists pgcrypto;

create table if not exists public.app_access (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);

create or replace function public.is_app_owner()
returns boolean language sql stable security definer set search_path = public
as $$ select exists (select 1 from public.app_access where user_id = auth.uid()); $$;

create table if not exists public.sources (
  id uuid primary key default gen_random_uuid(),
  platform text not null check (platform in ('telegram','instagram','website')),
  external_source_id text not null,
  title text,
  source_type text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  unique(platform, external_source_id)
);

create table if not exists public.chat_members (
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

create table if not exists public.messages (
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
create index if not exists messages_source_sent_at_idx on public.messages(source_id, sent_at desc);
create index if not exists messages_member_sent_at_idx on public.messages(member_id, sent_at desc);
create index if not exists messages_reply_idx on public.messages(source_id, reply_to_external_message_id);

create table if not exists public.request_classifications (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.messages(id) on delete cascade,
  is_customer_request boolean not null default false,
  topic text,
  intent text,
  confidence numeric(4,3),
  request_group_key text,
  classified_at timestamptz not null default now(),
  unique(message_id)
);

create table if not exists public.exclusions (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources(id) on delete cascade,
  external_user_id text not null,
  exclusion_type text not null check (exclusion_type in ('staff','bot','other')),
  note text,
  created_at timestamptz not null default now(),
  unique(source_id, external_user_id)
);

create table if not exists public.publication_metrics_snapshots (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.messages(id) on delete cascade,
  captured_at timestamptz not null default now(),
  views_count bigint,
  forwards_count bigint,
  reactions jsonb not null default '{}'::jsonb
);
create index if not exists publication_snapshots_message_time_idx on public.publication_metrics_snapshots(message_id, captured_at desc);

alter table public.app_access enable row level security;
alter table public.sources enable row level security;
alter table public.chat_members enable row level security;
alter table public.messages enable row level security;
alter table public.request_classifications enable row level security;
alter table public.exclusions enable row level security;
alter table public.publication_metrics_snapshots enable row level security;

-- The owner row is inserted manually after the first successful Google sign-in.
create policy "owner reads app access" on public.app_access for select to authenticated using (user_id = auth.uid());
create policy "owner reads sources" on public.sources for all to authenticated using (public.is_app_owner()) with check (public.is_app_owner());
create policy "owner reads members" on public.chat_members for all to authenticated using (public.is_app_owner()) with check (public.is_app_owner());
create policy "owner reads messages" on public.messages for all to authenticated using (public.is_app_owner()) with check (public.is_app_owner());
create policy "owner reads classifications" on public.request_classifications for all to authenticated using (public.is_app_owner()) with check (public.is_app_owner());
create policy "owner manages exclusions" on public.exclusions for all to authenticated using (public.is_app_owner()) with check (public.is_app_owner());
create policy "owner reads snapshots" on public.publication_metrics_snapshots for all to authenticated using (public.is_app_owner()) with check (public.is_app_owner());

grant select on public.app_access to authenticated;
grant all on public.sources, public.chat_members, public.messages, public.request_classifications, public.exclusions, public.publication_metrics_snapshots to authenticated;