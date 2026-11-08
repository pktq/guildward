import type { Metadata } from "next";
import { SetupSteps } from "@/components/site/SetupSteps";
import { installLinks } from "@/components/site/install";
import { HELP, STAGES, STEPS } from "@/lib/parents";
import "@/components/site/parents.css";

export const metadata: Metadata = {
  title: "For parents",
  description:
    "Set up Discord with your kid in about 20 minutes: safer settings, Guildward on their account, and the promise that matters most.",
};

const SAY = [
  "I looked into this because I care about you. Not because I don't trust you.",
  "If anything online ever feels wrong, scary or embarrassing, tell me. You will never be in trouble for telling me.",
  "Even if you broke a rule, sent something, or said yes to something you regret: tell me anyway. I will help, not punish.",
  "If it's too hard to tell me, tell another adult you trust, or call Bris on 116 111. Telling an adult always beats handling it alone.",
];

const KEEP: [string, string][] = [
  ["Stay calm, and thank them.", "Your first reaction decides whether they come to you next time. Be the person who was glad they told."],
  [
    "Don't take the phone or Discord away for telling.",
    "Fear of losing their phone is one of the main reasons kids keep quiet. If something has to change, decide it together, later.",
  ],
  ["Don't blame them.", "Even if they broke a rule. The person who targeted them is the one at fault, every time."],
  [
    "Don't act behind their back.",
    "No secret reading, no confronting the other person without them. Do the next steps side by side.",
  ],
];

const IF_THEY_TELL = [
  ["Listen first.", "Let them finish. Say thank you. Tell them it isn't their fault."],
  ["Don't pay and don't delete.", "Paying almost never makes threats stop. Keep the chat: it is the evidence."],
  [
    "Save the evidence.",
    "Screenshots, their username and user ID. Guildward's Save evidence button sends the details to your kid's DMs, so they survive if the other account disappears.",
  ],
  ["Report and block.", "Report the message to Discord, then block the account."],
  [
    "Get help.",
    "Pictures shared or threatened: report to the police on 114 14 (112 if it's happening now), and use Take It Down to get pictures removed. Bris is there for your kid, any time.",
  ],
];

export default function ParentsPage() {
  const install = installLinks().kid;
  return (
    <>
      <section className="pa-intro" aria-labelledby="pa-title">
        <h1 id="pa-title">Set up Discord together</h1>
        <p className="gw-lead">
          About 20 minutes, side by side. You change a few Discord settings, add Guildward to your kid&rsquo;s account,
          and make them one promise. The promise matters most.
        </p>
        <p className="pa-need">
          You need your kid&rsquo;s Discord logged in, and your own Discord account for steps 7 and 9.
        </p>
        <div className="gw-actions">
          <a className="gw-btn gw-btn-accent" href="#promise">
            Start with the promise
          </a>
          <a className="gw-textlink" href="#steps">
            Skip to the settings <span aria-hidden="true">→</span>
          </a>
        </div>
      </section>

      <section className="pa-promise" id="promise" aria-labelledby="promise-title">
        <div className="pa-promise-head">
          <h2 id="promise-title">Tell them they can always tell you</h2>
          <p className="pa-promise-lead">
            Settings stop a lot, not everything. What protects a kid most is knowing, without any doubt, that they can
            come to you, whatever happened and whatever they did.
          </p>
          <p>
            You are here, reading this, because you care. Say that out loud. Kids often don&rsquo;t know it, and the
            people who target them count on that: &ldquo;your parents will be furious&rdquo;, &ldquo;you&rsquo;ll lose
            your phone&rdquo;. A kid who is sure you won&rsquo;t react that way has nothing to be scared into silence
            with.
          </p>
        </div>
        <div className="pa-promise-body">
          <h3>Say it, in your own words</h3>
          <ul className="pa-say">
            {SAY.map((s) => (
              <li key={s}>&ldquo;{s}&rdquo;</li>
            ))}
          </ul>
          <h3>Then keep your side of it</h3>
          <dl className="pa-keep">
            {KEEP.map(([t, d]) => (
              <div key={t}>
                <dt>{t}</dt>
                <dd>{d}</dd>
              </div>
            ))}
          </dl>
          <p className="pa-promise-close">
            One angry reaction can undo the promise. Keep it most when it&rsquo;s hardest.
          </p>
        </div>
      </section>

      <section className="pa-steps" id="steps" aria-labelledby="steps-title">
        <div className="pa-steps-head">
          <h2 id="steps-title">The settings, one at a time</h2>
          <p>
            Do them together, and let your kid hold the phone. They should see everything that changes. Nothing here is
            secret.
          </p>
        </div>
        <SetupSteps steps={STEPS} install={install} />
      </section>

      <section className="pa-signs" aria-labelledby="signs-title">
        <div className="pa-signs-head">
          <h2 id="signs-title">What grooming can look like</h2>
          <p>
            It usually goes step by step, over days or weeks. Any single step can be harmless; the pattern is what
            matters. Guildward&rsquo;s checks look for these same steps.
          </p>
        </div>
        <ol className="pa-stages">
          {STAGES.map(([name, text]) => (
            <li key={name}>
              <b>{name}</b>
              <span>{text}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="pa-tell" aria-labelledby="tell-title">
        <div>
          <h2 id="tell-title">If they come to you</h2>
          <ol className="pa-tell-list">
            {IF_THEY_TELL.map(([t, d]) => (
              <li key={t}>
                <b>{t}</b> {d}
              </li>
            ))}
          </ol>
        </div>
        <div>
          <h2 className="pa-help-title">Where to get help in Sweden</h2>
          <ul className="pa-help">
            {HELP.map(([name, text, href, label]) => (
              <li key={name}>
                <b>{name}</b>
                <span>{text}</span>
                <a href={href} rel="noopener">
                  {label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="pa-end" aria-label="Closing">
        <p>
          You did something good today. Come back every few months: Discord changes, and so do kids. The promise
          doesn&rsquo;t.
        </p>
      </section>
    </>
  );
}
