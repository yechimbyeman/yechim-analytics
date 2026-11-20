import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = (process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);
  const path = request.nextUrl.pathname;

  // Fail closed: protected pages must never become public if auth is misconfigured.
  if (!url || !key) {
    if (path === "/login" || path.startsWith("/_next/") || path === "/favicon.ico") return NextResponse.next();
    return NextResponse.redirect(new URL("/login?error=configuration", request.url));
  }

  let response = NextResponse.next({ request });
  const supabase = createServerClient(url, key, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll(values) {
        values.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        values.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      }
    }
  });

  const { data: { user } } = await supabase.auth.getUser();
  const allowed = process.env.ALLOWED_EMAIL?.toLowerCase();
  const isPublicAuthRoute = path === "/login" || path.startsWith("/auth/callback");

  if (!user && !isPublicAuthRoute) return NextResponse.redirect(new URL("/login", request.url));
  if (user && (!allowed || user.email?.toLowerCase() !== allowed)) {
    await supabase.auth.signOut();
    return NextResponse.redirect(new URL("/login?error=unauthorized", request.url));
  }
  if (user && path === "/login") return NextResponse.redirect(new URL("/dashboard", request.url));
  return response;
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
