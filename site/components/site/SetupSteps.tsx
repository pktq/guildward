"use client";

import { useEffect, useRef, useState } from "react";
import type { Step } from "@/lib/parents";

const KEY = "gw-parents"; // { done: string[], at: number }, this browser only

export function SetupSteps({ steps, install }: { steps: Step[]; install: string }) {
  const [done, setDone] = useState<string[]>([]);
  const [at, setAt] = useState(0);
  const [device, setDevice] = useState<"desktop" | "mobile">("desktop");
  const top = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(KEY) || "{}");
      /* eslint-disable react-hooks/set-state-in-effect -- read once after hydration; storage isn't available on the server */
      if (Array.isArray(saved.done)) setDone(saved.done.filter((x: unknown) => typeof x === "string"));
      if (Number.isInteger(saved.at) && saved.at >= 0 && saved.at < steps.length) setAt(saved.at);
      /* eslint-enable react-hooks/set-state-in-effect */
    } catch {
      // private mode or blocked storage: progress just isn't remembered
    }
  }, [steps.length]);

  function save(nextDone: string[], nextAt: number) {
    setDone(nextDone);
    setAt(nextAt);
    try {
      localStorage.setItem(KEY, JSON.stringify({ done: nextDone, at: nextAt }));
    } catch {
      // not remembered, still works
    }
  }

  function go(i: number, nextDone = done) {
    save(nextDone, i);
    const el = top.current;
    if (el && el.getBoundingClientRect().top < 0) el.scrollIntoView({ block: "start" });
    el?.focus({ preventScroll: true });
  }

  const s = steps[at];
  const isDone = done.includes(s.id);
  const lines = s.same ?? s[device] ?? [];
  const last = at === steps.length - 1;

  function finish() {
    const nextDone = isDone ? done : [...done, s.id];
    if (last) save(nextDone, at);
    else go(at + 1, nextDone);
  }

  return (
    <div className="pa-wizard" ref={top} tabIndex={-1} aria-label="Setup steps">
      <ol className="pa-strip" aria-label="Steps">
        {steps.map((x, i) => (
          <li key={x.id}>
            <button
              type="button"
              onClick={() => go(i)}
              aria-current={i === at ? "step" : undefined}
              data-done={done.includes(x.id) || undefined}
              title={x.title}
            >
              <span className="pa-strip-n">{i + 1}</span>
              <span className="pa-strip-t">{x.title}</span>
            </button>
          </li>
        ))}
      </ol>

      <article className="pa-page" aria-labelledby={`step-${s.id}`}>
        <div className="pa-page-top">
          <p className="pa-count">
            Step {at + 1} of {steps.length}
            {isDone && <span className="pa-donemark"> · done</span>}
          </p>
          {!s.same && (
            <div className="pa-device" role="group" aria-label="Instructions for">
              {(["desktop", "mobile"] as const).map((d) => (
                <button key={d} type="button" aria-pressed={device === d} onClick={() => setDevice(d)}>
                  {d === "desktop" ? "Computer" : "Phone"}
                </button>
              ))}
            </div>
          )}
        </div>
        <h3 id={`step-${s.id}`}>{s.title}</h3>
        <p className="pa-step-why">{s.why}</p>
        {s.list && (
          <ul className="pa-bullets">
            {s.list.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        )}
        {s.install && (
          <a className="gw-btn gw-btn-accent pa-install" href={install} rel="noopener">
            Add Guildward to a Discord account
          </a>
        )}
        {lines.length > 0 && (
          <ol className="pa-do">
            {lines.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ol>
        )}
        {s.see && (
          <div className="pa-see">
            <div>
              <p>{s.see.canTitle}</p>
              <ul>
                {s.see.can.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
            <div>
              <p>{s.see.cannotTitle}</p>
              <ul>
                {s.see.cannot.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
        {s.note && <p className="pa-note">{s.note}</p>}
        {s.tip && <p className="pa-tip">{s.tip}</p>}
        {s.src && (
          <p className="pa-src">
            Discord&rsquo;s help:{" "}
            {s.src.map(([label, href], j) => (
              <span key={href}>
                {j > 0 && " · "}
                <a href={href} rel="noopener">
                  {label}
                </a>
              </span>
            ))}
          </p>
        )}

        <div className="pa-nav">
          <button type="button" className="gw-btn pa-back" onClick={() => go(at - 1)} disabled={at === 0}>
            Back
          </button>
          <button type="button" className="gw-btn gw-btn-ink" onClick={finish}>
            {last ? (isDone ? "All done" : "Done") : "Done, next step"}
          </button>
          {!last && (
            <button type="button" className="pa-skip" onClick={() => go(at + 1)}>
              Skip for now
            </button>
          )}
        </div>
      </article>
    </div>
  );
}
