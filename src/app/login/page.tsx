"use client";
import { FormEvent, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { LockKeyhole, Mail } from "lucide-react";

const BASE = "/yechim-analytics";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const supabase = createClient();
      const { data, error: signInError } = await supabase.auth.signInWithPassword({ email: email.trim().toLowerCase(), password });
      if (signInError) throw signInError;
      const { data: access, error: accessError } = await supabase.from("app_access").select("user_id").eq("user_id", data.user.id).maybeSingle();
      if (accessError || !access) {
        await supabase.auth.signOut();
        throw new Error("У этого аккаунта нет разрешения на доступ к YECHIM Analytics.");
      }
      window.location.assign(`${BASE}/dashboard/`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось выполнить вход."); setBusy(false);
    }
  }
  return <main className="login-wrap"><section className="login-card">
    <div className="brand">YECHIM<small>ANALYTICS PLATFORM</small></div><div style={{marginTop:34}}><LockKeyhole size={25}/></div>
    <h1 className="h1">Закрытая аналитика</h1><p className="sub">Войдите по email и паролю, чтобы открыть рабочую панель YECHIM.</p>
    <form onSubmit={signIn}><label className="login-label" htmlFor="email">Email</label><div className="login-input-wrap"><Mail size={16}/><input id="email" className="login-input" type="email" autoComplete="username" required value={email} onChange={e=>setEmail(e.target.value)} placeholder="name@example.com"/></div>
      <label className="login-label" htmlFor="password">Пароль</label><input id="password" className="login-input password-input" type="password" autoComplete="current-password" required value={password} onChange={e=>setPassword(e.target.value)} placeholder="Введите пароль"/>
      <button className="login-btn" type="submit" disabled={busy}>{busy ? "Входим…" : "Войти"}</button>
    </form>
    {error && <p className="error" role="alert">{error}</p>}<p className="empty-note">Доступ только для одного заранее разрешённого аккаунта. Самостоятельная регистрация отключена.</p>
  </section></main>;
}
