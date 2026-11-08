"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { splitName } from "@/lib/dashboard/api";
import type { Level, Signal, UserRef } from "@/lib/dashboard/types";
import { useDash } from "./context";

// Authored icons, 24px grid, 1.75 stroke. Level marks use shape as well as colour.
const ICONS: Record<string, string> = {
  shield: "M12 3l7.5 3v5.5c0 4.6-3.1 8.4-7.5 10-4.4-1.6-7.5-5.4-7.5-10V6L12 3z",
  grid: "M4 4h7v7H4zM13 4h7v4h-7zM13 10h7v10h-7zM4 13h7v7H4z",
  bell: "M6 16.5V11a6 6 0 1 1 12 0v5.5l1.5 1.5h-15L6 16.5zM10 20.5a2 2 0 0 0 4 0",
  users: "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20a6.5 6.5 0 0 1 13 0M16 4.3a3.5 3.5 0 0 1 0 6.4M18.5 14.5A6.5 6.5 0 0 1 21.5 20",
  sliders: "M4 7h9M17 7h3M4 17h3M11 17h9M15 5v4M9 15v4",
  doc: "M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6",
  server: "M4 4.5h16v6H4zM4 13.5h16v6H4zM8 7.5h.01M8 16.5h.01",
  logout: "M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10",
  sun: "M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4",
  moon: "M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z",
  up: "M7 17L17 7M9 7h8v8",
  down: "M7 7l10 10M17 9v8H9",
  flat: "M5 12h14M15 8l4 4-4 4",
  ext: "M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5",
  check: "M5 12.5l4.5 4.5L19 7.5",
  claim: "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20a6.5 6.5 0 0 1 13 0M16 11.5l2 2 4-4",
  note: "M5 4h14v11l-5 5H5zM14 20v-5h5M8 9h8M8 12.5h5",
  x: "M6 6l12 12M18 6L6 18",
  warn: "M12 4l9 16H3L12 4zM12 10v4M12 17.2h.01",
  print: "M7 9V3h10v6M7 17H4v-7h16v7h-3M7 14h10v7H7z",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4",
  arrowLeft: "M19 12H5M11 6l-6 6 6 6",
  wrench: "M14.5 6.5a4 4 0 0 0 5 5L12 19a2.1 2.1 0 0 1-3-3l7.5-7.5zM14.5 6.5L17 4l3 3-2.5 2.5",
  lgreen: "M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM8.5 12.3l2.4 2.4 4.6-4.9",
  lyellow: "M12 4.5l8.5 15h-17l8.5-15zM12 10.5v3.5M12 16.8h.01",
  lred: "M8.7 3.5h6.6l5.2 5.2v6.6l-5.2 5.2H8.7l-5.2-5.2V8.7l5.2-5.2zM9.5 9.5l5 5M14.5 9.5l-5 5",
};

export function Icon({ name, className = "" }: { name: string; className?: string }) {
  return (
    <svg className={`ic ${className}`} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d={ICONS[name]} />
    </svg>
  );
}

export function LevelPill({ level, score, short }: { level: Level; score?: number | null; short?: boolean }) {
  const { t } = useDash();
  const label = t("lvl_" + level);
  return (
    <span className={`pill pill-${level}`} title={score != null ? t("riskScore", { n: score }) : label}>
      <Icon name={"l" + level} />
      {score != null && <b className="num">{score}</b>}
      <span className={short ? "sr" : ""}>{label}</span>
    </span>
  );
}

export function Avatar({ name, large }: { name?: string | null; large?: boolean }) {
  const ch = (splitName(name).display.match(/[\p{L}\p{N}]/u) || ["?"])[0].toUpperCase();
  return <span className={`avatar${large ? " avatar-lg" : ""}`} aria-hidden="true">{ch}</span>;
}

export function Who({ user, gid, nolink }: { user: UserRef | null | undefined; gid?: string | null; nolink?: boolean }) {
  const { t, href } = useDash();
  if (!user) return null;
  const n = splitName(user.name);
  const inner = (
    <>
      <Avatar name={user.name} />
      <span className="who-name">
        <span className="who-display">{n.display}</span>
        {n.handle && <> <span className="who-handle">{n.handle}</span></>}
      </span>
      {user.minor && <> <span className="chip chip-minor">{t("fl_minor")}</span></>}
    </>
  );
  if (gid && !nolink) return <Link className="who" href={href(`/dashboard/g/${encodeURIComponent(gid)}/member/${encodeURIComponent(user.id)}`)}>{inner}</Link>;
  return <span className="who">{inner}</span>;
}

const FLAG_TONE: Record<string, string> = { reported: "warn", network: "warn", adult_contacting_minors: "bad", escalating: "bad", raid: "warn", quarantined: "warn", trusted: "good" };

export function FlagChips({ flags }: { flags: string[] }) {
  const { t } = useDash();
  return (
    <>
      {(flags || []).map((f) => (
        <span key={f} className={`chip ${FLAG_TONE[f] ? "chip-" + FLAG_TONE[f] : ""}`}>{t("fl_" + f)}</span>
      ))}
    </>
  );
}

export function Trend({ n }: { n: number }) {
  const { t } = useDash();
  if (!n) {
    return (
      <span className="trend trend-flat" title={t("trendFlat")}>
        <Icon name="flat" /><span className="sr">{t("trendFlat")}</span>0
      </span>
    );
  }
  const up = n > 0;
  const label = t(up ? "trendUp" : "trendDown", { n: Math.abs(n) });
  return (
    <span className={`trend ${up ? "trend-up" : "trend-down"}`} title={label}>
      <Icon name={up ? "up" : "down"} /><span className="sr">{label}</span>{up ? "+" : "−"}{Math.abs(n)}
    </span>
  );
}

export function TimeEl({ iso }: { iso: string | null | undefined }) {
  const { f } = useDash();
  if (!iso) return <>–</>;
  return <time dateTime={iso} title={f.date(iso, true)}>{f.rel(iso)}</time>;
}

export function SignalList({ signals, className = "" }: { signals: Signal[] | undefined; className?: string }) {
  const { t } = useDash();
  if (!signals || !signals.length) return null;
  return (
    <ul className={`signals ${className}`}>
      {signals.map((s, i) => {
        const neg = s.weight < 0;
        return (
          <li key={i} className={`${s.severe ? "is-severe" : ""} ${neg ? "is-good" : ""}`}>
            <span className="sig-w num" title={neg ? t("reassure") : ""}>{s.weight > 0 ? "+" : s.weight < 0 ? "−" : ""}{Math.abs(s.weight)}</span>
            <span className="sig-text">{s.text}</span>
            {s.at && <span className="sig-at"><TimeEl iso={s.at} /></span>}
          </li>
        );
      })}
    </ul>
  );
}

export function Sentences({ list }: { list: string[] | undefined }) {
  return <ul className="sentences">{(list || []).map((s, i) => <li key={i}>{s}</li>)}</ul>;
}

export const Empty = ({ children }: { children: ReactNode }) => <p className="empty">{children}</p>;

export function Panel({ title, id, cls = "", extra, children }: { title: ReactNode; id: string; cls?: string; extra?: ReactNode; children: ReactNode }) {
  return (
    <section className={`panel ${cls}`} aria-labelledby={id}>
      <header className="panel-head"><h2 id={id}>{title}</h2>{extra}</header>
      {children}
    </section>
  );
}

export function Skeleton() {
  const { t } = useDash();
  return (
    <div className="skeleton" aria-busy="true" aria-label={t("loading")}>
      <div className="sk sk-h" />
      <div className="sk-row"><div className="sk sk-b" /><div className="sk sk-b" /></div>
      <div className="sk sk-c" />
    </div>
  );
}

export function ErrorView({ msg, retry }: { msg: string; retry?: () => void }) {
  const { t } = useDash();
  return (
    <div className="state-box">
      <h1>{t("errTitle")}</h1>
      <p>{msg}</p>
      {retry && <button className="btn" type="button" onClick={retry}>{t("retry")}</button>}
    </div>
  );
}

/** Skeleton while loading, error box on failure, otherwise the view. Mirrors the legacy SPA's error mapping. */
export function Async<T>({ res, children }: {
  res: { data?: T; error?: { status: number; message: string }; loading: boolean; reload: () => void };
  children: (data: T) => ReactNode;
}) {
  const { t } = useDash();
  if (res.error) {
    const e = res.error;
    const msg = e.status === 403 ? t("errForbidden") : e.status === 404 ? t("errNotFound") : e.message || t("errTitle");
    return <ErrorView msg={msg} retry={e.status === 403 || e.status === 404 ? undefined : res.reload} />;
  }
  if (res.data === undefined) return <Skeleton />;
  return <>{children(res.data)}</>;
}

export const PageHead = ({ children, action }: { children: ReactNode; action?: ReactNode }) => (
  <header className="page-head"><div>{children}</div>{action}</header>
);
