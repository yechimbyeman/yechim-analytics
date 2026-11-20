import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export default async function Home() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  const allowed = process.env.ALLOWED_EMAIL?.toLowerCase();
  if (!allowed || user.email?.toLowerCase() !== allowed) {
    await supabase.auth.signOut();
    redirect("/login?error=unauthorized");
  }
  redirect("/dashboard");
}
