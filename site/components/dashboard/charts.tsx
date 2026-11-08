"use client";

import { useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import { useDash } from "./context";

const W = 300;

export function Chart({ label, days, values, type = "bar", compact }: { label: string; days: string[]; values: number[]; type?: "bar" | "area"; compact?: boolean }) {
  const { t, f } = useDash();
  const [cur, setCur] = useState(-1);
  const n = values.length, H = compact ? 56 : 84, pad = 3;
  if (!n) {
    return (
      <figure className="chart"><figcaption><span className="chart-title">{label}</span></figcaption><p className="empty">–</p></figure>
    );
  }
  const max = Math.max(...values, 1);
  const total = values.reduce((a, b) => a + b, 0);
  const peakI = values.indexOf(max);
  const slot = W / n;
  const y = (v: number) => H - pad - (v / max) * (H - pad * 2);
  const at = (i: number) => Math.max(0, Math.min(n - 1, i));
  const cx = cur >= 0 ? (cur + 0.5) * slot : -10;

  let marks;
  if (type === "area") {
    const pts = values.map((v, i) => [(i + 0.5) * slot, y(v)]);
    const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join("");
    const area = line + "L" + pts[n - 1][0].toFixed(1) + " " + (H - pad) + "L" + pts[0][0].toFixed(1) + " " + (H - pad) + "Z";
    marks = (
      <>
        <path className="ch-area" d={area} />
        <path className="ch-line" d={line} />
        <circle className="ch-dot" r="3.5" cx={cx} cy={cur >= 0 ? y(values[cur]) : -10} />
      </>
    );
  } else {
    const bw = slot - 2;
    marks = values.map((v, i) => {
      const x = i * slot + 1;
      let top = y(v), h = H - pad - top;
      if (v > 0 && h < 2) { h = 2; top = H - pad - 2; }
      const r = Math.min(2, bw / 2, h);
      const d = v > 0
        ? `M${x.toFixed(1)} ${H - pad}V${(top + r).toFixed(1)}q0 -${r} ${r} -${r}H${(x + bw - r).toFixed(1)}q${r} 0 ${r} ${r}V${H - pad}Z`
        : "";
      return <path key={i} className={`ch-bar${i === cur ? " is-hot" : ""}`} d={d} />;
    });
  }

  const aria = t("chartAria", { label, total: f.num(total), peak: f.num(max), day: days[peakI] ? f.day(days[peakI]) : "" });
  const frac = cur >= 0 ? (cur + 0.5) / n : 0;
  const tipStyle = frac < 0.14 ? { left: 0 } : frac > 0.86 ? { right: 0 } : { left: `${frac * 100}%`, transform: "translateX(-50%)" };

  function onMove(e: PointerEvent<SVGSVGElement>) {
    const r = e.currentTarget.getBoundingClientRect();
    setCur(at(Math.floor(((e.clientX - r.left) / r.width) * n)));
  }
  function onKey(e: KeyboardEvent<SVGSVGElement>) {
    const step = ({ ArrowLeft: -1, ArrowRight: 1 } as Record<string, number>)[e.key];
    if (step) { e.preventDefault(); setCur(at(cur + step)); }
    else if (e.key === "Home") { e.preventDefault(); setCur(0); }
    else if (e.key === "End") { e.preventDefault(); setCur(n - 1); }
  }

  return (
    <figure className={`chart ${compact ? "chart-compact" : ""} ${cur >= 0 ? "is-active" : ""}`}>
      <figcaption><span className="chart-title">{label}</span><span className="chart-total num">{t("chartTotal", { n: f.num(total) })}</span></figcaption>
      <div className="chart-plot">
        <span className="chart-max num" aria-hidden="true">{f.num(max)}</span>
        <svg
          viewBox={`0 0 ${W} ${H}`} role="img" tabIndex={0} aria-label={aria}
          onPointerMove={onMove} onPointerLeave={() => setCur(-1)} onBlur={() => setCur(-1)}
          onFocus={() => setCur((c) => (c < 0 ? n - 1 : c))} onKeyDown={onKey}
        >
          <line className="ch-grid" x1="0" x2={W} y1={pad} y2={pad} />
          <line className="ch-grid" x1="0" x2={W} y1={(H / 2).toFixed(1)} y2={(H / 2).toFixed(1)} />
          <line className="ch-base" x1="0" x2={W} y1={H - pad} y2={H - pad} />
          <line className="ch-cross" x1={cx} x2={cx} y1="0" y2={H} />
          {marks}
        </svg>
        {cur >= 0 && (
          <div className="chart-tip" role="status" style={tipStyle}>
            <span>{f.day(days[cur])}</span><b className="num">{f.num(values[cur])}</b>
          </div>
        )}
      </div>
      <div className="chart-axis" aria-hidden="true"><span>{days[0] ? f.day(days[0]) : ""}</span><span>{days[n - 1] ? f.day(days[n - 1]) : ""}</span></div>
    </figure>
  );
}

export function ChartTable({ days, series }: { days: string[]; series: [string, number[]][] }) {
  const { t, f } = useDash();
  return (
    <details className="chart-data">
      <summary>{t("dataTable")}</summary>
      <div className="table-wrap">
        <table className="table table-tight">
          <thead><tr><th scope="col">{t("day")}</th>{series.map((s) => <th key={s[0]} scope="col" className="r">{s[0]}</th>)}</tr></thead>
          <tbody>
            {days.map((d, i) => (
              <tr key={d}><th scope="row">{f.day(d)}</th>{series.map((s) => <td key={s[0]} className="r num">{f.num(s[1][i])}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export function SeriesCharts({ s, keys }: { s: { days: string[]; [k: string]: string[] | number[] }; keys: string[] }) {
  const { t } = useDash();
  const vals = (k: string) => (s[k] as number[]) || [];
  return (
    <>
      <div className="charts">
        {keys.map((k) => <Chart key={k} label={t("s_" + k)} days={s.days} values={vals(k)} type={k === "messages" ? "area" : "bar"} />)}
      </div>
      <ChartTable days={s.days} series={keys.map((k) => [t("s_" + k), vals(k)])} />
    </>
  );
}

export function Gauge({ score, level, grade }: { score: number; level: string; grade: string }) {
  const { t } = useDash();
  // 180 degree arc, pathLength 100 so dash values are scores. Zones match core/models.py (35 / 65).
  const arc = "M20 100A80 80 0 0 1 180 100";
  return (
    <div className="gauge" role="img" aria-label={`${t("grade")} ${grade}. ${t("riskScore", { n: score })}. ${t("lvl_" + level)}`}>
      <svg viewBox="0 0 200 112" aria-hidden="true">
        <path className="g-zone g-green" d={arc} pathLength="100" strokeDasharray="34.4 100" />
        <path className="g-zone g-yellow" d={arc} pathLength="100" strokeDasharray="0 35.3 29.4 100" />
        <path className="g-zone g-red" d={arc} pathLength="100" strokeDasharray="0 65.3 34.7 100" />
        <path className={`g-value g-${level}`} d={arc} pathLength="100" strokeDasharray={`${Math.max(0.5, Math.min(100, score))} 200`} />
      </svg>
      <div className="gauge-read"><span className="gauge-grade">{grade}</span><span className="gauge-score num">{score}<small>/100</small></span></div>
    </div>
  );
}
