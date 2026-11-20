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


## Security and database setup
- Keep the repository private. Never commit .env.local, Telegram .session files, API hashes, OAuth secrets or the Supabase service-role key.
- The application checks ALLOWED_EMAIL; database tables additionally require the authenticated user's UUID in public.app_access.
- Run supabase/migrations/0001_initial_schema.sql in the Supabase SQL Editor. After the first Google login, authorize the owner UUID:

```sql
insert into public.app_access(user_id)
select id from auth.users where email = 'YOUR_ALLOWED_EMAIL'
on conflict (user_id) do nothing;
```

Do not deploy until Google OAuth, the allowlisted email, RLS and HTTPS are configured and tested.