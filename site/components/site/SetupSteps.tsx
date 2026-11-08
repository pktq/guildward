"use client";

import { useEffect, useState } from "react";
import type { Step } from "@/lib/parents";

const KEY = "gw-parents-done";

export function SetupSteps({ steps, install }: { steps: Step[]; install: string }) {
  const [done, setDone] = useState<string[]>([]);
  const [device, setDevice] = useState<"desktop" | "mobile">("desktop");

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(KEY) || "[]");
      // eslint-disable-next-line react-hooks/set-state-in-effect -- read once after hydration; storage isn't available on the server
      if (Array.isArray(saved)) setDone(saved.filter((x) => typeof x === "string"));
    } catch {
      // private mode or blocked storage: ticks just aren't remembered
    }
  }, []);

  function toggle(id: string) {
    const next = done.includes(id) ? done.filter((x) => x !== id) : [...done, id];
    setDone(next);
    try {
      localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      // not remembered, still works
    }
  }

  const count = steps.filter((s) => done.includes(s.id)).length;
  return (
    <div className="pa-steplist">
      <div className="pa-stepbar">
        <p aria-live="polite">
          <b>{count}</b> of {steps.length} done
        </p>
        <div className="pa-device" role="group" aria-label="Instructions for">
          {(["desktop", "mobile"] as const).map((d) => (
            <button key={d} type="button" aria-pressed={device === d} onClick={() => setDevice(d)}>
              {d === "desktop" ? "Computer" : "Phone"}
            </button>
          ))}
        </div>
      </div>
      <ol>
        {steps.map((s, i) => {
          const lines = s.same ?? s[device] ?? [];
          const isDone = done.includes(s.id);
          return (
            <li key={s.id} className="pa-step" data-done={isDone || undefined} id={`step-${s.id}`}>
              <p className="pa-num" aria-hidden="true">
                {i + 1}
              </p>
              <div className="pa-step-body">
                <h3>{s.title}</h3>
                <p className="pa-why">{s.why}</p>
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
                  <ol className="pa-how">
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
                <div className="pa-step-foot">
                  <label className="pa-check">
                    <input type="checkbox" checked={isDone} onChange={() => toggle(s.id)} />
                    <span>We did this together</span>
                  </label>
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
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
