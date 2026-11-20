-- Private storage for Telegram advertising media and access limited to the YECHIM owner.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('telegram-ad-media', 'telegram-ad-media', false, 52428800, array['image/jpeg','image/png','image/webp','image/gif','video/mp4'])
on conflict (id) do update
set public = false,
    file_size_limit = 52428800,
    allowed_mime_types = excluded.allowed_mime_types;

create policy "YECHIM owner can view Telegram ad media"
on storage.objects for select to authenticated
using (
  bucket_id = 'telegram-ad-media'
  and exists (select 1 from public.app_access a where a.user_id = (select auth.uid()))
);

update public.messages
set permalink = 'https://t.me/c/2100556847/' || external_message_id
where source_id in (
  select id from public.sources
  where platform = 'telegram' and external_source_id = '2100556847'
)
and (message_kind = 'publication' or raw_metadata->>'is_advertising_account' = 'true')
and permalink is null;

create index if not exists messages_grouped_media_idx
on public.messages(source_id, (raw_metadata->>'grouped_id'), sent_at)
where raw_metadata ? 'grouped_id';
