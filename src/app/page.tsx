"use client";
import { useEffect } from "react";
import { createClient } from "@/lib/supabase/client";
export default function Home() {
  useEffect(() => {
    let active = true;
    async function route() {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (!active) return;
      if (!user) { window.location.replace("/yechim-analytics/login/"); return; }
      const { data } = await supabase.from("app_access").select("user_id").eq("user_id", user.id).maybeSingle();
      if (!active) return;
      if (data) window.location.replace("/yechim-analytics/dashboard/");
      else { await supabase.auth.signOut(); window.location.replace("/yechim-analytics/login/?error=unauthorized"); }
    }
    void route();
    return () => { active = false; };
  }, []);
  return <main className="login-wrap"><section className="login-card"><div className="brand">YECHIM<small>ANALYTICS PLATFORM</small></div><h1 className="h1">Открываем аналитику…</h1></section></main>;
}
