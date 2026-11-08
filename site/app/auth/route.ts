import { GUARD_API_URL } from "@/lib/guard";

// Sign-in links from `/guard dashboard` point here. The Guard API checks the one-time token and sets
// the session cookie; we pass the cookie through and send the browser to the Next dashboard route
// instead of the legacy SPA's hash route (`/#/g/<gid>` -> `/dashboard/g/<gid>`).
export async function GET(request: Request) {
  const url = new URL(request.url);
  const upstream = await fetch(`${GUARD_API_URL}/auth${url.search}`, {
    redirect: "manual",
    headers: { cookie: request.headers.get("cookie") ?? "" },
    cache: "no-store",
  });
  const location = upstream.headers.get("location");
  if (upstream.status !== 302 || !location) {
    return new Response(await upstream.text(), {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") ?? "text/html; charset=utf-8" },
    });
  }
  const route = location.startsWith("/#/") ? location.slice(2) : "/owner";
  const headers = new Headers({ location: `/dashboard${route}`, "cache-control": "no-store" });
  for (const c of upstream.headers.getSetCookie()) headers.append("set-cookie", c);
  return new Response(null, { status: 302, headers });
}
