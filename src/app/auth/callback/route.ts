import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      const { data: { user } } = await supabase.auth.getUser();
      const allowed = process.env.ALLOWED_EMAIL?.toLowerCase();
      if (allowed && user?.email?.toLowerCase() === allowed)
        return NextResponse.redirect(new URL("/dashboard", origin));
      await supabase.auth.signOut();
      return NextResponse.redirect(new URL("/login?error=unauthorized", origin));
    }
  }
  return NextResponse.redirect(new URL("/login?error=oauth", origin));
}
