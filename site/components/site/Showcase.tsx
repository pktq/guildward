"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { ShieldMark } from "./ShieldMark";
import { Btn, Buttons, Dot, Embed, Field, Message } from "./discord";

type Panel = { id: string; name: string; text: string; width: number; ui: ReactNode };

function Menu({ items, open }: { items: string[]; open?: { at: string; items: string[] } }) {
  return (
    <div className="dc-menu-wrap">
      <ul className="dc-menu">
        {items.map((it) => (
          <li key={it} className={open?.at === it ? "is-hover" : undefined}>
            {it}
            {open?.at === it && <span aria-hidden="true">›</span>}
          </li>
        ))}
      </ul>
      {open && (
        <ul className="dc-menu dc-submenu">
          {open.items.map((it, i) => (
            <li key={it} className={i === 0 ? "is-hover" : undefined}>
              <ShieldMark size={16} /> {it}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const PANELS: Panel[] = [
  {
    id: "check",
    name: "/check",
    text: "Paste an invite or any link before joining or clicking. Guildward looks at what Discord shows from the outside, without joining.",
    width: 420,
    ui: (
      <div className="dc-pad">
        <div className="dc-picker">
          <p className="dc-picker-head">
            <ShieldMark size={16} /> Guildward
          </p>
          <div className="dc-picker-row is-hover">
            <b>/check</b> <span>invite_or_link</span>
            <small>Check an invite or a link before you join or click</small>
          </div>
          <div className="dc-picker-row">
            <b>/help</b>
            <small>Step-by-step help if something happened</small>
          </div>
        </div>
        <div className="dc-composer">
          <span className="dc-cmd">/check</span>
          <span className="dc-opt">invite_or_link</span>
          <span>discord.gg/pixelart</span>
        </div>
      </div>
    ),
  },
  {
    id: "safety",
    name: "Safety check",
    text: "Right-click anyone, then Apps → Safety check: account age, Discord's own spammer flag and red-flag names, in plain words.",
    width: 380,
    ui: (
      <div className="dc-pad">
        <Menu
          items={["Profile", "Mention", "Message", "Add Note", "Apps", "Block"]}
          open={{ at: "Apps", items: ["Safety check", "Report to Guildward"] }}
        />
      </div>
    ),
  },
  {
    id: "sketchy",
    name: "Is this sketchy?",
    text: "Right-click a message for grooming signs: age questions, secrets, photo requests, gifts, a push to Snapchat, threats, and any links in it.",
    width: 420,
    ui: (
      <div className="dc-pad">
        <Message name="jaylen_x" color="#e0a35b" time="Today at 21:14">
          <p>send a pic? only u and me can see this chat</p>
        </Message>
        <Menu
          items={["Add Reaction", "Reply", "Forward", "Copy Text", "Apps", "Report Message"]}
          open={{ at: "Apps", items: ["Is this sketchy?", "Report to Guildward"] }}
        />
      </div>
    ),
  },
  {
    id: "forward",
    name: "Forward it",
    text: "Forward any message to Guildward's DMs for the same check. Several forwards are read together as one conversation.",
    width: 440,
    ui: (
      <div className="dc-pad">
        <Message name="you" color="#74aee3" time="Today at 19:48">
          <div className="dc-forward">
            <p className="dc-forward-label">Forwarded</p>
            <p>whats ur school called? i might be near there saturday</p>
          </div>
        </Message>
        <Message name="Guildward" bot time="Today at 19:48">
          <Embed
            level="yellow"
            title={
              <>
                <Dot level="yellow" /> This message has warning signs
              </>
            }
          >
            <Field name="What to do">
              Don&rsquo;t answer personal questions or move to another app. Show the chat to an adult you trust.
            </Field>
            <Field name="Want a better check?">
              A forward doesn&rsquo;t tell me who sent it. Use <b>Apps → Is this sketchy?</b> on the message instead,
              and I can also check the account and warn other kids.
            </Field>
          </Embed>
        </Message>
      </div>
    ),
  },
  {
    id: "help",
    name: "/help",
    text: "Calm steps for sextortion, picture requests, someone who wants to meet, scams and bullying. Nothing a kid picks here is saved.",
    width: 460,
    ui: (
      <div className="dc-pad">
        <Embed
          level="blue"
          title="Get help"
          description={
            <>
              Pick what&rsquo;s happening below for clear steps, one at a time.
            </>
          }
        />
        <div className="dc-select">
          <p className="dc-select-head">What&rsquo;s happening?</p>
          <ul>
            <li className="is-hover">
              <b>Someone threatens to share my pictures</b>
              <small>They want money, more pictures, or something else</small>
            </li>
            <li>
              <b>Someone asks for pictures or sends sexual stuff</b>
              <small>Nudes, sexual chat, or pictures you didn&rsquo;t want</small>
            </li>
            <li>
              <b>Someone wants to meet or knows where I live</b>
              <small>Asks where you live, your school, or to meet up</small>
            </li>
            <li>
              <b>Bullying, hate or threats</b>
              <small>Mean messages, being shut out on purpose, or threats</small>
            </li>
          </ul>
        </div>
      </div>
    ),
  },
  {
    id: "watch",
    name: "Watch alerts",
    text: "If an account a kid checked is later flagged, confirmed dangerous or deleted, Guildward sends them a DM.",
    width: 400,
    ui: (
      <div className="dc-pad">
        <Message name="Guildward" bot time="Yesterday at 08:15">
          <Embed
            level="grey"
            title="That account is gone"
            description={
              <>
                <b>jaylen_x</b>, who sent you something worrying, deleted their account. People who do this often come
                back with a new one. If someone new writes the same kind of things, it may be them.
              </>
            }
            footer="You get this because you checked this account. Turn it off: /guildward settings"
          />
          <Buttons>
            <Btn kind="link">Find a helpline in your country</Btn>
            <Btn kind="link">How to report on Discord</Btn>
          </Buttons>
        </Message>
      </div>
    ),
  },
  {
    id: "scan",
    name: "Server scan",
    text: "With the kid's OK on Discord's own page, Guildward flags risky servers they're in, then checks the new ones every day.",
    width: 440,
    ui: (
      <div className="dc-pad">
        <Message name="Guildward" bot time="Today at 07:00">
          <Embed
            level="red"
            title="Your 14 servers: 2 need a closer look"
            description={
              <ul className="dc-lines">
                <li>
                  <Dot level="red" />
                  <span>
                    <b>free robux hub</b>: The server is brand new (3 days old). Bad servers are often new and
                    short-lived.
                  </span>
                </li>
                <li>
                  <Dot level="yellow" />
                  <span>
                    <b>late night vc</b>: Anyone can post right away, even accounts made a minute ago.
                  </span>
                </li>
              </ul>
            }
            footer="Based on what Discord shows from the outside. Stop scans: /guildward forget"
          />
        </Message>
      </div>
    ),
  },
];

export function Showcase() {
  const scroller = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    let raf = 0;
    const measure = () => {
      raf = 0;
      const mid = el.getBoundingClientRect().left + el.clientWidth / 2;
      let best = 0;
      let dist = Infinity;
      [...el.children].forEach((c, i) => {
        const r = c.getBoundingClientRect();
        const d = Math.abs(r.left + r.width / 2 - mid);
        if (d < dist) [best, dist] = [i, d];
      });
      setActive(best);
    };
    const onScroll = () => (raf ||= requestAnimationFrame(measure));
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      el.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  function go(i: number) {
    const el = scroller.current;
    const target = el?.children[i] as HTMLElement | undefined;
    if (!el || !target) return;
    const smooth = !matchMedia("(prefers-reduced-motion: reduce)").matches;
    const box = el.getBoundingClientRect();
    const r = target.getBoundingClientRect(); // rects, not offsets: the slots are scaled with CSS zoom
    el.scrollTo({
      left: el.scrollLeft + r.left + r.width / 2 - (box.left + el.clientWidth / 2),
      behavior: smooth ? "smooth" : "auto",
    });
  }

  const p = PANELS[active];
  return (
    <section className="gw-show" aria-labelledby="show-title">
      <h2 id="show-title" className="gw-sr">
        Every way a kid can ask
      </h2>
      <div
        className="gw-show-row"
        ref={scroller}
        tabIndex={0}
        role="group"
        aria-roledescription="carousel"
        aria-label="Guildward in Discord, one feature per panel. Use the arrow keys or the buttons to move."
      >
        {PANELS.map((panel, i) => (
          <div
            key={panel.id}
            className="gw-show-slot"
            data-active={i === active || undefined}
            style={{ width: panel.width }}
            onClick={() => i !== active && go(i)}
          >
            <div className="gw-show-panel dc dc-light" data-ui="" inert={i !== active} aria-label={panel.name}>
              {panel.ui}
            </div>
          </div>
        ))}
      </div>
      <div className="gw-show-caption" aria-live="polite">
        <p className="gw-show-name">{p.name}</p>
        <p className="gw-show-text">{p.text}</p>
        <div className="gw-show-nav">
          <button
            type="button"
            className="gw-roundbtn"
            onClick={() => go(Math.max(0, active - 1))}
            disabled={active === 0}
            aria-label="Previous feature"
          >
            <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
              <path d="M15 5 8 12l7 7" fill="none" stroke="currentColor" strokeWidth="2.5" />
            </svg>
          </button>
          <button
            type="button"
            className="gw-roundbtn"
            onClick={() => go(Math.min(PANELS.length - 1, active + 1))}
            disabled={active === PANELS.length - 1}
            aria-label="Next feature"
          >
            <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
              <path d="m9 5 7 7-7 7" fill="none" stroke="currentColor" strokeWidth="2.5" />
            </svg>
          </button>
        </div>
      </div>
    </section>
  );
}
