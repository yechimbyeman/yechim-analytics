# YECHIM Analytics

Закрытая аналитическая платформа маркетинга YECHIM. Первый источник — Telegram Supergroup; Instagram подключается отдельным модулем позже.

## Зафиксированные решения
- Репозиторий GitHub: Private.
- Доступ к приложению: один разрешённый пользователь.
- Авторизация: Google OAuth через Supabase Auth.
- База данных: Supabase PostgreSQL + Row Level Security.
- Веб-приложение: Next.js App Router.
- Telegram: импорт истории и последующий сбор новых сообщений через серверный collector.
- Instagram: будущая интеграция через официальный Meta Graph API.

## Локальный запуск
1. Использовать Node.js 20+.
2. Скопировать `.env.example` в `.env.local` и заполнить параметры Supabase.
3. Выполнить миграцию `supabase/migrations/0001_initial_schema.sql` в Supabase SQL Editor.
4. Включить Google provider в Supabase Auth и настроить OAuth client в Google Cloud.
5. Добавить `http://localhost:3000/auth/callback` в Supabase redirect URLs.
6. Установить `ALLOWED_EMAIL` — email единственного разрешённого Google-аккаунта.
7. После первого входа добавить UUID этого пользователя в `public.app_access` через Supabase SQL Editor.
8. Выполнить `npm install`, затем `npm run dev`.

## Безопасность
Не коммитить пароли, API keys, Telegram session-файлы, Supabase service-role key и выгрузки переписки клиентов. Middleware и серверный layout проверяют единственный разрешённый email; RLS дополнительно ограничивает доступ к аналитическим таблицам. Реальные данные появятся после настройки Supabase и Telegram collector.

## Структура
- `src/app` — Next.js интерфейс и Google OAuth callback.
- `src/lib/supabase` — клиенты Supabase.
- `src/middleware.ts` — проверка сессии и разрешённого email.
- `supabase/migrations` — схема базы данных и RLS.
- `docs/` — архитектура и словарь данных.
