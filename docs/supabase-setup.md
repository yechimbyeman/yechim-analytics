# Supabase and Google sign-in setup

1. Create a Supabase project in the correct company-owned workspace.
2. Open SQL Editor and run `supabase/migrations/0001_initial_schema.sql`.
3. In Authentication > Providers, enable Google.
4. Create an OAuth client in Google Cloud. Add the Supabase callback URL shown in the Supabase Google provider settings to the Google OAuth client's authorized redirect URIs.
5. Copy the Google Client ID and Client Secret into the Supabase Google provider settings. Do not put the Google Client Secret in GitHub or a NEXT_PUBLIC variable.
6. In Supabase Authentication URL Configuration, add the local callback `http://localhost:3000/auth/callback` and the eventual production callback `https://YOUR-PRIVATE-APP-DOMAIN/auth/callback`.
7. Set the application environment variables in the local environment and deployment host: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `ALLOWED_EMAIL`.
8. Sign in once with the intended Google account. In Authentication > Users, copy that user's UUID.
9. In SQL Editor, grant the single account access:

```sql
insert into public.app_access (user_id)
values ('PASTE-AUTH-USER-UUID-HERE')
on conflict (user_id) do nothing;
```

10. Test that the approved account can open /dashboard and a different Google account is redirected to /login?error=unauthorized.

The Supabase anon/publishable key is intended for browser use when RLS is correctly enabled. Never expose the service-role key. Keep the Telegram API hash and Telethon session on the server-side collector only.
