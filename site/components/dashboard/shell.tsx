"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import type { ReactNode } from "react";
import { api, ApiError } from "@/lib/dashboard/api";
import type { Demo } from "@/lib/dashboard/api";
import { t as translate } from "@/lib/dashboard/i18n";
import type { Lang } from "@/lib/dashboard/i18n";
import { langStore, navLang, noopSubscribe, prefersLight, subscribeLight, themeStore } from "@/lib/dashboard/prefs";
import type { Me } from "@/lib/dashboard/types";
import { DashContext, makeFmt, useDash } from "./context";
import type { Dash } from "./context";
import { Avatar, ErrorView, Icon } from "./ui";

type Toast = { id: number; msg: string; kind?: "error"; out?: boolean };
type Confirm = { title: string; body: string; ok: string; resolve: (ok: boolean) => void };

export function DashShell({ children }: { children: ReactNode }) {
  const params = useSearchParams();
  const pathname = usePathname();
  const demoParam = params.get("demo");
  const demo: Demo = demoParam == null ? null : demoParam === "signin" ? "signin" : "on";

  // ---- preferences
  const chosenLang = useSyncExternalStore(langStore.subscribe, langStore.get, () => null);
  const browserLang = useSyncExternalStore(noopSubscribe, navLang, () => "en");
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

  const langPick = chosenLang === "sv" || chosenLang === "en" ? chosenLang : null;
  const lang: Lang = langPick ?? (me?.lang === "sv" || me?.lang === "en" ? me.lang : browserLang === "sv" ? "sv" : "en");
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

  const setLang = (l: Lang) => langStore.set(l);
  const toggleTheme = () => themeStore.set(dark ? "light" : "dark");
  const logout = () => {
    api("POST", "/api/logout", {}, demo, lang).catch(() => {}).then(() => { setSignedOut(true); toast(tr("signedOut")); });
  };

  let body: ReactNode;
  if (signedOut) body = <SignIn demo={demo} lang={lang} setLang={setLang} />;
  else if (meError) body = <ErrorView msg={meError.message || tr("errNetwork")} retry={() => { setMeRes(null); setMeNonce((n) => n + 1); }} />;
  else if (!me) body = <div className="skeleton" aria-busy="true"><div className="sk sk-h" /></div>;
  else body = children;

  return (
    <DashContext.Provider value={ctx}>
      <div className={`gw-dash${signedOut ? " signed-out" : ""}`} data-theme={theme === "light" || theme === "dark" ? theme : undefined} lang={lang}>
        <a className="skip" href="#main">{tr("skip")}</a>
        <div className="app">
          <aside className="side" id="side">
            {!signedOut && me && <Sidebar me={me} pathname={pathname} lang={lang} setLang={setLang} dark={dark} toggleTheme={toggleTheme} logout={logout} />}
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

function LangSeg({ lang, setLang }: { lang: Lang; setLang: (l: Lang) => void }) {
  return (
    <div className="seg" role="group" aria-label={translate(lang, "language")}>
      {(["en", "sv"] as const).map((l) => (
        <button key={l} type="button" aria-pressed={lang === l} onClick={() => setLang(l)}>{l.toUpperCase()}</button>
      ))}
    </div>
  );
}

function SignIn({ demo, lang, setLang }: { demo: Demo; lang: Lang; setLang: (l: Lang) => void }) {
  const t = (k: string, v?: Record<string, string>) => translate(lang, k, v);
  const [before, after] = t("signinBody", { cmd: "\u0000" }).split("\u0000");
  return (
    <div className="signin">
      <Icon name="shield" className="signin-mark" />
      <h1>{t("signinTitle")}</h1>
      <p>{before}<code>/guard dashboard</code>{after}</p>
      {!demo && <p className="signin-demo"><Link href="/dashboard/g/10?demo">{t("signinDemo")}</Link></p>}
      <LangSeg lang={lang} setLang={setLang} />
    </div>
  );
}

function Sidebar({ me, pathname, lang, setLang, dark, toggleTheme, logout }: {
  me: Me; pathname: string; lang: Lang; setLang: (l: Lang) => void; dark: boolean; toggleTheme: () => void; logout: () => void;
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
          <LangSeg lang={lang} setLang={setLang} />
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
