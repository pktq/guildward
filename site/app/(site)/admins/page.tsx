import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import { SetupSteps } from "@/components/site/SetupSteps";
import { installLinks } from "@/components/site/install";
import { GUARD_STEPS } from "@/lib/admins";
import "@/components/site/parents.css";

export const metadata: Metadata = {
  title: "For server admins",
  description:
    "Guard watches your Discord server for grooming, sextortion setups, scams and raids, and tells your moderators what it saw and why. Message text is never stored.",
};

const SOURCES: [title: string, href: string][] = [
  [
    "NCMEC, Sextortion: What Parents Should Know (2024)",
    "https://www.missingkids.org/content/dam/netsmartz/downloadable/tipsheets/sextortion-what-parents-should-know.pdf",
  ],
  [
    "Thorn & NCMEC, Trends in Financial Sextortion (June 2024)",
    "https://info.thorn.org/hubfs/Research/Thorn_TrendsInFinancialSextortion_June2024.pdf",
  ],
  [
    "FBI and international partners, joint warning about a global financial sextortion crisis (7 February 2023)",
    "https://www.fbi.gov/news/press-releases/international-law-enforcement-agencies-issue-joint-warning-about-global-financial-sextortion-crisis",
  ],
];

function Ref({ n }: { n: number }) {
  return (
    <sup className="pa-ref">
      <a href={`#source-${n}`} aria-label={`Source ${n}`}>
        {n}
      </a>
    </sup>
  );
}

const WHY: [string, ReactNode][] = [
  [
    "It starts where kids already are.",
    <>
      NCMEC describes the pattern: contact on a platform the child uses, learning about their interests, friends and
      school, then a push to a second or third app with encrypted messages.
      <Ref n={1} /> A busy server is that first platform.
    </>,
  ],
  [
    "The script repeats.",
    <>
      Investigators find the same, often identical, threats across many cases.
      <Ref n={2} /> The setup before them repeats too: age questions, &ldquo;add me on snap&rdquo;, &ldquo;don&rsquo;t
      tell anyone&rdquo;, aimed at the same few kids. That is what makes it catchable.
    </>,
  ],
  [
    "Moderators can't read everything.",
    "In a server with thousands of messages a day, the move to DMs is easy to miss. It is also the last moment anyone on the server can still see it happen.",
  ],
];

const DOES: [string, string][] = [
  [
    "One alert per person, not a stream.",
    "Alerts go to your private mod channel. If someone keeps going, the same alert grows, with buttons for timeout, kick, ban, delete and watch. I'm on it shows who is handling it, and resolving or marking a false alarm takes an optional note.",
  ],
  [
    "Reasons in plain words.",
    "Every alert says what Guard saw, who it was aimed at, whether they are under 18 and how new the account is. Each member gets a score with reasons and a rising or falling trend.",
  ],
  [
    "Patterns, not just words.",
    "Guard follows each contact between two members through the grooming stages: trust, age and risk checks, secrecy, moving to another app, sexual talk or pictures, meeting up. Adult-to-minor contact counts far more than kids talking to kids.",
  ],
  [
    "A calm word to the kid.",
    "When a member under 18 receives a red message, Guard sends them a short DM: what it saw, don't reply, show an adult, and who they can talk to.",
  ],
  [
    "Raids and scams too.",
    "Join bursts, cross-channel spam, scam links and mass mentions are flagged, and in protect mode raid accounts are quarantined.",
  ],
  [
    "A dashboard for the team.",
    "Server health, an A to F grade, alerts, members, full person reports with a timeline, settings and a printable report. Your team signs in with Discord; you choose which roles can view or act.",
  ],
];

const KEEPS: [string, string][] = [
  ["Message text is never stored.", "Guard reads each message in memory, keeps the warning sign it found and the IDs involved, and lets the text go. An alert can show the message in Discord; Guard itself doesn't keep it."],
  ["Data has an end date.", "Signals and scores are deleted after 90 days by default. You can set anything from 7 to 365 days."],
  ["You can wipe it.", "/guard erase removes everything Guard holds about the server. It needs Administrator or the server owner."],
  ["Only your team sees it.", "Commands need Manage Server. The dashboard lets in admins and the roles you pick, checked against each person's current roles on every request. Alerts only go to a channel @everyone can't see."],
];

export default function AdminsPage() {
  const links = installLinks();
  return (
    <>
      <section className="pa-intro" aria-labelledby="ad-title">
        <h1 id="ad-title">Guard for your server</h1>
        <p className="gw-lead">
          Guard watches every channel for grooming, sextortion setups, scams and raids, and tells your moderators what it
          saw and why. Setup takes about ten minutes.
        </p>
        <div className="gw-actions pa-cta">
          <a className="gw-btn gw-btn-accent" href={links.guard} rel="noopener">
            Add Guard to your server
          </a>
          <Link className="gw-textlink" href="/dashboard">
            Open the dashboard <span aria-hidden="true">→</span>
          </Link>
        </div>
        <nav className="pa-toc" aria-label="On this page">
          <a href="#why">Why servers</a>
          <a href="#does">What Guard does</a>
          <a href="#keeps">What it keeps</a>
          <a href="#setup">Set it up</a>
        </nav>
      </section>

      <section className="pa-how" id="why" aria-labelledby="why-title">
        <div className="pa-side">
          <h2 id="why-title">Why your server matters</h2>
          <p>
            The FBI, the UK&rsquo;s National Crime Agency and police in Australia, Canada and New Zealand have warned
            together that financial sextortion of kids is a global crisis.
            <Ref n={3} />
          </p>
        </div>
        <ol className="pa-facts">
          {WHY.map(([t, d]) => (
            <li key={t}>
              <b>{t}</b>
              <p>{d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="pa-tell" id="does" aria-labelledby="does-title">
        <div className="pa-side">
          <h2 id="does-title">What Guard does</h2>
          <p>
            Observe mode only alerts; your moderators decide. Protect mode also deletes the worst messages aimed at
            minors and times out members who turn red until a moderator looks.
          </p>
        </div>
        <ol className="pa-facts">
          {DOES.map(([t, d]) => (
            <li key={t}>
              <b>{t}</b>
              <p>{d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="pa-happens" id="keeps" aria-labelledby="keeps-title">
        <div className="pa-side">
          <h2 id="keeps-title">What Guard keeps</h2>
          <p>Enough to see a pattern. Not enough to read anyone&rsquo;s conversations.</p>
        </div>
        <ol className="pa-facts">
          {KEEPS.map(([t, d]) => (
            <li key={t}>
              <b>{t}</b>
              <p>{d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="pa-setup" id="setup" aria-labelledby="setup-title">
        <div className="pa-setup-head">
          <h2 id="setup-title">Set it up</h2>
          <p>Nine steps. You need Manage Server, and a moderator role for the alert channel.</p>
        </div>
        <SetupSteps steps={GUARD_STEPS} install={{ guard: links.guard }} storageKey="gw-admins" />
      </section>

      <section className="pa-sources" aria-labelledby="sources-title">
        <h2 id="sources-title">Sources</h2>
        <ol>
          {SOURCES.map(([title, href], i) => (
            <li key={href} id={`source-${i + 1}`}>
              <a href={href} rel="noopener">
                {title}
              </a>
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}
