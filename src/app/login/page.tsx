"use client";
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { LockKeyhole } from "lucide-react";
export default function LoginPage(){
 const [busy,setBusy]=useState(false),[error,setError]=useState("");
 async function signIn(){setBusy(true);setError("");const supabase=createClient();const {error}=await supabase.auth.signInWithOAuth({provider:"google",options:{redirectTo:window.location.origin+"/auth/callback",queryParams:{prompt:"select_account"}}});if(error){setError(error.message);setBusy(false);}}
 return <main className="login-wrap"><section className="login-card"><div className="brand">YECHIM<small>ANALYTICS PLATFORM</small></div><div style={{marginTop:34}}><LockKeyhole size={25}/></div><h1 className="h1">Закрытая аналитика</h1><p className="sub">Войдите через разрешённый Google-аккаунт, чтобы открыть рабочую панель YECHIM.</p><button className="login-btn" onClick={signIn} disabled={busy}>{busy?"Перенаправляем…":"Продолжить с Google"}</button>{error&&<p className="error">{error}</p>}<p className="empty-note">Доступ только для одного заранее разрешённого аккаунта.</p></section></main>;
}