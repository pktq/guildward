"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import type { ReactNode } from "react";
import { api, ApiError } from "@/lib/dashboard/api";
import type { Demo } from "@/lib/dashboard/api";
import { t as translate } from "@/lib/dashboard/i18n";
import type { Lang } from "@/lib/dashboard/i18n";
import { prefersLight, subscribeLight, themeStore } from "@/lib/dashboard/prefs";
import type { Me } from "@/lib/dashboard/types";
import { DashContext, makeFmt, useDash } from "./context";
import type { Dash } from "./context";
import { ShieldMark } from "@/components/site/ShieldMark";
import { Avatar, ErrorView, Icon } from "./ui";

type Toast = { id: number; msg: string; kind?: "error"; out?: boolean };
type Confirm = { title: string; body: string; ok: string; resolve: (ok: boolean) => void };

export function DashShell({ children }: { children: ReactNode }) {
  const params = useSearchParams();
  const pathname = usePathname();
  const demoParam = params.get("demo");
  const demo: Demo = demoParam == null ? null : demoParam === "signin" ? "signin" : "on";

  // ---- preferences
  const theme = useSyncExternalStore(themeStore.subscribe, themeStore.get, () => null);
  const lightPref = useSyncExternalStore(subscribeLight, prefersLight, () => false);
  const dark = theme === "light" || theme === "dark" ? theme === "dark" : !lightPref;

  // ---- session
  const [meRes, setMeRes] = useState<{ me?: Me; error?: ApiError; key: string } | null>(null);
  const [meNonce, setMeNonce] = useState(0);
  const [signedOut, setSignedOut] = useState(false);
  const meKey = demo ?? "";
  const me = meRes && meRes.key === meKey ? meRes.me ?? null : null;
  const meError = meRes && meRes.key === meKey ? meRes.error : undefined;

  // shortcut: English only for now (Swedish strings stay in i18n.ts); bring back a language switch when Swedish returns.
  const lang: Lang = "en";
  const tr = useCallback((key: string, vars?: Record<string, string | number | null | undefined>) => translate(lang, key, vars), [lang]);

  const langRef = useRef(lang);
  useEffect(() => { langRef.current = lang; });

  useEffect(() => {
    let alive = true;
    api<Me>("GET", "/api/me", undefined, demo, langRef.current).then(
      (m) => { if (alive) { setSignedOut(false); setMeRes({ me: m, key: meKey }); } },
      (e) => {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 401) setSignedOut(true);
        else setMeRes({ error: e instanceof ApiError ? e : new ApiError(-1, ""), key: meKey });
      },
    );
    return () => { alive = false; };
  }, [demo, meKey, meNonce]);

  // ---- toasts + confirm dialog
  const [toasts, setToasts] = useState<Toast[]>([]);
  const toastId = useRef(0);
  const toast = useCallback((msg: string, kind?: "error") => {
    const id = ++toastId.current;
    setToasts((l) => [...l, { id, msg, kind }]);
    setTimeout(() => setToasts((l) => l.map((x) => (x.id === id ? { ...x, out: true } : x))), kind === "error" ? 6000 : 3500);
    setTimeout(() => setToasts((l) => l.filter((x) => x.id !== id)), (kind === "error" ? 6000 : 3500) + 250);
  }, []);

  const [dlg, setDlg] = useState<Confirm | null>(null);
  const dlgRef = useRef<HTMLDialogElement>(null);
  const confirm = useCallback((title: string, body: string, ok: string) => new Promise<boolean>((resolve) => setDlg({ title, body, ok, resolve })), []);
  useEffect(() => {
    const d = dlgRef.current;
    if (dlg && d && !d.open) {
      d.returnValue = "";
      d.showModal();
      d.querySelector<HTMLButtonElement>("[value=cancel]")?.focus();
    }
  }, [dlg]);

  // ---- context value
  const [openAlerts, setOpenAlertsState] = useState<Record<string, number>>({});
  const setOpenAlerts = useCallback((gid: string, u: number | ((n: number) => number)) => {
    setOpenAlertsState((s) => {
      const next = typeof u === "function" ? u(s[gid] ?? 0) : u;
      return s[gid] === next ? s : { ...s, [gid]: next };
    });
  }, []);
  const [guildNames, setGuildNames] = useState<Record<string, string>>({});
  const setGuildName = useCallback((gid: string, name: string) => setGuildNames((s) => (s[gid] === name ? s : { ...s, [gid]: name })), []);

  const unauthorized = useCallback(() => setSignedOut(true), []);
  const call = useCallback(
    <T,>(method: "GET" | "POST" | "PUT", path: string, body?: unknown) => api<T>(method, path, body, demo, lang),
    [demo, lang],
  );
  const fail = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.status === 401) { setSignedOut(true); return; }
    toast((e instanceof Error && e.message) || tr("errTitle"), "error");
  }, [toast, tr]);
  const href = useCallback((path: string) => {
    if (!demo) return path;
    const [p, q = ""] = path.split("?");
    return `${p}?${q ? q + "&" : ""}${demo === "signin" ? "demo=signin" : "demo"}`;
  }, [demo]);

  const f = useMemo(() => makeFmt(lang), [lang]);
  const ctx: Dash = {
    lang, t: tr, f, demo, me, href, call, fail, unauthorized, toast, confirm,
    openAlerts, setOpenAlerts, guildNames, setGuildName,
  };

  // Move focus to the content on in-app navigation (not on first load).
  const mainRef = useRef<HTMLElement>(null);
  const lastPath = useRef(pathname);
  useEffect(() => {
    if (lastPath.current !== pathname) { lastPath.current = pathname; mainRef.current?.focus({ preventScroll: true }); }
  }, [pathname]);

  const toggleTheme = () => themeStore.set(dark ? "light" : "dark");
  const logout = () => {
    api("POST", "/api/logout", {}, demo, lang).catch(() => {}).then(() => { setSignedOut(true); toast(tr("signedOut")); });
  };

  let body: ReactNode;
  if (signedOut) body = <SignIn demo={demo} lang={lang} />;
  else if (meError) body = <ErrorView msg={meError.message || tr("errNetwork")} retry={() => { setMeRes(null); setMeNonce((n) => n + 1); }} />;
  else if (!me) body = <div className="skeleton" aria-busy="true"><div className="sk sk-h" /></div>;
  else body = children;

  return (
    <DashContext.Provider value={ctx}>
      <div className={`gw-dash${signedOut ? " signed-out" : ""}`} data-theme={theme === "light" || theme === "dark" ? theme : undefined} lang={lang}>
        <a className="skip" href="#main">{tr("skip")}</a>
        <div className="app">
          <aside className="side" id="side">
            {!signedOut && me && <Sidebar me={me} pathname={pathname} dark={dark} toggleTheme={toggleTheme} logout={logout} />}
          </aside>
          <main className="main" id="main" tabIndex={-1} ref={mainRef}>{body}</main>
        </div>
        <dialog
          ref={dlgRef} className="dialog" aria-labelledby="confirm-title" aria-describedby="confirm-body"
          onClose={() => { dlg?.resolve(dlgRef.current?.returnValue === "ok"); setDlg(null); }}
        >
          <form method="dialog">
            <h2 id="confirm-title">{dlg?.title}</h2>
            <p id="confirm-body">{dlg?.body}</p>
            <div className="dialog-actions">
              <button className="btn" value="cancel">{tr("cancel")}</button>
              <button className="btn btn-danger" value="ok">{dlg?.ok}</button>
            </div>
          </form>
        </dialog>
        <div className="toasts" role="status" aria-live="polite">
          {toasts.map((x) => <div key={x.id} className={`toast${x.kind === "error" ? " toast-error" : ""}${x.out ? " is-out" : ""}`}>{x.msg}</div>)}
        </div>
      </div>
    </DashContext.Provider>
  );
}

// Discord's own mark, as Discord asks sign-in buttons to show it.

const DISCORD_PATH = "M20.317 4.37a19.79 19.79 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.865-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.74 19.74 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.873-1.295 1.226-1.994a.076.076 0 0 0-.042-.106 13.1 13.1 0 0 1-1.872-.892.077.077 0 0 1-.008-.128c.126-.094.252-.192.372-.291a.074.074 0 0 1 .078-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.009c.12.1.246.198.373.292a.077.077 0 0 1-.007.128 12.3 12.3 0 0 1-1.873.891.077.077 0 0 0-.041.107c.36.698.772 1.363 1.225 1.993a.076.076 0 0 0 .084.029 19.84 19.84 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.331c-1.183 0-2.157-1.086-2.157-2.42 0-1.333.956-2.418 2.157-2.418 1.21 0 2.176 1.095 2.157 2.419 0 1.333-.956 2.419-2.157 2.419zm7.975 0c-1.183 0-2.157-1.086-2.157-2.42 0-1.333.955-2.418 2.157-2.418 1.21 0 2.176 1.095 2.157 2.419 0 1.333-.946 2.419-2.157 2.419z";



function SignIn({ demo, lang }: { demo: Demo; lang: Lang }) {
  const t = (k: string, v?: Record<string, string>) => translate(lang, k, v);
  const pathname = usePathname();
  const params = useSearchParams();
  // Come back to the page that asked for sign-in. The API only accepts /dashboard paths.
  const q = params.toString();
  const next = pathname.startsWith("/dashboard") ? pathname + (q ? "?" + q : "") : "/dashboard";
  const discordHref = demo ? "/dashboard/g/10?demo" : `/auth/discord?next=${encodeURIComponent(next)}`;
  const [before, after] = t("signinOr", { cmd: "\u0000" }).split("\u0000");
  return (
    <div className="signin">
      <header className="signin-top">
        <Link href="/" className="brand">
          <ShieldMark size={26} />
          <span className="brand-text"><b>Guildward</b> <span>{t("brandSub")}</span></span>
        </Link>
      </header>
      <div className="signin-center">
        <section className="signin-card" aria-labelledby="signin-title">
          <ShieldMark size={44} className="signin-mark" />
          <h1 id="signin-title">{t("signinTitle")}</h1>
          <p className="signin-who">{t("signinWho")}</p>
          {/* A full navigation, not <Link>: the API answers with a redirect to discord.com. */}
          <a className="btn btn-discord" href={discordHref}>
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d={DISCORD_PATH} /></svg>
            {t("signinDiscord")}
          </a>
          <p className="signin-or"><span>{t("signinOrWord")}</span></p>
          <p className="signin-alt">{before}<code>/guard dashboard</code>{after}</p>
        </section>
        {!demo && <Link className="signin-demo" href="/dashboard/g/10?demo">{t("signinDemo")}</Link>}
      </div>
    </div>
  );
}

function Sidebar({ me, pathname, dark, toggleTheme, logout }: {
  me: Me; pathname: string; dark: boolean; toggleTheme: () => void; logout: () => void;
}) {
  const { t, href, demo, openAlerts, guildNames } = useDash();
  const router = useRouter();
  const parts = pathname.split("/").filter(Boolean); // dashboard, g, <gid>, <key>, ...
  const gid = parts[1] === "g" ? decodeURIComponent(parts[2] ?? "") || null : null;
  const key = parts[1] === "owner" ? "owner" : gid ? parts[3] || "overview" : "";
  const guilds = me.guilds;
  const g = guilds.find((x) => x.id === gid);
  const count = gid ? openAlerts[gid] : 0;
  const base = gid ? `/dashboard/g/${encodeURIComponent(gid)}` : "";
  const link = (sub: string, k: string, ic: string, label: string, extra?: ReactNode) => (
    <Link href={href(base + (sub ? "/" + sub : ""))} className="nav-link" aria-current={key === k ? "page" : undefined}>
      <Icon name={ic} /><span>{label}</span>{extra}
    </Link>
  );
  return (
    <>
      <div className="brand">
        <Icon name="shield" className="brand-mark" />
        <span className="brand-text"><b>Guildward</b> <span>{t("brandSub")}</span></span>
        {demo && <span className="chip chip-demo">{t("demo")}</span>}
      </div>
      {gid ? (
        <>
          <div className="guild-box">
            {guilds.length > 1 ? (
              <>
                <label className="sr" htmlFor="guild-switch">{t("server")}</label>
                <select id="guild-switch" className="guild-switch" value={gid} onChange={(e) => router.push(href(`/dashboard/g/${encodeURIComponent(e.target.value)}`))}>
                  {guilds.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
                  {!g && <option value={gid}>{gid}</option>}
                </select>
              </>
            ) : <div className="guild-name">{g ? g.name : guildNames[gid] ?? ""}</div>}
            {g && !me.owner && g.level !== "admin" && <span className="chip chip-access">{t("acc_" + g.level)}</span>}
          </div>
          <nav className="nav" aria-label={t("nav")}>
            {link("", "overview", "grid", t("overview"))}
            {link("alerts", "alerts", "bell", t("alerts"), count ? <span className="badge num" aria-label={`${count} ${t("f_open")}`}>{count}</span> : null)}
            {link("members", "members", "users", t("members"))}
            {link("settings", "settings", "sliders", t("settings"))}
            {link("report", "report", "doc", t("report"))}
          </nav>
        </>
      ) : guilds.length ? (
        <nav className="nav" aria-label={t("nav")}>
          {guilds.map((x) => (
            <Link key={x.id} className="nav-link" href={href(`/dashboard/g/${encodeURIComponent(x.id)}`)}><Icon name="grid" /><span>{x.name}</span></Link>
          ))}
        </nav>
      ) : null}
      {me.owner && (
        <nav className="nav nav-owner" aria-label={t("owner")}>
          <Link href={href("/dashboard/owner")} className="nav-link" aria-current={key === "owner" ? "page" : undefined}><Icon name="server" /><span>{t("owner")}</span></Link>
        </nav>
      )}
      <div className="side-foot">
        <div className="prefs">
          <button type="button" className="icon-btn" onClick={toggleTheme} aria-label={`${t("theme")}: ${t(dark ? "dark" : "light")}`} title={t("theme")}>
            <Icon name={dark ? "moon" : "sun"} />
          </button>
        </div>
        <div className="me">
          <Avatar name={me.user.name} /><span className="me-name">{me.user.name}</span>
          <button type="button" className="icon-btn" onClick={logout} aria-label={t("logout")} title={t("logout")}><Icon name="logout" /></button>
        </div>
      </div>
    </>
  );
}
