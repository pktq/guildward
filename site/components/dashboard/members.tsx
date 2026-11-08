"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { splitName } from "@/lib/dashboard/api";
import { safeUrl } from "@/lib/dashboard/format";
import type { MemberReport, MemberRow } from "@/lib/dashboard/types";
import { Chart } from "./charts";
import { useApi, useDash } from "./context";
import { Async, Avatar, Empty, FlagChips, Icon, LevelPill, Panel, PageHead, Sentences, SignalList, TimeEl, Trend, Who } from "./ui";

export function MemberTable({ rows, gid, compact }: { rows: MemberRow[]; gid: string | null; compact?: boolean }) {
  const { t, f } = useDash();
  if (!rows.length) return <Empty>{t("noMembers")}</Empty>;
  return (
    <div className="table-wrap">
      <table className={`table members-table ${compact ? "is-compact" : ""}`}>
        <thead>
          <tr>
            <th scope="col">{t("col_member")}</th><th scope="col">{t("col_risk")}</th><th scope="col" className="r">{t("col_trend")}</th>
            {!compact && <><th scope="col">{t("col_age")}</th><th scope="col">{t("col_joined")}</th><th scope="col">{t("col_seen")}</th></>}
            <th scope="col">{t("col_signal")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((m) => (
            <tr key={m.id} className={m.status === "left" ? "is-left" : ""}>
              <td className="cell-member">
                <Who user={m} gid={gid} />
                {!compact && (
                  <div className="chips">
                    {m.status !== "none" && !m.flags.includes(m.status) && m.status !== "trusted" && <span className="chip">{t("ms_" + m.status)}</span>}
                    <FlagChips flags={m.flags.filter((x) => x !== "minor")} />
                  </div>
                )}
              </td>
              <td><LevelPill level={m.level} score={m.score} /></td>
              <td className="r"><Trend n={m.trend} /></td>
              {!compact && (
                <>
                  <td className="nowrap">{m.self_age != null ? t("ageYears", { n: m.self_age }) : "–"}<div className="sub">{t("acctDays", { n: f.num(m.account_age_days) })}</div></td>
                  <td className="nowrap"><TimeEl iso={m.joined_at} /></td>
                  <td className="nowrap"><TimeEl iso={m.last_seen} /></td>
                </>
              )}
              <td className="cell-signal">{m.top_signal || <span className="muted">–</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const FILTERS = ["all", "at_risk", "minors", "watch", "new"];
const SORTS = ["risk", "recent", "name"];

export function MembersView() {
  const { gid } = useParams<{ gid: string }>();
  const { t, f, href } = useDash();
  const router = useRouter();
  const params = useSearchParams();
  const rawFilter = params.get("filter"), rawSort = params.get("sort");
  const filter = rawFilter && FILTERS.includes(rawFilter) ? rawFilter : "all";
  const sort = rawSort && SORTS.includes(rawSort) ? rawSort : "risk";
  const q = params.get("q") || "";
  const base = `/dashboard/g/${encodeURIComponent(gid)}/members`;
  const to = (over: { filter?: string; sort?: string; q?: string }) => {
    const o = { filter, sort, q, ...over }, s = new URLSearchParams();
    if (o.filter !== "all") s.set("filter", o.filter);
    if (o.sort !== "risk") s.set("sort", o.sort);
    if (o.q) s.set("q", o.q);
    const qs = s.toString();
    return href(base + (qs ? "?" + qs : ""));
  };

  const res = useApi<{ members: MemberRow[]; total: number }>(
    `/api/guilds/${gid}/members?filter=${filter}&sort=${sort}&q=${encodeURIComponent(q)}&limit=100`, { keepPrevious: true },
  );

  // The box is uncontrolled so typing never fights the debounced URL update.
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  const onSearch = (v: string) => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => router.replace(to({ q: v.trim() }), { scroll: false }), 250);
  };

  return (
    <>
      <PageHead><h1>{t("membersTitle")}</h1></PageHead>
      <div className="toolbar">
        <nav className="tabs" aria-label={t("membersTitle")}>
          {FILTERS.map((x) => <Link key={x} className="tab" href={to({ filter: x })} aria-current={x === filter ? "page" : undefined}>{t("mf_" + x)}</Link>)}
        </nav>
        <div className="toolbar-right">
          <label className="search">
            <Icon name="search" /><span className="sr">{t("search")}</span>
            <input id="m-search" type="search" defaultValue={q} placeholder={t("searchPh")} autoComplete="off" onChange={(e) => onSearch(e.target.value)} />
          </label>
          <label className="select-label">
            <span>{t("sortBy")}</span>
            <select id="m-sort" value={sort} onChange={(e) => router.replace(to({ sort: e.target.value }), { scroll: false })}>
              {SORTS.map((s) => <option key={s} value={s}>{t("so_" + s)}</option>)}
            </select>
          </label>
        </div>
      </div>
      <div id="m-table" aria-busy={res.loading || undefined}>
        <Async res={res}>
          {(d) => (
            <>
              <p className="result-count" role="status">{t("showing", { n: f.num(d.members.length), m: f.num(d.total) })}</p>
              <MemberTable rows={d.members} gid={gid} />
            </>
          )}
        </Async>
      </div>
    </>
  );
}

const MEMBER_ACTIONS = ["watch", "trust", "clear", "timeout", "kick", "ban"];
const STAT_KEYS = ["messages", "flagged", "distinct_targets", "minor_targets", "reports", "mod_actions", "network_flags"] as const;
const TR_ICON = { rising: "up", falling: "down", stable: "flat" } as const;

function MemberBody({ r, gid, onUpdate }: { r: MemberReport; gid: string; onUpdate: (m: Partial<MemberRow>) => void }) {
  const { t, f, href, call, confirm, toast, fail } = useDash();
  const [busy, setBusy] = useState<string | null>(null);
  const m = r.member, v = r.verdict, pr = r.prediction, n = splitName(m.name);
  const meta = [
    m.self_age != null ? t("pSelfAge", { n: m.self_age }) : null,
    m.account_created ? t("pAccount", { d: f.date(m.account_created) }) : t("acctDays", { n: m.account_age_days }),
    m.joined_at ? t("pJoined", { d: f.date(m.joined_at) }) : null,
    m.invite_code ? t("pInvite", { c: m.invite_code }) : null,
    m.left_at ? t("pLeft", { d: f.date(m.left_at) }) : null,
  ].filter(Boolean);

  async function act(action: string) {
    if (action === "kick" && !(await confirm(t("cKickTitle", { name: n.display }), t("cKickBody"), t("a_kick")))) return;
    if (action === "ban" && !(await confirm(t("cBanTitle", { name: n.display }), t("cBanBody"), t("a_ban")))) return;
    setBusy(action);
    try {
      const res = await call<{ member?: MemberRow }>("POST", `/api/guilds/${gid}/members/${m.id}`, { action });
      toast(t("done"));
      if (res.member) onUpdate(res.member);
    } catch (e) {
      fail(e);
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <Link className="back" href={href(`/dashboard/g/${encodeURIComponent(gid)}/members`)}><Icon name="arrowLeft" />{t("members")}</Link>
      <header className="person-head">
        <div className="person-id">
          <Avatar name={m.name} large />
          <div>
            <h1>{n.display} {n.handle && <span className="who-handle">{n.handle}</span>}</h1>
            <p className="page-meta">{meta.map((x, i) => <span key={i}>{x}</span>)}</p>
            <div className="chips">
              {m.status !== "none" && <span className="chip chip-status">{t("ms_" + m.status)}</span>}
              {m.minor && <span className="chip chip-minor">{t("fl_minor")}</span>}
              <FlagChips flags={m.flags.filter((x) => x !== "minor" && x !== m.status)} />
              {(m.roles || []).length > 0 && (
                <span className="roles"><span className="sr">{t("pRoles")}: </span>{m.roles!.map((x, i) => <span key={i} className="role">{x}</span>)}</span>
              )}
            </div>
          </div>
        </div>
        <div className="person-actions" role="group" aria-label={t("memberActions")}>
          {MEMBER_ACTIONS.map((a) => {
            const on = (a === "watch" && m.status === "watch") || (a === "trust" && m.status === "trusted");
            return (
              <button key={a} type="button" disabled={busy != null} aria-busy={busy === a} aria-pressed={on || undefined}
                className={a === "kick" || a === "ban" ? "btn btn-danger" : a === "watch" ? "btn btn-primary" : "btn"} onClick={() => act(a)}>
                {t("a_" + a)}
              </button>
            );
          })}
        </div>
      </header>
      <div className="grid grid-person">
        <section className="panel panel-verdict" aria-labelledby="p-verdict">
          <header className="panel-head"><h2 id="p-verdict">{t("verdict")}</h2></header>
          <div className="verdict-top"><span className={`verdict-score num score-${v.level}`}>{v.score}</span><LevelPill level={v.level} /><Trend n={m.trend} /></div>
          <p className="confidence">{v.confidence}</p>
          <SignalList signals={v.signals} />
        </section>
        <div className="stack">
          <Panel title={t("summary")} id="p-sum"><Sentences list={r.summary} /></Panel>
          <section className={`panel panel-predict pred-${pr.escalation}`} aria-labelledby="p-pred">
            <header className="panel-head"><h2 id="p-pred">{t("prediction")}</h2></header>
            <div className="pred-tags">
              <span className="pred-tag"><Icon name={TR_ICON[pr.trajectory] || "flat"} />{t("tr_" + pr.trajectory)}</span>
              <span className="pred-tag pred-esc"><Icon name={pr.escalation === "none" ? "check" : "warn"} />{t("es_" + pr.escalation)}</span>
            </div>
            <p className="pred-text">{pr.text}</p>
          </section>
        </div>
        <Panel title={t("stats")} id="p-stats">
          <dl className="stats">
            {STAT_KEYS.map((k) => {
              const warn = ["minor_targets", "reports", "network_flags", "flagged"].includes(k) && r.stats[k] > 0;
              return <div key={k} className={warn ? "is-warn" : ""}><dt>{t("st_" + k)}</dt><dd className="num">{f.num(r.stats[k])}</dd></div>;
            })}
          </dl>
          <div className="charts charts-2">
            <Chart label={t("s_messages")} days={r.series.days} values={r.series.messages as number[]} type="area" compact />
            <Chart label={t("s_flagged")} days={r.series.days} values={r.series.flagged as number[]} compact />
          </div>
        </Panel>
        <Panel title={t("contacts")} id="p-contacts" cls="panel-wide">
          {r.contacts.length ? (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th scope="col">{t("col_member")}</th><th scope="col">{t("col_risk")}</th><th scope="col" className="r">{t("col_messages")}</th><th scope="col">{t("col_stages")}</th><th scope="col">{t("col_last")}</th></tr></thead>
                <tbody>
                  {r.contacts.map((c, i) => (
                    <tr key={i}>
                      <td><Who user={c.user} gid={gid} /></td>
                      <td><LevelPill level={c.level} /></td>
                      <td className="r num">{f.num(c.messages)}</td>
                      <td>{c.stages.length ? <ol className="stages">{c.stages.map((s, j) => <li key={j}>{s}</li>)}</ol> : <span className="muted">{t("noStages")}</span>}</td>
                      <td className="nowrap"><TimeEl iso={c.last_at} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <Empty>{t("noContacts")}</Empty>}
        </Panel>
        <Panel title={t("timeline")} id="p-tl" cls="panel-wide">
          {r.timeline.length ? (
            <ol className="timeline">
              {r.timeline.map((e, i) => {
                const j = safeUrl(e.jump_url);
                return (
                  <li key={i} className={`tl-${e.level || "none"}`}>
                    <span className="tl-dot" aria-hidden="true" />
                    <div className="tl-meta"><span className="tl-kind">{t("tk_" + e.kind)}</span><TimeEl iso={e.at} />{e.level && <span className="sr">{t("lvl_" + e.level)}</span>}</div>
                    <p className="tl-text">{e.text}{j && <> <a href={j} target="_blank" rel="noopener noreferrer" className="tl-jump"><Icon name="ext" /><span className="sr">{t("jump")}</span></a></>}</p>
                  </li>
                );
              })}
            </ol>
          ) : <Empty>{t("noTimeline")}</Empty>}
        </Panel>
      </div>
    </>
  );
}

export function MemberView() {
  const { gid, uid } = useParams<{ gid: string; uid: string }>();
  const res = useApi<MemberReport>(`/api/guilds/${gid}/members/${encodeURIComponent(uid)}`);
  return (
    <Async res={res}>
      {(r) => <MemberBody r={r} gid={gid} onUpdate={(m) => res.mutate((d) => ({ ...d, member: { ...d.member, ...m } }))} />}
    </Async>
  );
}
