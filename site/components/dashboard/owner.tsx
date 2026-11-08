"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { splitName } from "@/lib/dashboard/api";
import { duration, unixIso } from "@/lib/dashboard/format";
import type { Account, AccountsResponse, Counts, OwnerOverview } from "@/lib/dashboard/types";
import { Chart, ChartTable } from "./charts";
import { useApi, useDash } from "./context";
import { Async, Avatar, Empty, ErrorView, Icon, LevelPill, Panel, PageHead, TimeEl, Who } from "./ui";

function OwnerGate({ children }: { children: React.ReactNode }) {
  const { me, t } = useDash();
  if (me && !me.owner) return <ErrorView msg={t("errNotFound")} />;
  return <>{children}</>;
}

const LEVELS = ["green", "yellow", "red"] as const;

function Owner({ o, reload }: { o: OwnerOverview; reload: () => void }) {
  const { t, f, href, call, confirm, toast, fail } = useDash();
  const [sort, setSort] = useState<{ key: "fired_30d" | "false_positive" | "fp_rate"; dir: 1 | -1 }>({ key: "fp_rate", dir: -1 });
  const [busy, setBusy] = useState<string | null>(null);
  const s = o.system;
  const m = s.model || { state: "off" as const };

  async function run(id: string, ask: Promise<boolean>, path: string, action: string, done: string) {
    if (!(await ask)) return;
    setBusy(id);
    try {
      await call("POST", path, { action });
      toast(done);
      reload();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(null);
    }
  }

  const tiles: [string, boolean, number | null | undefined][] = [
    [t("pocket"), s.pocket_online, s.latency_ms?.pocket],
    [t("guard"), s.guard_online, s.latency_ms?.guard],
  ];
  const sys = (
    <div className="sys">
      {tiles.map((x) => (
        <div key={x[0]} className={`sys-tile ${x[1] ? "is-up" : "is-down"}`}>
          <span className="sys-label">{x[0]}</span>
          <span className="sys-state"><Icon name={x[1] ? "lgreen" : "lred"} />{x[1] ? t("online") : t("offline")}</span>
          {x[2] != null && <span className="sys-sub num">{t("latency", { n: x[2] })}</span>}
        </div>
      ))}
      <div className={`sys-tile ${m.state === "ready" ? "is-up" : "is-down"}`} title={m.detail || ""}>
        <span className="sys-label">{t("model")}</span>
        <span className="sys-state"><Icon name={m.state === "ready" ? "lgreen" : m.state === "failed" || m.state === "off" ? "lred" : "lyellow"} />{t("m_" + m.state)}</span>
        {m.batch_ms_p50 != null ? <span className="sys-sub num">{t("latency", { n: m.batch_ms_p50 })}</span> : m.detail ? <span className="sys-sub">{m.detail}</span> : null}
      </div>
      <dl className="sys-facts">
        <div><dt>{t("uptime")}</dt><dd className="num">{duration(s.uptime_s)}</dd></div>
        <div><dt>{t("version")}</dt><dd className="num">{s.version}</dd></div>
        <div><dt>{t("rules")}</dt><dd>{s.rules}</dd></div>
        <div><dt>{t("database")}</dt><dd className="num">{f.bytes(s.db_bytes)}</dd></div>
        <div><dt>{t("events")}</dt><dd className="num">{f.num(s.events_per_min)}</dd></div>
        {m.state === "ready" && (
          <>
            <div><dt>{t("m_queue")}</dt><dd className="num">{f.num(m.queue_kids)} / {f.num(m.queue_guard)}</dd></div>
            <div><dt>{t("m_shed")}</dt><dd className="num">{f.num(m.shed)}</dd></div>
          </>
        )}
      </dl>
    </div>
  );

  const totals = (
    <dl className="kpis kpis-owner">
      {(["guilds", "members", "alerts_open", "alerts_7d", "flagged_7d", "network_flags", "pocket_checks_7d"] as const).map((k) => (
        <div key={k} className={`kpi ${k === "alerts_open" && o.totals[k] ? "kpi-warn" : ""}`}><dt>{t("t_" + k)}</dt><dd className="num">{f.num(o.totals[k])}</dd></div>
      ))}
    </dl>
  );
  const crowd = o.crowd && (
    <dl className="kpis kpis-owner">
      {(["users", "accounts", "reports_7d", "review", "flagged", "confirmed", "watch_alerts_7d"] as const).map((k) => (
        <div key={k} className={`kpi ${k === "review" && o.crowd![k] ? "kpi-warn" : ""}`}><dt>{t("cr_" + k)}</dt><dd className="num">{f.num(o.crowd![k])}</dd></div>
      ))}
    </dl>
  );

  const pocket = (
    <div className="pocket">
      {(["server", "person", "message"] as const).map((k) => {
        const c: Counts = o.pocket[k] || {};
        const tot = (c.green || 0) + (c.yellow || 0) + (c.red || 0);
        return (
          <div key={k} className="pocket-row">
            <span className="pocket-label">{t("pk_" + k)}</span>
            <div className="stack-bar" role="img" aria-label={`${t("pk_" + k)}: ${LEVELS.map((l) => `${t("lvl_" + l)} ${c[l] || 0}`).join(", ")}`}>
              {LEVELS.map((l) => (c[l] ? <span key={l} className={`seg-${l}`} style={{ width: `${tot ? ((c[l]! / tot) * 100).toFixed(2) : 0}%` }} /> : null))}
            </div>
            <span className="pocket-nums num">
              {LEVELS.map((l) => <span key={l} className={`pn pn-${l}`} title={t("lvl_" + l)}><Icon name={"l" + l} />{f.num(c[l] || 0)}</span>)}
            </span>
          </div>
        );
      })}
    </div>
  );

  const guilds = o.guilds.length ? (
    <div className="table-wrap">
      <table className="table">
        <thead><tr>
          <th scope="col">{t("col_server")}</th><th scope="col" className="r">{t("t_members")}</th><th scope="col">{t("col_mode")}</th><th scope="col">{t("col_risk")}</th>
          <th scope="col" className="r">{t("col_open")}</th><th scope="col" className="r">{t("col_7d")}</th><th scope="col">{t("col_since")}</th><th scope="col"><span className="sr">{t("actions")}</span></th>
        </tr></thead>
        <tbody>
          {o.guilds.map((g) => (
            <tr key={g.id}>
              <td><Link href={href(`/dashboard/g/${encodeURIComponent(g.id)}`)}>{g.name}</Link></td>
              <td className="r num">{f.num(g.members)}</td>
              <td><span className={`mode mode-${g.mode}`}>{t("mode_" + g.mode)}</span></td>
              <td><LevelPill level={g.level} score={g.score} /></td>
              <td className="r num">{f.num(g.open_alerts)}</td><td className="r num">{f.num(g.alerts_7d)}</td>
              <td className="nowrap">{f.date(g.joined_at)}</td>
              <td className="r">
                <button type="button" className="btn btn-sm btn-danger" disabled={busy === g.id} aria-busy={busy === g.id}
                  onClick={() => run(g.id, confirm(t("cLeaveTitle", { name: g.name }), t("cLeaveBody"), t("leave")), `/api/owner/guilds/${g.id}`, "leave", t("left"))}>{t("leave")}</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : <Empty>–</Empty>;

  const sq = [...o.signal_quality].sort((a, b) => (a[sort.key] - b[sort.key]) * sort.dir);
  const sortTh = (key: typeof sort.key, label: string) => {
    const on = sort.key === key;
    return (
      <th scope="col" className="r" aria-sort={on ? (sort.dir > 0 ? "ascending" : "descending") : "none"}>
        <button type="button" className="th-sort" onClick={() => setSort(on ? { key, dir: (-sort.dir) as 1 | -1 } : { key, dir: -1 })}>
          {label}{on && <Icon name={sort.dir > 0 ? "up" : "down"} className="ic-sort" />}
        </button>
      </th>
    );
  };
  const quality = (
    <div className="table-wrap">
      <table className="table">
        <thead><tr><th scope="col">{t("col_signalq")}</th>{sortTh("fired_30d", t("col_fired"))}{sortTh("false_positive", t("col_fp"))}{sortTh("fp_rate", t("col_fprate"))}</tr></thead>
        <tbody>
          {sq.map((x) => {
            const tone = x.fp_rate >= 0.3 ? "red" : x.fp_rate >= 0.15 ? "yellow" : "green";
            return (
              <tr key={x.code}>
                <td><b>{x.label}</b><div className="sub mono">{x.code}</div></td>
                <td className="r num">{f.num(x.fired_30d)}</td><td className="r num">{f.num(x.false_positive)}</td>
                <td className="r"><span className="fp"><span className="fp-bar"><span className={`fp-fill fp-${tone}`} style={{ width: `${Math.min(100, x.fp_rate * 100).toFixed(1)}%` }} /></span><span className="num">{f.pct(x.fp_rate)}</span></span></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  const network = o.network.length ? (
    <div className="table-wrap">
      <table className="table">
        <thead><tr><th scope="col">{t("col_user")}</th><th scope="col" className="r">{t("col_guilds")}</th><th scope="col">{t("col_reasons")}</th><th scope="col">{t("col_first")}</th><th scope="col"><span className="sr">{t("actions")}</span></th></tr></thead>
        <tbody>
          {o.network.map((x) => (
            <tr key={x.user.id}>
              <td><Who user={x.user} nolink /><div className="sub mono">{x.user.id}</div></td>
              <td className="r num">{f.num(x.guilds)}</td>
              <td>{x.reasons.map((r, i) => <span key={i} className="chip chip-warn">{r}</span>)}</td>
              <td className="nowrap"><TimeEl iso={x.first_at} /></td>
              <td className="r">
                <button type="button" className="btn btn-sm" disabled={busy === x.user.id} aria-busy={busy === x.user.id}
                  onClick={() => run(x.user.id, confirm(t("cClearTitle", { name: splitName(x.user.name).display }), t("cClearBody"), t("clear")), `/api/owner/network/${x.user.id}`, "clear", t("cleared"))}>{t("clear")}</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : <Empty>{t("noNetwork")}</Empty>;

  const sk = ["pocket_checks", "alerts", "flagged", "messages"];
  const vals = (k: string) => (o.series[k] as number[]) || [];
  return (
    <>
      <PageHead><h1>{t("ownerTitle")}</h1><p className="page-meta"><span>Guildward {s.version}</span></p></PageHead>
      <div className="grid grid-owner">
        <Panel title={t("system")} id="o-sys">{sys}</Panel>
        <Panel title={t("totals")} id="o-tot">{totals}</Panel>
        {o.crowd && <Panel title={t("crowdTitle")} id="o-crowd" cls="panel-wide" extra={<Link className="btn btn-sm" href={href("/dashboard/owner/accounts")}>{t("viewAccounts")}</Link>}>{crowd}</Panel>}
        <Panel title={t("activity")} id="o-act" cls="panel-wide">
          <div className="charts">{sk.map((k) => <Chart key={k} label={t("s_" + k)} days={o.series.days} values={vals(k)} type={k === "messages" ? "area" : "bar"} />)}</div>
          <ChartTable days={o.series.days} series={sk.map((k) => [t("s_" + k), vals(k)])} />
        </Panel>
        <Panel title={t("pocketBreak")} id="o-pocket" cls="panel-wide">{pocket}</Panel>
        <Panel title={t("guilds")} id="o-guilds" cls="panel-wide">{guilds}</Panel>
        <Panel title={t("quality")} id="o-sq">{quality}</Panel>
        <Panel title={t("networkTitle")} id="o-net">{network}</Panel>
      </div>
    </>
  );
}

export function OwnerView() {
  const { me } = useDash();
  const res = useApi<OwnerOverview>(me?.owner ? "/api/owner/overview" : null);
  return <OwnerGate><Async res={res}>{(o) => <Owner o={o} reload={res.reload} />}</Async></OwnerGate>;
}

// ---------------------------------------------------------------- accounts
const ACC_STATUSES = ["review", "flagged", "confirmed", "cleared", "all"];
const ACC_REASONS = ["age_pics", "sexual", "threat", "meet", "scam", "hate", "other"];
const ACC_LINKS = ["handle", "payment", "script", "avatar", "name"];
const ACC_ACTIONS: Record<string, string> = { confirm: "confirmed", clear: "cleared", watch: "watch" };
const FLAG_TONE: Record<string, string> = { confirmed: "chip-bad", flagged: "chip-bad", watch: "chip-warn", cleared: "chip-good", none: "" };

function AccountItem({ a, busy, onAct }: { a: Account; busy: boolean; onAct: (a: Account, action: string) => void }) {
  const { t, f } = useDash();
  const rs = ACC_REASONS.filter((k) => a.reasons && a.reasons[k]);
  const acts = ["confirm", "clear", "watch", "reset"].filter((x) => (x === "reset" ? a.flag !== a.auto_flag && a.flag !== "none" : ACC_ACTIONS[x] !== a.flag));
  const created = unixIso(a.created_at);
  return (
    <li className="acct">
      <div className="acct-head">
        <span className="who"><Avatar name={a.name} /><span className="who-name"><b className="who-display">{a.name}</b><span className="sub mono">{a.id}</span></span></span>
        <span className="acct-chips">
          <span className={`chip ${FLAG_TONE[a.flag] || ""}`}>{t("fl_" + a.flag)}</span>
          {a.flag !== a.auto_flag && a.auto_flag !== "none" && <span className="chip">{t("fl_auto", { f: t("fl_" + a.auto_flag) })}</span>}
          <LevelPill level={a.level} score={a.score} />
          {a.deleted && <span className="chip">{t("acc_deleted")}</span>}
        </span>
      </div>
      <dl className="acct-facts">
        <div><dt>{t("acc_created")}</dt><dd>{created ? <time dateTime={created} title={f.date(created, true)}>{f.date(created)}</time> : "–"}</dd></div>
        <div><dt>{t("acc_seen")}</dt><dd><TimeEl iso={unixIso(a.last_seen)} /></dd></div>
        <div><dt>{t("acc_checks")}</dt><dd className="num">{t("acc_checkers", { n: f.num(a.checkers), r: f.num(a.red_checkers) })}</dd></div>
        {a.network > 0 && <div><dt>{t("guard")}</dt><dd className="num">{t("acc_network", { n: f.num(a.network) })}</dd></div>}
        <div className="acct-wide">
          <dt>{t("acc_reports", { n: f.num(a.reports), w: (a.report_score || 0).toFixed(1) })}</dt>
          <dd>{rs.length ? <span className="chips acct-reasons">{rs.map((k) => <span key={k} className="chip chip-warn">{t("rs_" + k)} <b className="num">{a.reasons[k]}</b></span>)}</span> : t("acc_noReports")}</dd>
        </div>
      </dl>
      {a.links && a.links.length > 0 && (
        <ul className="acct-links" aria-label={t("acc_links")}>
          {a.links.map((l, i) => {
            const fl = l.other_flag && l.other_flag !== "none" ? ` (${t("fl_" + l.other_flag).toLowerCase()})` : "";
            return <li key={i}><Icon name="ext" /><span>{t("lkTo", { kind: ACC_LINKS.includes(l.kind) ? t("lk_" + l.kind) : l.kind, name: l.other_name })}{fl}</span></li>;
          })}
        </ul>
      )}
      <div className="acct-actions">
        {acts.map((x) => (
          <button key={x} type="button" className={`btn btn-sm ${x === "confirm" ? "btn-danger" : ""}`} disabled={busy} aria-busy={busy} onClick={() => onAct(a, x)}>{t("a_" + x)}</button>
        ))}
      </div>
    </li>
  );
}

export function AccountsView() {
  const { me, t, f, href, call, confirm, toast, fail } = useDash();
  const params = useSearchParams();
  const raw = params.get("status");
  const status = raw && ACC_STATUSES.includes(raw) ? raw : "review";
  const res = useApi<AccountsResponse>(me?.owner ? `/api/owner/accounts?status=${status}` : null);
  const [busy, setBusy] = useState<string | null>(null);

  async function act(a: Account, action: string) {
    const K = action.charAt(0).toUpperCase() + action.slice(1);
    if (!(await confirm(t(`cAcc${K}Title`, { name: a.name }), t(`cAcc${K}Body`), t("a_" + action)))) return;
    setBusy(a.id);
    try {
      await call("POST", `/api/owner/accounts/${a.id}`, { action });
      toast(t("accDone"));
      res.reload();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(null);
    }
  }

  return (
    <OwnerGate>
      <PageHead>
        <h1>{t("accTitle")}</h1>
        <p className="page-meta"><Link href={href("/dashboard/owner")}>{t("back")}</Link></p>
      </PageHead>
      <p className="acct-intro">{t("accIntro")}</p>
      <Async res={res}>
        {(d) => (
          <>
            <nav className="tabs" aria-label={t("accAria")}>
              {ACC_STATUSES.map((s) => (
                <Link key={s} className="tab" href={href("/dashboard/owner/accounts" + (s === "review" ? "" : "?status=" + s))} aria-current={s === status ? "page" : undefined}>
                  {t("st_" + s)}{s !== "all" && <span className="tab-n num">{f.num(d.counts?.[s] || 0)}</span>}
                </Link>
              ))}
            </nav>
            {d.accounts.length
              ? <ul className="acct-list">{d.accounts.map((a) => <AccountItem key={a.id} a={a} busy={busy === a.id} onAct={act} />)}</ul>
              : <Empty>{t("noAccounts")}</Empty>}
          </>
        )}
      </Async>
    </OwnerGate>
  );
}
