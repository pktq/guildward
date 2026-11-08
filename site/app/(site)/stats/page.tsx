import type { Metadata } from "next";
import { Suspense } from "react";
import { Columns } from "@/components/site/Columns";
import { getPublicStats, type PublicStats } from "@/lib/guard";
import "@/components/site/stats.css";

export const metadata: Metadata = {
  title: "Stats",
  description:
    "What Guildward has done so far: messages checked, warning signs flagged, alerts and kids' checks. Counts only, never a message.",
};

const nf = new Intl.NumberFormat("en");
const dateFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
const dayFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
const stampFmt = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
});

type Levels = PublicStats["pocket"]["by_kind"]["server"];
const LEVELS = [
  { key: "green", name: "No warning signs" },
  { key: "yellow", name: "Be careful" },
  { key: "red", name: "High risk" },
] as const;

export default function StatsPage() {
  return (
    <Suspense fallback={<p className="st-loading">Counting…</p>}>
      <Stats />
    </Suspense>
  );
}

async function Stats() {
  const { stats: s, live } = await getPublicStats();
  const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);
  // Start the charts at the first active day (pre-launch there are long runs of zeros), keeping at least two weeks.
  const all = s.series;
  const first = all.days.findIndex(
    (_, i) => all.messages[i] || all.flagged[i] || all.alerts[i] || all.pocket_checks[i],
  );
  const from = first < 0 ? 0 : Math.min(first, Math.max(0, all.days.length - 14));
  const cut = (xs: number[]) => xs.slice(from);
  const days = all.days.slice(from).map((d) => dayFmt.format(new Date(`${d}T00:00:00Z`)));

  const guard: [number, string, string?][] = [
    [s.servers, s.servers === 1 ? "server running Guard" : "servers running Guard"],
    [s.members, "members protected"],
    [s.guard.messages, "messages checked"],
    [s.guard.flagged, "warning signs flagged"],
    [
      s.guard.alerts,
      "alerts to moderators",
      s.guard.alerts ? `${nf.format(s.guard.red_alerts)} of them red` : undefined,
    ],
    [s.guard.actions, "moderator actions taken"],
    [s.guard.raids, "join raids caught"],
    [s.guard.kids_warned, "kids sent a safety tip"],
  ];
  const pocket: [number, string][] = [
    [s.pocket.checks, "checks by kids"],
    [s.pocket.scans, "server scans"],
    [s.pocket.watch_alerts, "watch alerts sent"],
    [s.pocket.flagged_accounts, "accounts flagged"],
  ];
  const kinds: [string, Levels][] = [
    ["Servers", s.pocket.by_kind.server],
    ["People", s.pocket.by_kind.person],
    ["Messages", s.pocket.by_kind.message],
  ];
  const topSignal = Math.max(1, ...s.signals.map((x) => x.n));
  const multiples: [string, number[], string][] = [
    ["Warning signs flagged", cut(all.flagged), "flagged"],
    ["Alerts to moderators", cut(all.alerts), "alerts"],
    ["Checks by kids", cut(all.pocket_checks), "checks"],
  ];

  return (
    <>
      <section className="st-intro" aria-labelledby="stats-title">
        <h1 id="stats-title">Guildward so far</h1>
        <p className="gw-lead">
          Counts from every server running Guard and every kid using the app. Never a message, never a name.
        </p>
        <p className="st-meta">
          {s.since && <>Counting since {dateFmt.format(new Date(s.since))} · </>}
          updated {stampFmt.format(new Date(s.generated_at))} UTC
        </p>
        {!live && (
          <p className="st-sample" role="note">
            <b>Sample data.</b> The live numbers can&rsquo;t be reached right now, so this page shows a simulated server
            instead. Real counts return on their own.
          </p>
        )}
      </section>

      <section className="st-field" aria-labelledby="st-messages" data-reveal>
        <div className="st-field-head">
          <p className="st-figure" id="st-messages">
            {nf.format(s.guard.messages)}
          </p>
          <p className="st-claim">messages checked, and not one of them stored</p>
        </div>
        {sum(all.messages) > 0 ? (
          <Columns
            days={days}
            values={cut(all.messages)}
            unit="messages"
            label="Messages checked per day"
            tone="dark"
            height="min(52vh, 440px)"
          />
        ) : (
          <p className="st-empty">No messages checked in the last 90 days yet.</p>
        )}
        <p className="st-field-note">Messages checked per day, last {days.length} days.</p>
      </section>

      <section className="st-ledger" aria-label="Totals">
        <div className="st-group st-group-guard" data-reveal>
          <p className="st-eyebrow">Guard</p>
          <h2>In servers running Guard</h2>
          <dl>
            {guard.map(([n, label, sub]) => (
              <div key={label} className="st-item" data-zero={n === 0 || undefined}>
                <dt>{label}</dt>
                <dd>
                  {nf.format(n)}
                  {sub && <small>{sub}</small>}
                </dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="st-group st-group-kids" data-reveal>
          <p className="st-eyebrow">Kids&rsquo; app</p>
          <h2>In kids&rsquo; own Discord</h2>
          <dl>
            {pocket.map(([n, label]) => (
              <div key={label} className="st-item" data-zero={n === 0 || undefined}>
                <dt>{label}</dt>
                <dd>{nf.format(n)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="st-split" aria-labelledby="st-split-title">
        <div className="st-split-head">
          <h2 id="st-split-title">What kids&rsquo; checks found</h2>
          <p>
            Every check ends in one of three answers. Here is how {nf.format(s.pocket.checks)} of them came out, by what
            was checked.
          </p>
          <ul className="st-legend" aria-label="Legend">
            {LEVELS.map((l) => (
              <li key={l.key}>
                <span className={`st-swatch st-${l.key}`} aria-hidden="true" />
                {l.name}
              </li>
            ))}
          </ul>
        </div>
        <div className="st-bars" data-reveal>
          {kinds.map(([name, lv]) => {
            const total = lv.green + lv.yellow + lv.red;
            return (
              <div key={name} className="st-bar-row">
                <p className="st-bar-name">
                  {name} <span>{nf.format(total)} checked</span>
                </p>
                {total > 0 ? (
                  <div
                    className="st-seg"
                    role="img"
                    aria-label={`${name}: ${LEVELS.map((l) => `${nf.format(lv[l.key])} ${l.name.toLowerCase()}`).join(", ")}.`}
                  >
                    {LEVELS.filter((l) => lv[l.key] > 0).map((l) => {
                      const share = lv[l.key] / total;
                      return (
                        <span
                          key={l.key}
                          className={`st-seg-part st-${l.key}`}
                          style={{ flexGrow: lv[l.key] }}
                          title={`${l.name}: ${nf.format(lv[l.key])} (${Math.round(share * 100)}%)`}
                        >
                          {share >= 0.1 && `${Math.round(share * 100)}%`}
                        </span>
                      );
                    })}
                  </div>
                ) : (
                  <p className="st-empty-row">None yet.</p>
                )}
                <p className="st-bar-counts">{LEVELS.map((l) => `${nf.format(lv[l.key])} ${l.key}`).join(" · ")}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="st-signals" aria-labelledby="st-signals-title">
        <h2 id="st-signals-title">Top warning signs</h2>
        {s.signals.length ? (
          <ol className="st-hbars" data-reveal>
            {s.signals.map((x) => (
              <li key={x.code}>
                <span className="st-hbar-label">{x.label}</span>
                <span className="st-hbar-track">
                  <span className="st-hbar" style={{ width: `${(x.n / topSignal) * 100}%` }} />
                  <span className="st-hbar-val">{nf.format(x.n)}</span>
                </span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="st-empty-row">No warning signs flagged yet.</p>
        )}
      </section>

      <section className="st-multi" aria-labelledby="st-multi-title">
        <h2 id="st-multi-title" className="gw-sr">
          The last {days.length} days
        </h2>
        {multiples.map(([title, values, unit]) => (
          <div key={title} className="st-multi-item" data-reveal>
            <h3>{title}</h3>
            <p className="st-multi-total">
              {nf.format(sum(values))} <span>in {days.length} days</span>
            </p>
            {sum(values) > 0 ? (
              <Columns days={days} values={values} unit={unit} label={`${title} per day`} height="160px" />
            ) : (
              <p className="st-empty-row">None in this period.</p>
            )}
          </div>
        ))}
      </section>

      <section className="st-how" aria-labelledby="st-how-title">
        <h2 id="st-how-title">How this is counted</h2>
        <ul data-reveal>
          <li>
            Guard counts what it does as it does it: a message checked, a sign flagged, an alert raised. Text is never
            kept.
          </li>
          <li>
            Kids&rsquo; checks appear here by kind and answer only: no names, no IDs, nothing about what was checked.
          </li>
          <li>
            The page refreshes every few minutes. Totals run from the first day counted; the charts show the last{" "}
            {days.length} days.
          </li>
        </ul>
      </section>
    </>
  );
}
