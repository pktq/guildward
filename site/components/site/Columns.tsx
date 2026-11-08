"use client";

import { useState, type KeyboardEvent } from "react";

const nf = new Intl.NumberFormat("en");

/** Daily columns standing on one baseline. One series: the title names it, so there is no legend.
 * `days` are display labels, formatted on the server so hydration can't disagree about them. */
export function Columns({
  days,
  values,
  unit,
  label,
  tone = "light",
  height,
}: {
  days: string[];
  values: number[];
  unit: string;
  label: string;
  tone?: "light" | "dark";
  height: string;
}) {
  const [at, setAt] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  const max = Math.max(0, ...values);
  const peak = max > 0 ? values.indexOf(max) : -1;
  const last = values.length - 1;
  const marked = new Set([peak, values[last] > 0 ? last : -1].filter((i) => i >= 0));
  const total = values.reduce((a, b) => a + b, 0);

  function onKey(e: KeyboardEvent) {
    const cur = at ?? last;
    const next = { ArrowRight: cur + 1, ArrowLeft: cur - 1, Home: 0, End: last }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    setAt(Math.max(0, Math.min(last, next)));
  }

  const show = at ?? null;
  return (
    <figure className={`gw-cols gw-cols-${tone}`}>
      <div
        className="gw-cols-plot"
        style={{ height, gridTemplateColumns: `repeat(${values.length}, minmax(0, 1fr))` }}
        tabIndex={0}
        role="img"
        aria-label={`${label}: ${nf.format(total)} over ${values.length} days, from ${days[0]} to ${days[last]}. Highest ${nf.format(max)}${peak >= 0 ? ` on ${days[peak]}` : ""}. Use the arrow keys to read each day.`}
        onKeyDown={onKey}
        onBlur={() => setAt(null)}
        onPointerLeave={() => setAt(null)}
      >
        {values.map((v, i) => (
          <div
            key={days[i]}
            className="gw-col"
            data-peak={i === peak || undefined}
            data-on={i === show || undefined}
            onPointerEnter={() => setAt(i)}
          >
            {v > 0 && <span className="gw-col-bar" style={{ height: `${(v / max) * 100}%` }} />}
            {marked.has(i) && show === null && (
              <span className="gw-col-val" style={{ bottom: `${(v / max) * 100}%` }}>
                {nf.format(v)}
              </span>
            )}
            {i === show && (
              <span
                className="gw-col-tip"
                style={{ bottom: `${max ? (v / max) * 100 : 0}%` }}
                data-side={i > last * 0.7 ? "left" : undefined}
              >
                <b>{nf.format(v)}</b> {unit}
                <br />
                {days[i]}
              </span>
            )}
          </div>
        ))}
      </div>
      <figcaption className="gw-cols-axis">
        <span>{days[0]}</span>
        <span>{days[last]}</span>
      </figcaption>
      <details className="gw-table" onToggle={(e) => setTable(e.currentTarget.open)}>
        <summary>Show as a table</summary>
        {table && (
          <div className="gw-table-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">Day</th>
                  <th scope="col">{unit[0].toUpperCase() + unit.slice(1)}</th>
                </tr>
              </thead>
              <tbody>
                {values.map((v, i) => (
                  <tr key={days[i]}>
                    <td>{days[i]}</td>
                    <td data-zero={v === 0 || undefined}>{nf.format(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </details>
    </figure>
  );
}
