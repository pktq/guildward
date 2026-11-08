"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/dashboard/api";
import type { Demo } from "@/lib/dashboard/api";
import type { Lang } from "@/lib/dashboard/i18n";
import type { Access, Me } from "@/lib/dashboard/types";
import * as F from "@/lib/dashboard/format";

type Vars = Record<string, string | number | null | undefined>;

export type Fmt = {
  num: (n: number | null | undefined) => string;
  pct: (x: number) => string;
  date: (iso: string | null | undefined, withTime?: boolean) => string;
  day: (isoDay: string) => string;
  rel: (iso: string | null | undefined) => string;
  bytes: (n: number) => string;
};

export type Dash = {
  lang: Lang;
  t: (key: string, vars?: Vars) => string;
  f: Fmt;
  demo: Demo;
  me: Me | null;
  href: (path: string) => string;
  call: <T = unknown>(method: "GET" | "POST" | "PUT", path: string, body?: unknown) => Promise<T>;
  /** Route an error from a user action: 401 shows the sign-in screen, anything else a toast. */
  fail: (e: unknown) => void;
  unauthorized: () => void;
  toast: (msg: string, kind?: "error") => void;
  confirm: (title: string, body: string, okLabel: string) => Promise<boolean>;
  openAlerts: Record<string, number>;
  setOpenAlerts: (gid: string, update: number | ((n: number) => number)) => void;
  guildNames: Record<string, string>;
  setGuildName: (gid: string, name: string) => void;
};

export const DashContext = createContext<Dash | null>(null);

export function useDash(): Dash {
  const c = useContext(DashContext);
  if (!c) throw new Error("useDash outside the dashboard shell");
  return c;
}

const RANK: Record<Access, number> = { view: 0, act: 1, admin: 2 };

/** True when the signed-in user's level in `gid` is at least `need`. The API enforces the same rule. */
export function useCan(gid: string | null | undefined): (need: Access) => boolean {
  const { me } = useDash();
  const level = me?.owner ? "admin" : me?.guilds.find((g) => g.id === gid)?.level;
  return (need) => level != null && RANK[level] >= RANK[need];
}

export function makeFmt(lang: Lang): Fmt {
  return {
    num: (n) => F.num(lang, n),
    pct: (x) => F.pct(lang, x),
    date: (iso, withTime) => F.date(lang, iso, withTime),
    day: (d) => F.day(lang, d),
    rel: (iso) => F.rel(lang, iso),
    bytes: (n) => F.bytes(lang, n),
  };
}

type Res<T> = { key: string; data?: T; error?: ApiError };

/**
 * Load `path` through the dashboard API client. `path = null` skips. Data is only handed back for
 * the current key (unless keepPrevious), `reload()` refetches in place without a loading state.
 */
export function useApi<T>(path: string | null, opts: { keepPrevious?: boolean; onData?: (d: T) => void } = {}) {
  const { call, unauthorized, demo } = useDash();
  const [res, setRes] = useState<Res<T> | null>(null);
  const [nonce, setNonce] = useState(0);
  const key = `${demo ?? ""}|${path}`;
  const onData = useRef(opts.onData);
  useEffect(() => { onData.current = opts.onData; });
  // call/unauthorized are stable per (demo, lang); lang changes must not refetch, so read them via a ref.
  const fns = useRef({ call, unauthorized });
  useEffect(() => { fns.current = { call, unauthorized }; });

  useEffect(() => {
    if (path == null) return;
    let alive = true;
    fns.current.call<T>("GET", path).then(
      (data) => { if (!alive) return; onData.current?.(data); setRes({ key, data }); },
      (e) => {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 401) { fns.current.unauthorized(); return; }
        setRes({ key, error: e instanceof ApiError ? e : new ApiError(-1, "") });
      },
    );
    return () => { alive = false; };
  }, [key, path, nonce]);

  const current = res && res.key === key;
  const shown = current ? res : opts.keepPrevious ? res : null;
  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const mutate = useCallback((fn: (d: T) => T) => {
    setRes((r) => (r && r.data !== undefined ? { ...r, data: fn(r.data) } : r));
  }, []);
  return {
    data: shown?.data,
    error: current ? res?.error : undefined,
    loading: !current && path != null,
    reload,
    mutate,
  };
}
