"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { splitName } from "@/lib/dashboard/api";
import { safeUrl } from "@/lib/dashboard/format";
import type { Alert } from "@/lib/dashboard/types";
import { useApi, useDash } from "./context";
import { Async, Empty, Icon, LevelPill, PageHead, SignalList, TimeEl, Who } from "./ui";

export function AlertItem({ a, gid, compact, onUpdate }: { a: Alert; gid: string; compact?: boolean; onUpdate?: (a: Alert) => void }) {
  const { t, call, confirm, toast, fail } = useDash();
  const [busy, setBusy] = useState(false);
  const title = useRef<HTMLHeadingElement>(null);
  const [acted, setActed] = useState(false);
  const closed = a.status !== "open";
  const jump = safeUrl(a.jump_url);
  const acts = ["resolve", "false_positive", "watch", "timeout", "delete", "kick", "ban"].filter((x) => {
    if (x === "delete") return a.kind === "message" && !!a.jump_url;
    if (["timeout", "kick", "ban", "watch"].includes(x)) return !!a.user;
    return true;
  });
  // After the card closes, the clicked button is gone: move focus to the title.
  useEffect(() => {
    if (closed && acted) title.current?.focus();
  }, [closed, acted]);

  async function act(action: string) {
    const name = a.user ? splitName(a.user.name).display : "";
    if (action === "kick" && !(await confirm(t("cKickTitle", { name }), t("cKickBody"), t("a_kick")))) return;
    if (action === "ban" && !(await confirm(t("cBanTitle", { name }), t("cBanBody"), t("a_ban")))) return;
    setBusy(true);
    try {
      const r = await call<{ alert: Alert }>("POST", `/api/guilds/${gid}/alerts/${a.id}`, { action });
      toast(t("done"));
      setActed(true);
      onUpdate?.(r.alert);
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className={`alert alert-${a.level} ${closed ? "is-closed" : ""}`} data-alert={a.id} aria-labelledby={`al-${a.id}`}>
      <div className="alert-top">
        <LevelPill level={a.level} score={a.score} />
        <span className="chip">{t("k_" + a.kind)}</span>
        {closed && <span className="chip chip-good"><Icon name="check" />{t("st_" + a.status)}</span>}
        <span className="alert-time"><TimeEl iso={a.created_at} /></span>
      </div>
      <h3 id={`al-${a.id}`} className="alert-title" tabIndex={-1} ref={title}>{a.title}</h3>
      <p className="alert-summary">{a.summary}</p>
      {a.quote && !compact && <blockquote className="quote">{a.quote}</blockquote>}
      {(a.user || a.target) && !compact && (
        <div className="alert-people">
          <Who user={a.user} gid={gid} />
          {a.user && a.target && <span className="arrow">{t("toTarget")}</span>}
          <Who user={a.target} gid={gid} />
        </div>
      )}
      {!compact && a.signals && a.signals.length > 0 && (
        <details className="alert-sigs"><summary>{t("signalsN", { n: a.signals.length })}</summary><SignalList signals={a.signals} /></details>
      )}
      {closed && a.resolved_by && (
        <p className="alert-resolved">
          {t("resolvedBy", { status: t("st_" + a.status), who: a.resolved_by })}
          {a.action && a.action !== a.status && a.action !== "resolve" ? " · " + t("actionWas", { a: t("a_" + a.action) }) : ""}
        </p>
      )}
      {!compact && (
        <div className="alert-actions">
          {!closed && acts.map((x) => (
            <button key={x} type="button" disabled={busy} aria-busy={busy}
              className={x === "resolve" ? "btn btn-primary" : x === "kick" || x === "ban" ? "btn btn-danger" : "btn"}
              onClick={() => act(x)}>{t("a_" + x)}</button>
          ))}
          {jump && <a className="btn btn-ghost" href={jump} target="_blank" rel="noopener noreferrer"><Icon name="ext" />{t("jump")}</a>}
        </div>
      )}
    </article>
  );
}

export function AlertsView() {
  const { gid } = useParams<{ gid: string }>();
  const { t, href, setOpenAlerts } = useDash();
  const params = useSearchParams();
  const status = params.get("status") === "all" ? "all" : "open";
  const res = useApi<{ alerts: Alert[] }>(`/api/guilds/${gid}/alerts?status=${status}&limit=50`, {
    onData: (d) => { if (status === "open") setOpenAlerts(gid, d.alerts.length); },
  });
  const base = `/dashboard/g/${encodeURIComponent(gid)}/alerts`;

  function update(a: Alert) {
    res.mutate((d) => ({ ...d, alerts: d.alerts.map((x) => (x.id === a.id ? a : x)) }));
    if (a.status !== "open") setOpenAlerts(gid, (n) => Math.max(0, n - 1));
  }

  return (
    <>
      <PageHead><h1>{t("alertsTitle")}</h1></PageHead>
      <nav className="tabs" aria-label={t("alertsTitle")}>
        {(["open", "all"] as const).map((s) => (
          <Link key={s} className="tab" href={href(base + (s === "all" ? "?status=all" : ""))} aria-current={s === status ? "page" : undefined}>{t("f_" + s)}</Link>
        ))}
      </nav>
      <Async res={res}>
        {(d) => d.alerts.length
          ? <div className="alert-list">{d.alerts.map((a) => <AlertItem key={a.id} a={a} gid={gid} onUpdate={update} />)}</div>
          : <Empty>{status === "open" ? t("noAlertsOpen") : t("noAlerts")}</Empty>}
      </Async>
    </>
  );
}
