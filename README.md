# YECHIM Analytics

Закрытая аналитическая платформа маркетинга YECHIM. Первый источник — Telegram Supergroup; Instagram подключается отдельным модулем позже.

## Зафиксированные решения
- Репозиторий GitHub: Private.
- Доступ к приложению: один разрешённый пользователь (yechim.tashkent@gmail.com).
- Авторизация: email + пароль через Supabase Auth; единственный владелец — `yechim.tashkent@gmail.com`.
- База данных: Supabase PostgreSQL + Row Level Security.
- Веб-приложение: Next.js App Router, запускается локально на личном компьютере; публичный хостинг не используется.
- Telegram: импорт истории и последующий сбор новых сообщений через серверный collector.
- Instagram: будущая интеграция через официальный Meta Graph API.

## Локальный запуск
1. Использовать Node.js 20+.
2. Скопировать `.env.example` в `.env.local` и заполнить параметры Supabase.
3. Выполнить миграцию `supabase/migrations/0001_initial_schema.sql` в Supabase SQL Editor.
4. В Supabase Auth оставить включённым Email provider; Google OAuth не требуется.
5. Установить `ALLOWED_EMAIL=yechim.tashkent@gmail.com`.
6. Убедиться, что пользователь создан в Supabase Auth и его UUID добавлен в `public.app_access`.
7. Выполнить `npm install`, затем `npm run dev`.

## Безопасность
Не коммитить пароли, API keys, Telegram session-файлы, Supabase service-role key и выгрузки переписки клиентов. Middleware и серверная страница проверяют единственный разрешённый email; RLS дополнительно ограничивает доступ к аналитическим таблицам. Реальные данные появятся после настройки Supabase и Telegram collector.

## Структура
- `src/app` — Next.js интерфейс и авторизация email/password.
- `src/lib/supabase` — клиенты Supabase.
- `src/middleware.ts` — проверка сессии и разрешённого email.
- `supabase/migrations` — схема базы данных и RLS.
- `docs/` — архитектура и словарь данных.


## Current Supabase project
- Project ref: `nhdxtixwkysvskdpahxi` (region `ap-southeast-2`).
- Project URL: `https://nhdxtixwkysvskdpahxi.supabase.co`.
- The initial schema has been applied and verified: 7 public tables, all with RLS enabled.
- The `rls_auto_enable()` event-trigger function was inspected; direct execution by `anon` and `authenticated` was revoked. The Supabase security advisor then returned no findings.
- Set `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` from Supabase API Keys and `ALLOWED_EMAIL` to the one Google email permitted to use the dashboard.


## Авторизация (email + пароль)
- Вход выполняется через Supabase Auth `signInWithPassword`; Google OAuth для входа не нужен.
- Публичной регистрации в приложении нет. Единственный пользователь создаётся владельцем в Supabase Dashboard → Authentication → Users.
- Middleware разрешает только `yechim.tashkent@gmail.com` (или значение `ALLOWED_EMAIL` в окружении деплоя).
- После создания пользователя добавьте его UUID в `public.app_access`, чтобы открыть доступ к аналитическим таблицам по RLS:

```sql
insert into public.app_access(user_id)
select id from auth.users where email = 'yechim.tashkent@gmail.com'
on conflict (user_id) do nothing;
```
- Оставьте Email provider включённым в Supabase Auth. Google OAuth больше не требуется для приложения.
