"use client";

import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Btn, Buttons, Dot, Embed, Field, Message, Reasons } from "./discord";

const FOOT = "Guildward · Only you can see this · Message text is never saved";
const OUTSIDE = "Based only on what anyone can see from the outside. A hint, not proof.";

type Example = { id: string; tab: string; used: string; origin: ReactNode; result: ReactNode };

const EXAMPLES: Example[] = [
  {
    id: "message",
    tab: "A message",
    used: "Is this sketchy?",
    origin: (
      <Message name="jaylen_x" color="#e0a35b" time="Today at 21:14">
        <p>ur really mature for 13 tbh. add me on snap? easier to talk there. dont tell ur mom lol</p>
      </Message>
    ),
    result: (
      <Embed
        level="red"
        title={
          <>
            <Dot level="red" /> This message is a serious warning sign
          </>
        }
        description="Message from jaylen_x"
        footer={FOOT}
      >
        <Field name="Why">
          <Reasons
            items={[
              [
                "warn",
                "Lays on the compliments, like saying you're mature or that only they get you. Tricksters often start this way.",
              ],
              [
                "warn",
                "Wants you to move to Snapchat. People who pull you off Discord may want a place where no one is watching.",
              ],
              [
                "warn",
                "Asks you to keep secrets or hide things from your parents. Safe people don't ask you to hide things.",
              ],
              [
                "info",
                "This is warning sign #3 from this person in the last two weeks. So far: Trust building, Isolation, Secrecy.",
              ],
            ]}
          />
        </Field>
        <Field name="What to do">
          Stop replying. Don&rsquo;t send anything, don&rsquo;t delete the chat, and show it to an adult you trust now.
          Report the message (right-click → Report) and block them. Need someone to talk to? <b>I need help</b> shows
          who you can call where you live.
        </Field>
        <Buttons>
          <Btn kind="primary">I need help</Btn>
          <Btn>Save evidence</Btn>
          <Btn kind="danger">Report to Guildward</Btn>
        </Buttons>
      </Embed>
    ),
  },
  {
    id: "person",
    tab: "A person",
    used: "Safety check",
    origin: (
      <Message name="mia.draws" color="#9aa3ad" time="Today at 18:02">
        <p>hey i saw ur art in the server!! can i dm u? i have something to show u</p>
      </Message>
    ),
    result: (
      <Embed
        level="yellow"
        title={
          <>
            <Dot level="yellow" /> Be careful with this person
          </>
        }
        description="mia.draws"
        footer={FOOT}
      >
        <Field name="Why">
          <Reasons
            items={[
              ["warn", "This account is only 9 days old. Brand-new accounts are a common warning sign."],
              ["info", "No profile picture."],
            ]}
          />
        </Field>
        <Field name="What to do">
          Don&rsquo;t accept a friend request just because they&rsquo;re in the same server. Never move to another app
          with them.
        </Field>
        <Field name="How sure">
          Risk <b>41/100</b>
          <br />
          {OUTSIDE}
        </Field>
        <Buttons>
          <Btn kind="primary">I need help</Btn>
          <Btn>Save evidence</Btn>
          <Btn kind="link">How to report</Btn>
        </Buttons>
      </Embed>
    ),
  },
  {
    id: "link",
    tab: "A link",
    used: "/check",
    origin: (
      <Message name="nitro drops" color="#c58be0" time="Today at 16:40">
        <p>
          free nitro for the first 50 people, claim fast <span className="dc-link">https://dlscord-gift.com/claim</span>
        </p>
      </Message>
    ),
    result: (
      <Embed
        level="red"
        title={
          <>
            <Dot level="red" /> Don&rsquo;t click this link
          </>
        }
        description="dlscord-gift.com/claim"
        footer={FOOT}
      >
        <Field name="Why">
          <Reasons
            items={[
              [
                "warn",
                "dlscord-gift.com is made to look like Discord but it is NOT Discord. Scammers copy names with small spelling tricks.",
              ],
              [
                "warn",
                "It talks about free Nitro, Robux, skins or gifts. Free stuff like that is almost always a scam.",
              ],
              ["warn", "The website was created only 6 days ago. Scam sites are usually brand new."],
            ]}
          />
        </Field>
        <Field name="What to do">
          Don&rsquo;t open it and don&rsquo;t log in through it. Open Discord (or the app) yourself instead. Tell a
          grown-up and block whoever sent it.
        </Field>
        <Buttons>
          <Btn kind="primary">I need help</Btn>
          <Btn kind="link">How to report</Btn>
        </Buttons>
      </Embed>
    ),
  },
  {
    id: "server",
    tab: "A server",
    used: "/check",
    origin: (
      <Message name="noor" color="#6cc59a" time="Today at 15:21">
        <p>
          join this one its all drawing stuff <span className="dc-link">discord.gg/pixelart</span>
        </p>
      </Message>
    ),
    result: (
      <Embed
        level="green"
        title={
          <>
            <Dot level="green" /> No warning signs found
          </>
        }
        description={
          <>
            <b>Pixel Art Club</b> · 2,418 members
          </>
        }
        footer={FOOT}
      >
        <Field name="Why">
          <Reasons
            items={[
              ["ok", "The server has existed for 3+ years."],
              ["ok", "New accounts must wait or verify a phone before posting."],
            ]}
          />
        </Field>
        <Field name="What to do">
          Looks fine from the outside. Still: never share your age, school or other apps with strangers there.
        </Field>
        <Field name="How sure">
          Risk <b>8/100</b>
          <br />
          {OUTSIDE}
        </Field>
        <Buttons>
          <Btn kind="primary">I need help</Btn>
        </Buttons>
      </Embed>
    ),
  },
];

const HOLD = 6500;

export function HeroCheck() {
  const [active, setActive] = useState(0);
  const [auto, setAuto] = useState(true);
  const [paused, setPaused] = useState(false);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!auto || paused || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let visible = true;
    const io = new IntersectionObserver(([e]) => (visible = e.isIntersecting));
    if (root.current) io.observe(root.current);
    const t = setInterval(() => {
      if (visible && document.visibilityState === "visible") setActive((a) => (a + 1) % EXAMPLES.length);
    }, HOLD);
    return () => {
      clearInterval(t);
      io.disconnect();
    };
  }, [auto, paused]);

  function choose(i: number, focus = false) {
    setAuto(false);
    setActive(i);
    if (focus) tabs.current[i]?.focus();
  }

  function onKey(e: KeyboardEvent) {
    const n = EXAMPLES.length;
    const next = { ArrowRight: active + 1, ArrowLeft: active - 1 + n, Home: 0, End: n - 1 }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    choose(next % n, true);
  }

  return (
    <div
      className="gw-check"
      ref={root}
      onPointerEnter={() => setPaused(true)}
      onPointerLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <div className="gw-check-tabs" role="tablist" aria-label="Try an example check" onKeyDown={onKey}>
        {EXAMPLES.map((ex, i) => (
          <button
            key={ex.id}
            ref={(el) => {
              tabs.current[i] = el;
            }}
            role="tab"
            id={`check-tab-${ex.id}`}
            aria-selected={i === active}
            aria-controls={`check-panel-${ex.id}`}
            tabIndex={i === active ? 0 : -1}
            className="gw-check-tab"
            onClick={() => choose(i)}
          >
            {ex.tab}
          </button>
        ))}
      </div>
      <div className="gw-check-stack">
        {EXAMPLES.map((ex, i) => (
          <div
            key={ex.id}
            role="tabpanel"
            id={`check-panel-${ex.id}`}
            aria-labelledby={`check-tab-${ex.id}`}
            className="gw-check-panel dc"
            data-ui=""
            data-active={i === active || undefined}
            inert={i !== active}
          >
            {ex.origin}
            <p className="dc-used">
              <span className="dc-used-curve" aria-hidden="true" />
              You used <b>{ex.used}</b>
            </p>
            <Message name="Guildward" bot time="Today" ephemeral>
              {ex.result}
            </Message>
          </div>
        ))}
      </div>
      <p className="gw-check-note">An example in Guildward&rsquo;s own words. The names and numbers are made up.</p>
    </div>
  );
}
