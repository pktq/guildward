"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { Btn, Buttons, Dot, Embed, Field, Message } from "./discord";

type Note = { part: string; name: string; text: string; side: "left" | "right" };

const NOTES: Note[] = [
  {
    part: "title",
    side: "left",
    name: "One alert per person",
    text: "If they keep going, the same alert grows. Mods get one case, not a stream.",
  },
  {
    part: "why",
    side: "left",
    name: "Reasons in plain words",
    text: "Every alert lists what Guard saw, who it was aimed at and how new the account is.",
  },
  {
    part: "message",
    side: "left",
    name: "Shown once, never stored",
    text: "Mods see the message in the alert. Guard keeps only signal codes and IDs.",
  },
  {
    part: "risk",
    side: "right",
    name: "A score that adds up",
    text: "Profile, stated age, messages, who they target and patterns over time.",
  },
  {
    part: "act",
    side: "right",
    name: "Act from the alert",
    text: "Timeout, kick, ban or delete in one press. Guard never asks for Administrator.",
  },
  {
    part: "close",
    side: "right",
    name: "Close it honestly",
    text: "Watch, resolved or false alarm. False alarms are counted so weak signals show up.",
  },
];

export function GuardPlate() {
  const panel = useRef<HTMLDivElement>(null);
  const [tops, setTops] = useState<Record<string, number> | null>(null);
  const [focus, setFocus] = useState<string | null>(null);
  const notes = useRef<Record<string, HTMLLIElement | null>>({});

  useLayoutEffect(() => {
    const el = panel.current;
    if (!el) return;
    const measure = () => {
      const base = el.getBoundingClientRect().top;
      const next: Record<string, number> = {};
      el.querySelectorAll<HTMLElement>("[data-part]").forEach((p) => {
        next[p.dataset.part!] = Math.round(p.getBoundingClientRect().top - base);
      });
      // Level each note with its part, but never let a note run into the one above it.
      for (const side of ["left", "right"] as const) {
        let floor = 0;
        for (const n of NOTES.filter((x) => x.side === side)) {
          const h = notes.current[n.part]?.offsetHeight ?? 0;
          next[n.part] = Math.max(next[n.part], floor);
          floor = next[n.part] + h + 20;
        }
      }
      setTops(next);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const note = (n: Note) => (
    <li
      key={n.part}
      ref={(li) => {
        notes.current[n.part] = li;
      }}
      style={tops ? { top: tops[n.part] } : undefined}
    >
      <button
        type="button"
        className="gw-note"
        aria-pressed={focus === n.part}
        onPointerEnter={() => setFocus(n.part)}
        onPointerLeave={() => setFocus(null)}
        onFocus={() => setFocus(n.part)}
        onBlur={() => setFocus(null)}
      >
        <span className="gw-note-name">{n.name}</span>
        <span className="gw-note-text">{n.text}</span>
      </button>
    </li>
  );

  return (
    <div className="gw-plate" data-measured={tops ? "" : undefined}>
      <ul className="gw-plate-notes gw-plate-left">{NOTES.filter((n) => n.side === "left").map(note)}</ul>
      <div className="gw-plate-panel dc" data-ui="" ref={panel} data-focus={focus ?? undefined}>
        <p className="dc-channel"># mod-alerts</p>
        <Message name="Guildward" bot time="Today at 20:31">
          <Embed
            level="red"
            part="title"
            title={
              <>
                <Dot level="red" /> Pulling a member into DMs or another app
              </>
            }
            description="nightowl99 → lily in #art-share."
            footer="Guildward Guard · alert #214 · message text is never stored"
          >
            <Field name="Why" part="why">
              <ul className="dc-reasons">
                <li>
                  <span className="dc-glyph dc-glyph-severe">!!</span>{" "}
                  <span>Tried to move the chat to another app</span>
                </li>
                <li>
                  <span className="dc-glyph dc-glyph-severe">!!</span> <span>Asked someone&rsquo;s age</span>
                </li>
                <li>
                  <span className="dc-glyph dc-glyph-bullet">•</span> <span>Aimed at a member who is under 18.</span>
                </li>
                <li>
                  <span className="dc-glyph dc-glyph-bullet">•</span>{" "}
                  <span>Sender&rsquo;s account is 12 days old.</span>
                </li>
              </ul>
            </Field>
            <Field name="Message (not stored by Guard)" part="message">
              <code className="dc-code">how old r u? add me on snap, its easier there</code>
            </Field>
            <div className="dc-inline-fields" data-part="risk">
              <Field name="Who">
                <span className="dc-mention">@nightowl99</span> → <span className="dc-mention">@lily</span>{" "}
                <span className="dc-minor">under 18</span>
              </Field>
              <Field name="Risk">
                <b>78/100</b>
              </Field>
            </div>
            <p className="dc-jump">
              <span className="dc-link">Jump to message</span> · <span className="dc-link">Full report</span>
            </p>
          </Embed>
          <Buttons part="act">
            <Btn>Timeout 1h</Btn>
            <Btn>Kick</Btn>
            <Btn kind="danger">Ban</Btn>
            <Btn>Delete message</Btn>
          </Buttons>
          <Buttons part="close">
            <Btn>Watch</Btn>
            <Btn kind="success">Resolved</Btn>
            <Btn>False alarm</Btn>
            <Btn kind="link">Open dashboard</Btn>
          </Buttons>
        </Message>
      </div>
      <ul className="gw-plate-notes gw-plate-right">{NOTES.filter((n) => n.side === "right").map(note)}</ul>
    </div>
  );
}
