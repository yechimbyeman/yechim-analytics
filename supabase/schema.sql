-- YECHIM Analytics schema. Run once in the Supabase SQL Editor.
create extension if not exists pgcrypto;

create table if not exists public.allowed_users (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  created_at timestamptz not null default now()
);
create table if not exists public.sources (
  id uuid primary key default gen_random_uuid(),
  provider text not null check (provider in ('telegram','instagram','website')),
  external_id text,
  name text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  unique(provider, external_id)
);
create table if not exists public.chat_members (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources(id) on delete cascade,
  external_user_id text not null,
  username text,
  display_name text,
  is_bot boolean not null default false,
  is_internal boolean not null default false,
  first_seen_at timestamptz,
  last_seen_at timestamptz,
  created_at timestamptz not null default now(),
  unique(source_id, external_user_id)
);
create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources(id) on delete cascade,
  external_message_id text not null,
  member_id uuid references public.chat_members(id) on delete set null,
  message_type text not null default 'customer_message'
    check (message_type in ('customer_message','publication','manager_message','bot_message','system')),
  text text,
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
create index if not exists messages_sent_at_idx on public.messages(sent_at desc);
create index if not exists messages_member_sent_idx on public.messages(member_id, sent_at desc);
create index if not exists messages_reply_idx on public.messages(source_id, reply_to_external_message_id);

create table if not exists public.request_classifications (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.messages(id) on delete cascade,
  category text not null,
  intent text,
  is_customer_request boolean not null default false,
  confidence numeric(5,4),
  model_version text,
  created_at timestamptz not null default now(),
  unique(message_id, category, model_version)
);
create table if not exists public.exclusions (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources(id) on delete cascade,
  external_user_id text not null,
  label text,
  reason text,
  created_at timestamptz not null default now(),
  unique(source_id, external_user_id)
);
create table if not exists public.publication_metrics_snapshots (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.messages(id) on delete cascade,
  captured_at timestamptz not null default now(),
  views_count bigint,
  reactions jsonb not null default '{}'::jsonb,
  forwards_count bigint
);

alter table public.allowed_users enable row level security;
alter table public.sources enable row level security;
alter table public.chat_members enable row level security;
alter table public.messages enable row level security;
alter table public.request_classifications enable row level security;
alter table public.exclusions enable row level security;
alter table public.publication_metrics_snapshots enable row level security;

create policy "owner reads own allowlist row" on public.allowed_users
  for select to authenticated using (user_id = auth.uid());
create policy "owner manages own allowlist row" on public.allowed_users
  for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

do $$
declare t text;
begin
  foreach t in array array['sources','chat_members','messages','request_classifications','exclusions','publication_metrics_snapshots']
  loop
    execute format(
      'create policy "allowlisted owner full access" on public.%I for all to authenticated using (exists (select 1 from public.allowed_users a where a.user_id = auth.uid())) with check (exists (select 1 from public.allowed_users a where a.user_id = auth.uid()))',
      t
    );
  end loop;
end $$;

-- After the first successful Google login, add the owner using the exact auth.users
-- UUID and email from Supabase Authentication > Users:
-- insert into public.allowed_users (user_id, email) values ('YOUR-AUTH-USER-UUID', 'YOUR-GOOGLE-EMAIL');
-- Never expose the Supabase service-role key in browser code.
