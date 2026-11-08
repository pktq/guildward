/* eslint-disable @typescript-eslint/no-explicit-any */
import { t } from "./i18n";
import type { Lang } from "./i18n";
import type { Account, MemberReport, MemberRow } from "./types";

/** null = live API; "on" = fixtures from /demo/*.json; "signin" = demo that shows the sign-in screen. */
export type Demo = null | "on" | "signin";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Same-origin: next.config rewrites /api/* to the Guard API, so the HttpOnly session cookie rides along.
export async function api<T = any>(method: "GET" | "POST" | "PUT", path: string, body?: unknown, demo: Demo = null, lang: Lang = "en"): Promise<T> {
  if (demo) return demoApi(method, path, body as any, demo, lang) as Promise<T>;
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") {
    headers["X-Guildward"] = "1";
    headers["Content-Type"] = "application/json";
  }
  let r: Response;
  try {
    r = await fetch(path, { method, credentials: "same-origin", headers, body: method === "GET" ? undefined : JSON.stringify(body ?? {}) });
  } catch {
    throw new ApiError(0, t(lang, "errNetwork"));
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.ok === false) throw new ApiError(r.status, data.error || "");
  return data as T;
}

// ---------------------------------------------------------------- demo mode (fixtures, mutations kept in memory)
const demoCache: Record<string, Promise<any>> = {};

function fixture(name: string, lang: Lang): Promise<any> {
  if (!demoCache[name]) {
    demoCache[name] = fetch(`/demo/${name}.json`).then((r) => {
      if (!r.ok) throw new ApiError(404, t(lang, "errNotFound"));
      return r.json();
    });
  }
  return demoCache[name];
}
const clone = <T,>(o: T): T => JSON.parse(JSON.stringify(o));

export function splitName(name?: string | null) {
  const m = /^(.*) \((@[^)]+)\)$/.exec(name || "");
  return m ? { display: m[1].trim() || m[2], handle: m[2] } : { display: name || "?", handle: "" };
}

export function accIn(a: Account, st: string) {
  if (st === "all") return true;
  if (st === "review") return (a.auto_flag === "watch" || a.auto_flag === "flagged") && a.flag !== "confirmed" && a.flag !== "cleared";
  return a.flag === st;
}
function accCounts(list: Account[]) {
  const c: Record<string, number> = {};
  for (const k of ["review", "flagged", "confirmed", "cleared"]) c[k] = list.filter((a) => accIn(a, k)).length;
  return c;
}

async function demoApi(method: string, path: string, body: any, demo: Demo, lang: Lang): Promise<any> {
  const u = new URL(path, "http://demo.local"), p = u.pathname, q = u.searchParams;
  let m: RegExpExecArray | null;
  const fx = (n: string) => fixture(n, lang);
  const answer = async (promise: Promise<any>) => {
    const [r] = await Promise.all([promise, new Promise((res) => setTimeout(res, 120))]);
    return clone(r);
  };
  if (p === "/api/public/auth") return answer(Promise.resolve({ discord: true, link: true }));
  if (demo === "signin" && p !== "/api/logout") throw new ApiError(401, "");
  if (p === "/api/me") return answer(fx("me"));
  if (p === "/api/logout") return answer(Promise.resolve({ ok: true }));
  if ((m = /^\/api\/guilds\/(\w+)\/overview$/.exec(p))) {
    const og = m[1];
    // One overview fixture serves every demo guild; borrow the switched-to guild's name from me.json.
    return answer(Promise.all([fx("overview"), fx("me")]).then(([ov, me]) => {
      const g = me.guilds.find((x: any) => x.id === og);
      if (og === ov.guild.id || !g) return ov;
      const o = clone(ov);
      o.guild.id = g.id;
      o.guild.name = g.name;
      return o;
    }));
  }
  if (/^\/api\/guilds\/(\w+)\/fix$/.test(p)) {
    return answer(fx("overview").then((o) => {
      o.audit.forEach((a: any) => { if (a.fix === body.fix) { a.ok = true; a.fix = null; } });
      o.recommendations = o.recommendations.filter((r: any) => r.fix !== body.fix);
      o.health.score = Math.max(0, o.health.score - 4);
      return { ok: true, text: `Applied: ${body.fix} (demo).` };
    }));
  }
  if (/^\/api\/guilds\/(\w+)\/alerts$/.test(p)) {
    return answer(fx("alerts").then((d) => {
      let list = d.alerts;
      if (q.get("status") !== "all") list = list.filter((a: any) => a.status === "open");
      return { alerts: list.slice(0, +(q.get("limit") || 50)) };
    }));
  }
  if ((m = /^\/api\/guilds\/(\w+)\/alerts\/(\w+)$/.exec(p))) {
    const id = +m[2];
    return answer(Promise.all([fx("alerts"), fx("overview"), fx("me")]).then(([al, ov, me]) => {
      const a = al.alerts.find((x: any) => x.id === id);
      if (!a) throw new ApiError(404, t(lang, "errNotFound"));
      if (body.action === "claim" || body.action === "unclaim") {
        if (a.status !== "open") throw new ApiError(409, "This alert is already closed.");
        if (body.action === "claim" && a.assigned && a.assigned.id !== me.user.id) throw new ApiError(409, `${a.assigned.name} is already on this alert.`);
        a.assigned = body.action === "claim" ? { id: me.user.id, name: me.user.name, avatar: null } : null;
      } else if (body.action !== "watch") {
        a.status = body.action === "false_positive" ? "false_positive" : "resolved";
        a.resolved_by = me.user.name;
        a.action = body.action;
        if (typeof body.note === "string" && body.note.trim()) a.note = body.note.trim().slice(0, 500);
      }
      ov.recent_alerts = ov.recent_alerts.map((x: any) => (x.id === id ? a : x));
      ov.kpis.open_alerts = al.alerts.filter((x: any) => x.status === "open").length;
      return { ok: true, alert: a };
    }));
  }
  if (/^\/api\/guilds\/(\w+)\/members$/.test(p)) {
    return answer(fx("members").then((d) => {
      const f = q.get("filter") || "all", s = q.get("sort") || "risk", term = (q.get("q") || "").toLowerCase();
      const rows: MemberRow[] = d.members.filter((r: MemberRow) => {
        if (f === "at_risk" && r.level === "green") return false;
        if (f === "minors" && !r.minor) return false;
        if (f === "watch" && r.status !== "watch") return false;
        if (f === "new" && !(r.account_age_days <= 30 || Date.now() - new Date(r.joined_at || 0).getTime() < 7 * 864e5)) return false;
        return !term || r.name.toLowerCase().includes(term);
      });
      rows.sort(s === "name" ? (a, b) => a.name.localeCompare(b.name)
        : s === "recent" ? (a, b) => ((b.joined_at || "") < (a.joined_at || "") ? -1 : 1)
        : (a, b) => b.score - a.score);
      return { members: rows.slice(0, +(q.get("limit") || 100)), total: d.total };
    }));
  }
  if ((m = /^\/api\/guilds\/(\w+)\/members\/(\w+)$/.exec(p))) {
    const uid = m[2];
    if (method === "GET") {
      // Only a few people have a full fixture; the rest get a thin report built from their member row.
      return answer(fx("member-" + uid).catch(() => {
        delete demoCache["member-" + uid];
        return fx("members").then((d): MemberReport => {
          const row: MemberRow | undefined = d.members.find((x: MemberRow) => x.id === uid);
          if (!row) throw new ApiError(404, t(lang, "errNotFound"));
          return {
            member: Object.assign({ username: splitName(row.name).handle.slice(1), account_created: null, left_at: null, invite_code: null, roles: ["Member"] }, row),
            verdict: {
              score: row.score, level: row.level, confidence: "Demo: only the member list row exists for this person.",
              signals: row.top_signal ? [{ code: "demo.row", weight: row.score, severe: false, text: row.top_signal, at: null }] : [],
            },
            summary: [row.top_signal || "Nothing unusual recorded."],
            prediction: { trajectory: row.trend > 0 ? "rising" : row.trend < 0 ? "falling" : "stable", escalation: "none", text: "Not enough history for a prediction." },
            stats: { messages: 0, flagged: 0, distinct_targets: 0, minor_targets: 0, reports: 0, mod_actions: 0, network_flags: 0 },
            contacts: [], timeline: [], series: { days: [], messages: [], flagged: [] },
          };
        });
      }));
    }
    return answer(fx("members").then((d) => {
      const row = d.members.find((x: MemberRow) => x.id === uid);
      if (!row) throw new ApiError(404, t(lang, "errNotFound"));
      row.status = ({ watch: "watch", trust: "trusted", clear: "none" } as Record<string, string>)[body.action] || "actioned";
      return { ok: true, member: row };
    }));
  }
  if (/^\/api\/guilds\/(\w+)\/settings$/.test(p)) {
    return answer(fx("settings").then((d) => {
      if (method === "PUT") { Object.assign(d.settings, body); return { ok: true, settings: d.settings }; }
      return d;
    }));
  }
  if (p === "/api/owner/overview") return answer(fx("owner-overview"));
  if (p === "/api/owner/accounts") {
    return answer(fx("owner-accounts").then((d) => {
      const st = q.get("status") || "review";
      return { counts: accCounts(d.accounts), accounts: d.accounts.filter((a: Account) => accIn(a, st)) };
    }));
  }
  if ((m = /^\/api\/owner\/accounts\/(\w+)$/.exec(p))) {
    const id = m[1];
    return answer(fx("owner-accounts").then((d) => {
      const a = d.accounts.find((x: Account) => x.id === id);
      if (!a) throw new ApiError(404, t(lang, "errNotFound"));
      a.flag = ({ confirm: "confirmed", clear: "cleared", watch: "watch", reset: a.auto_flag } as Record<string, string>)[body.action] || a.flag;
      return { ok: true };
    }));
  }
  if ((m = /^\/api\/owner\/(network|guilds)\/(\w+)$/.exec(p))) {
    const key = m[1], target = m[2];
    return answer(fx("owner-overview").then((o) => {
      if (key === "network") o.network = o.network.filter((n: any) => n.user.id !== target);
      else o.guilds = o.guilds.filter((g: any) => g.id !== target);
      return { ok: true };
    }));
  }
  throw new ApiError(404, t(lang, "errNotFound"));
}
