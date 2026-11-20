# YECHIM Analytics

Закрытая аналитическая платформа маркетинга YECHIM. Первый источник — Telegram Supergroup; Instagram подключается отдельным модулем позже.

## Зафиксированная архитектура
- GitHub-репозиторий: Private — хранит исходный код.
- Приложение: Next.js App Router, локальный запуск на личном компьютере; публичный хостинг не используется.
- Доступ: один владелец — 
- Авторизация: Supabase Auth, email + пароль; публичной регистрации нет.
- База данных: Supabase PostgreSQL + Row Level Security.
- Telegram: отдельный серверный/локальный collector на Python + Telethon.
- Instagram: будущая интеграция через официальный Meta Graph API.

## Локальный запуск
1. Установить Node.js 20 или новее.
2. Скопировать `.env.example` в `.env.local`.
3. Заполнить Supabase URL и publishable key.
4. Установить зависимости: `npm install`.
5. Запустить приложение: `npm run dev`.
6. Открыть `http://localhost:3000` и войти через email + пароль.

## Настройки доступа
- В Supabase Auth создан подтверждённый пользователь 
- Его UUID добавлен в `public.app_access`.
- В локальном окружении установить `ALLOWED_EMAIL=yechim.tashkent@gmail.com`.
- В Supabase оставить включённым Email provider. Google OAuth не требуется.
- Не включать публичную регистрацию.
- Все аналитические таблицы защищены RLS. Не помещать service-role key в браузер или Git.

## Supabase
- Project ref: `nhdxtixwkysvskdpahxi`.
- Region: `ap-southeast-2`.
- URL: `https://nhdxtixwkysvskdpahxi.supabase.co`.
- Первичная миграция: `supabase/migrations/0001_initial_schema.sql`.
- Основные таблицы: `app_access`, `sources`, `chat_members`, `messages`, `request_classifications`, `exclusions`, `publication_metrics_snapshots`.

## Telegram data collection
- Начальный период импорта: 2026-01-01 — 2026-11-20 (включительно, локальное время чата).
- Исключать сотрудников и ботов по стабильным Telegram user ID, не по username.
- Публикации компании сохранять для аналитики публикаций, даже если автор — сотрудник.
- Считать отдельно все сообщения клиентов и классифицированные клиентские запросы.
- Сохранять message ID, user ID, timestamp, reply/thread links, реакции и доступные просмотры.
- Если исторические просмотры недоступны, хранить NULL, а не ноль.
- Импорт должен быть возобновляемым и идемпотентным.

## Безопасность
Не коммитить `.env.local`, Telegram `.session` файлы, API hash, пароли, Supabase service-role key и выгрузки клиентской переписки. Секреты хранить только локально или в защищённом хранилище сервера.

## Структура
- `src/app` — интерфейс Next.js.
- `src/lib/supabase` — клиенты Supabase.
- `src/middleware.ts` — проверка сессии и разрешённого email.
- `supabase/migrations` — SQL-схема и RLS.
- `docs/` — документация коллектора и словарь данных.
