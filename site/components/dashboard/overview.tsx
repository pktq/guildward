"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { Overview } from "@/lib/dashboard/types";
import { AlertItem } from "./alerts";
import { Gauge, SeriesCharts } from "./charts";
import { useApi, useDash } from "./context";
import { MemberTable } from "./members";
import { Async, Empty, Icon, LevelPill, Panel, PageHead, Sentences, SignalList } from "./ui";

const KPI_LINKS: Record<string, string> = {
  at_risk: "members?filter=at_risk", red: "members?filter=at_risk", minors_est: "members?filter=minors", open_alerts: "alerts", joins_7d: "members?filter=new",
};
const KPI_KEYS = ["members", "minors_est", "at_risk", "red", "open_alerts", "flagged_7d", "messages_7d", "joins_7d", "actions_7d", "median_response_min"] as const;

function GuildMeta({ g }: { g: Overview["guild"] }) {
  const { t, f } = useDash();
  return (
    <p className="page-meta">
      <span>{t("ovMembers", { n: f.num(g.member_count) })}</span>
      <span className={`mode mode-${g.mode}`}>{t("ovMode", { mode: t("mode_" + g.mode) })}</span>
      {g.alert_channel && <span>{t("ovAlertsTo", { ch: g.alert_channel })}</span>}
      <span>{t("ovSince", { d: f.date(g.guard_since) })}</span>
    </p>
  );
}

function Kpis({ k, gid, linked }: { k: Overview["kpis"]; gid: string; linked: boolean }) {
  const { t, f, href } = useDash();
  return (
    <dl className="kpis">
      {KPI_KEYS.map((key) => {
        const raw = k[key];
        const v = key === "median_response_min" ? (raw == null ? "–" : t("minutes", { n: raw })) : f.num(raw);
        const tone = key === "red" && k.red ? "kpi-bad" : key === "open_alerts" && k.open_alerts ? "kpi-warn" : "";
        const link = KPI_LINKS[key];
        return (
          <div key={key} className={`kpi ${tone}`}>
            <dt>{t("k_" + key)}{/_7d$/.test(key) && <> <span className="kpi-span">{t("last7")}</span></>}</dt>
            <dd className="num">{linked && link ? <Link href={href(`/dashboard/g/${encodeURIComponent(gid)}/${link}`)}>{v}</Link> : v}</dd>
          </div>
        );
      })}
    </dl>
  );
}

function FixButton({ fix, gid, onDone, icon }: { fix: string; gid: string; onDone: () => void; icon?: boolean }) {
  const { t, call, toast, fail } = useDash();
  const [busy, setBusy] = useState(false);
  async function run() {
    setBusy(true);
    try {
      const r = await call<{ text?: string }>("POST", `/api/guilds/${gid}/fix`, { fix });
      toast(r.text || t("done"));
      onDone();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <button type="button" className="btn btn-sm" disabled={busy} aria-busy={busy} onClick={run}>
      {icon && <Icon name="wrench" />}{t("fix")}
    </button>
  );
}

export function OverviewBody({ o, gid, isReport, reload }: { o: Overview; gid: string; isReport: boolean; reload: () => void }) {
  const { t, f, href } = useDash();
  const g = o.guild, h = o.health;
  const passed = o.audit.filter((a) => a.ok).length;
  const base = `/dashboard/g/${encodeURIComponent(gid)}`;
  // Report dates are "now"; capture once per mount so re-renders don't drift.
  const [generated] = useState(() => new Date().toISOString());

  const perms: ReactNode = o.permissions_missing && o.permissions_missing.length > 0 && (
    <div className="banner banner-warn" role="alert">
      <Icon name="warn" />
      <div>
        <strong>{t("permTitle")}</strong>
        <p>{t("permBody", { list: "\u0000" }).split("\u0000")[0]}<b>{o.permissions_missing.join(", ")}</b>{t("permBody", { list: "\u0000" }).split("\u0000")[1]}</p>
      </div>
    </div>
  );

  const healthPanel = (
    <section className="panel panel-health" aria-labelledby="h-health">
      <header className="panel-head"><h2 id="h-health">{t("health")}</h2><LevelPill level={h.level} /></header>
      <div className="health-top"><Gauge score={h.score} level={h.level} grade={h.grade} /><p className="confidence">{h.confidence}</p></div>
      <h3 className="sub-h">{t("healthReasons")}</h3>
      <SignalList signals={h.signals} />
    </section>
  );
  const situation = (
    <Panel title={t("situation")} id="h-sit" cls="panel-situation">
      <Sentences list={o.summary} />
      <h3 className="sub-h">{t("keyFigures")}</h3>
      <Kpis k={o.kpis} gid={gid} linked={!isReport} />
    </Panel>
  );
  const recs = (
    <Panel title={t("recs")} id="h-recs">
      {o.recommendations.length ? (
        <ul className="recs">
          {o.recommendations.map((r, i) => (
            <li key={i} className="rec">
              <span className={`sev sev-${r.severity}`}>{t("sev_" + r.severity)}</span>
              <span className="rec-text">{r.text}</span>
              {r.fix && !isReport && <FixButton fix={r.fix} gid={gid} onDone={reload} icon />}
            </li>
          ))}
        </ul>
      ) : <Empty>{t("noRecs")}</Empty>}
    </Panel>
  );
  const audit = (
    <Panel title={t("audit")} id="h-audit" extra={<span className="panel-note num">{t("auditPassed", { n: passed, m: o.audit.length })}</span>}>
      <ul className="audit">
        {o.audit.map((a) => (
          <li key={a.id} className={a.ok ? "is-ok" : "is-fail"}>
            <span className="audit-mark"><Icon name={a.ok ? "check" : "x"} /><span className="sr">{a.ok ? t("auditOk") : t("auditFail")}</span></span>
            <div className="audit-body">
              <b>{a.label}</b> {!a.ok && <span className={`sev sev-${a.severity}`}>{t("sev_" + a.severity)}</span>}
              <p>{a.detail}</p>
            </div>
            {!a.ok && a.fix && !isReport && <FixButton fix={a.fix} gid={gid} onDone={reload} />}
          </li>
        ))}
      </ul>
    </Panel>
  );
  const activity = <Panel title={t("activity")} id="h-act" cls="panel-wide"><SeriesCharts s={o.series} keys={["messages", "flagged", "joins", "alerts"]} /></Panel>;
  const risks = (
    <Panel title={t("topRisks")} id="h-risk" extra={!isReport && <Link className="panel-link" href={href(`${base}/members?filter=at_risk`)}>{t("seeAll")}</Link>}>
      <MemberTable rows={o.top_risks} gid={isReport ? null : gid} compact />
    </Panel>
  );
  const recent = (
    <Panel title={t("recentAlerts")} id="h-recent" extra={!isReport && <Link className="panel-link" href={href(`${base}/alerts`)}>{t("openQueue")}</Link>}>
      {o.recent_alerts.length
        ? <div className="alert-list is-compact">{o.recent_alerts.map((a) => <AlertItem key={a.id} a={a} gid={gid} compact />)}</div>
        : <Empty>{t("noAlerts")}</Empty>}
    </Panel>
  );

  if (isReport) {
    return (
      <article className="report-doc">
        <header className="report-head">
          <div className="report-brand"><Icon name="shield" className="brand-mark" /><span>Guildward Guard · {t("reportTitle")}</span></div>
          <h1>{g.name}</h1>
          <GuildMeta g={g} />
          <p className="report-date">{t("reportFor", { d: f.date(generated, true) })}</p>
          <div className="report-tools no-print">
            <button type="button" className="btn btn-primary" onClick={() => window.print()}><Icon name="print" />{t("print")}</button>
            <Link className="btn btn-ghost" href={href(base)}><Icon name="arrowLeft" />{t("reportBack")}</Link>
          </div>
        </header>
        {perms}
        <div className="report-grid">{healthPanel}{situation}</div>
        {recs}{audit}{activity}{risks}{recent}
      </article>
    );
  }
  return (
    <>
      <PageHead action={<Link className="btn btn-ghost" href={href(`${base}/report`)}><Icon name="print" />{t("printable")}</Link>}>
        <h1>{g.name}</h1>
        <GuildMeta g={g} />
      </PageHead>
      {perms}
      <div className="grid grid-ov">{healthPanel}{situation}{recs}{audit}{activity}{risks}{recent}</div>
    </>
  );
}

export function OverviewView({ report }: { report?: boolean }) {
  const { gid } = useParams<{ gid: string }>();
  const { setOpenAlerts, setGuildName, t } = useDash();
  const res = useApi<Overview>(`/api/guilds/${gid}/overview`, {
    onData: (o) => {
      setGuildName(gid, o.guild.name);
      if (!report) setOpenAlerts(gid, o.kpis.open_alerts);
    },
  });
  const name = res.data?.guild.name;
  const title = report && name ? `${t("reportTitle")} · ${name}` : null;
  useEffect(() => {
    if (!title) return;
    const prev = document.title;
    document.title = title;
    return () => { document.title = prev; };
  }, [title]);
  return <Async res={res}>{(o) => <OverviewBody o={o} gid={gid} isReport={!!report} reload={res.reload} />}</Async>;
}
