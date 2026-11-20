# YECHIM Analytics

Закрытая аналитическая платформа маркетинга YECHIM. Первый источник — Telegram Supergroup; Instagram подключается отдельным модулем на следующем этапе.

## Принятые решения
- GitHub repository: Private.
- Доступ к приложению: один разрешённый пользователь.
- Авторизация: Google OAuth через Supabase Auth.
- База данных: Supabase PostgreSQL + Row Level Security.
- Веб-приложение: Next.js App Router.
- Telegram: исторический импорт и последующий сбор новых сообщений через серверный collector.
- Instagram: будущая интеграция через официальный Meta Graph API.

## Локальный запуск
1. Node.js 20+.
2. Скопировать `.env.example` в `.env.local` и заполнить параметры Supabase.
3. Выполнить `supabase/schema.sql` в Supabase SQL Editor.
4. Включить Google provider в Supabase Auth и настроить OAuth client в Google Cloud.
5. Добавить `http://localhost:3000/auth/callback` в Supabase redirect URLs.
6. Установить `ALLOWED_EMAIL` — email единственного разрешённого Google-аккаунта.
7. Выполнить `npm install`, затем `npm run dev`.

## Безопасность
Не коммитить пароли, API keys, Telegram session-файлы, service-role key и выгрузки переписки клиентов. Репозиторий содержит стартовый каркас, а не подключённую аналитику: реальные данные появятся после настройки Supabase и Telegram collector.

## Структура
- `src/app` — Next.js UI и Google OAuth callback.
- `src/lib/supabase` — клиенты Supabase.
- `src/middleware.ts` — проверка сессии и единственного разрешённого email.
- `supabase/schema.sql` — схема базы и RLS.
- `docs/` — архитектура и словарь данных.
