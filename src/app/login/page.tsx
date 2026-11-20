"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function signIn() {
    setBusy(true); setError("");
    const supabase = createClient();
    const redirectTo = `${window.location.origin}/auth/callback`;
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo, queryParams: { access_type: "offline", prompt: "consent" } }
    });
    if (error) { setError(error.message); setBusy(false); }
  }
  return <main className="login-shell"><section className="login-card">
    <div className="brand-mark">Y</div><p className="eyebrow">PRIVATE WORKSPACE</p>
    <h1>YECHIM <span>Analytics</span></h1>
    <p className="muted">Закрытая аналитическая платформа маркетинга YECHIM.</p>
    <button className="google-button" onClick={signIn} disabled={busy}>
      <span className="google-g">G</span>{busy ? "Перенаправляем…" : "Войти через Google"}
    </button>
    {error && <p className="error">{error}</p>}
    <p className="login-foot">Доступ только для разрешённого аккаунта.</p>
  </section></main>;
}
