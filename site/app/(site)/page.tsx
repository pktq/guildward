import Link from "next/link";
import { Btn, Buttons, Dot, Embed, Field, Message } from "@/components/site/discord";
import { DoorFilm } from "@/components/site/DoorFilm";
import { GuardPlate } from "@/components/site/GuardPlate";
import { HeroCheck } from "@/components/site/HeroCheck";
import { InstallDialog } from "@/components/site/InstallDialog";
import { installLinks } from "@/components/site/install";
import { Showcase } from "@/components/site/Showcase";

const FAQ: [string, React.ReactNode][] = [
  [
    "Does Guildward read my kid's messages?",
    <>
      Only the ones your kid chooses to check or forward. In a server that has switched on Guard, the bot reads messages
      in memory to look for warning signs, then keeps only signal codes and IDs. The text itself is never stored.
    </>,
  ],
  [
    "Who sees the answers?",
    <>
      In the kids&rsquo; app, every reply is visible only to the kid who asked. In a Guard server, alerts go to a
      private channel for the moderators.
    </>,
  ],
  [
    "Will I hear about it as a parent?",
    <>
      Only if your kid chooses. They can name a trusted adult with <code>/guildward adult</code>, and that adult hears
      from Guildward when they press &ldquo;Tell my trusted adult&rdquo; under a result. Nothing goes to an adult behind
      a kid&rsquo;s back. <Link href="/parents#setup">How to set it up together</Link>.
    </>,
  ],
  [
    "Does it work in DMs and group chats?",
    <>
      Yes. Kids install Guildward on their own Discord account, so the checks work in DMs, group chats and any server,
      including servers that don&rsquo;t use Guildward.
    </>,
  ],
  [
    "What if it gets something wrong?",
    <>
      Every answer says how sure it is, and a check based on what Discord shows from the outside says plainly that
      it&rsquo;s a hint, not proof. In Guard, moderators decide what happens, and a False alarm button feeds back into
      which signals can be trusted.
    </>,
  ],
  [
    "What does Guard need permission to do?",
    <>
      Exactly what its buttons do: read and manage messages, timeout, kick, ban, manage roles and server settings for
      the one-click fixes, and view the audit log. Never Administrator. A checks-only server install reads nothing.
    </>,
  ],
  [
    "Which languages does it speak?",
    <>
      English and Swedish, following each kid&rsquo;s Discord language. In <code>/help</code>, kids pick where they
      live and get local numbers: Sweden, the US, the UK, Australia and Canada so far, and services that work in every
      other country.
    </>,
  ],
  [
    "Do I need to host or set up anything?",
    <>
      No. Guildward runs on our servers: add it from Discord and it works straight away. The detection rules and the
      message model are ours and stay private, so abusers can&rsquo;t read them and phrase around them.
    </>,
  ],
];

export default function Home() {
  const links = installLinks();
  return (
    <>
      <section className="gw-hero" aria-labelledby="hero-title">
        <div className="gw-hero-text">
          <h1 id="hero-title">Is this sketchy?</h1>
          <p className="gw-lead">
            Guildward is a Discord app against sextortion and grooming. A kid checks a server, a person, a message or
            a link in two clicks and gets a plain answer: green, yellow or red, why, and what to do.
          </p>
          <div className="gw-actions">
            <a className="gw-btn gw-btn-accent" href="#install">
              Add to Discord
            </a>
            <Link className="gw-textlink" href="/parents">
              For parents <span aria-hidden="true">→</span>
            </Link>
            <Link className="gw-textlink" href="/admins">
              For server admins <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
        <div className="gw-hero-stage">
          <HeroCheck />
        </div>
      </section>

      <DoorFilm />

      <section className="gw-stakes" aria-labelledby="stakes-title">
        <div className="gw-stakes-head">
          <h2 id="stakes-title">Sextortion is a worldwide crime against kids</h2>
          <p>
            Organized groups run it as a script: a friendly profile, a picture sent first, one asked back, then a demand
            for money. The FBI, the UK&rsquo;s National Crime Agency and police in Australia, Canada and New Zealand
            have warned about it together as a global crisis.
          </p>
          <Link className="gw-textlink" href="/parents">
            What parents should know <span aria-hidden="true">→</span>
          </Link>
        </div>
        <dl className="gw-stakes-figs">
          <div>
            <dt>minor victims counted by the FBI in a year and a half, with more than 20 suicides linked to it</dt>
            <dd>12,600+</dd>
          </div>
          <div>
            <dt>of financial sextortion victims in NCMEC&rsquo;s reports are boys aged 14 to 17</dt>
            <dd>90%</dd>
          </div>
          <div>
            <dt>sextortion reports reach NCMEC in an average week</dt>
            <dd>812</dd>
          </div>
        </dl>
        <p className="gw-stakes-src">
          Sources:{" "}
          <a href="https://www.fbi.gov/news/stories/the-financially-motivated-sextortion-threat" rel="noopener">
            FBI
          </a>{" · "}
          <a href="https://info.thorn.org/hubfs/Research/Thorn_TrendsInFinancialSextortion_June2024.pdf" rel="noopener">
            Thorn &amp; NCMEC, 2024
          </a>{" · "}
          <a href="https://www.fbi.gov/news/press-releases/international-law-enforcement-agencies-issue-joint-warning-about-global-financial-sextortion-crisis" rel="noopener">
            Joint warning, 2023
          </a>
        </p>
      </section>

      <Showcase />

      <section className="gw-help" aria-labelledby="help-title">
        <div className="gw-help-text" data-reveal>
          <h2 id="help-title">When someone threatens to share pictures</h2>
          <p className="gw-strong">
            Sextortion usually starts like any other chat: a friendly profile, flattery, a push to another app, a
            picture sent first and one asked back. Guildward&rsquo;s checks look for exactly that setup, and for photo
            requests, pressure and threats.
          </p>
          <p>
            If it has already happened, <code>/help</code> walks a kid through it one step at a time: don&rsquo;t pay,
            don&rsquo;t send more, keep the chat, save the evidence, report and block, and tell an adult today.
          </p>
          <p>
            It points to the people who can act: the police, a child helpline, and Take It Down to get pictures
            removed. Kids pick where they live and the numbers change to theirs. It is the same advice the FBI, NCMEC and police in Sweden and Australia give. Nothing a
            kid picks in <code>/help</code> is saved.
          </p>
        </div>
        <div className="gw-help-frag dc" data-ui="" data-reveal>
          <Message name="Guildward" bot time="Today at 22:07" ephemeral>
            <Embed
              level="blue"
              title="Someone is threatening to share pictures"
              description={
                <>
                  <p>
                    <b>The person threatening you is committing a crime, and this can be stopped.</b> These threats
                    follow a script meant to scare you into paying fast.
                  </p>
                  <ol className="dc-steps">
                    <li>
                      <b>Don&rsquo;t pay, and don&rsquo;t send anything more.</b> Paying almost never makes it stop.
                      They usually just ask for more.
                    </li>
                    <li>
                      <b>Stop replying, but don&rsquo;t delete the chat</b> or your account. The chat is evidence.
                    </li>
                    <li>
                      <b>Save evidence.</b> Screenshot the chat and their profile, and write down their @username and
                      user ID.
                    </li>
                    <li>
                      <b>Report, then block.</b> Right-click or long-press their message → <b>Report Message</b>. Then
                      block them.
                    </li>
                    <li>
                      <b>Tell an adult you trust, today.</b> A parent, someone else in your family, a teacher or the
                      school counselor. If that feels too hard, start with a child helpline in your country
                      (childhelplineinternational.org).
                    </li>
                    <li>
                      <b>Report it to the police where you live.</b> They can act even if the person lives in another
                      country.
                    </li>
                    <li>
                      <b>Get the pictures taken down.</b> Take It Down works for pictures taken before you turned 18, on
                      apps and sites that take part. Your picture never leaves your phone.
                    </li>
                  </ol>
                </>
              }
              footer="Guildward · Only you can see this · Nothing here is saved"
            />
            <Buttons>
              <Btn kind="link">Take It Down: remove pictures</Btn>
              <Btn kind="link">Find a helpline in your country</Btn>
              <Btn kind="link">How to report on Discord</Btn>
            </Buttons>
          </Message>
        </div>
      </section>

      <section className="gw-guard" id="guard" aria-labelledby="guard-title">
        <div className="gw-guard-head" data-reveal>
          <h2 id="guard-title">Guard, for server admins</h2>
          <p>
            Add the same bot to a server and it watches every channel for grooming, scams and raids, then tells your
            moderators what it saw and why.
          </p>
        </div>
        <GuardPlate />

        <div className="gw-guard-row gw-guard-row-a">
          <div className="gw-guard-say" data-reveal>
            <h3>A calm word to the kid</h3>
            <p>
              When a member under 18 receives a red message, Guard sends them a short DM: what it saw, don&rsquo;t
              reply, show an adult, and who they can talk to. The moderators hear about it at the same time.
            </p>
          </div>
          <div className="gw-guard-frag dc" data-ui="" data-reveal>
            <Message name="Guildward" bot time="Today at 20:31">
              <Embed
                level="yellow"
                title="A safety tip from Guildward"
                description={
                  <>
                    <p>
                      A message you got in <b>Pixel Art Club</b> has warning signs, like asking for photos, secrets,
                      your age, or to move to another app.
                    </p>
                    <ul className="dc-lines dc-bullets">
                      <li>Don&rsquo;t reply and don&rsquo;t send anything.</li>
                      <li>Don&rsquo;t move to Snapchat, DMs or any other app with them.</li>
                      <li>Show it to an adult you trust.</li>
                    </ul>
                    <p>
                      The server&rsquo;s moderators have seen it. Want to talk to someone? Try a child helpline in
                      your country (childhelplineinternational.org).
                    </p>
                  </>
                }
              />
            </Message>
          </div>
        </div>

        <div className="gw-guard-row gw-guard-row-b">
          <div className="gw-guard-frag gw-guard-frag-wide dc" data-ui="" data-reveal>
            <Message name="Guildward" bot time="Today at 09:12">
              <Embed
                level="yellow"
                title={
                  <>
                    <Dot level="yellow" /> Safety report: Pixel Art Club (grade C)
                  </>
                }
                description={
                  <ul className="dc-lines">
                    <li>412 members; 96 of them said or show they are under 18.</li>
                    <li>3,108 messages this week, 9 flagged (2.9 per 1,000).</li>
                    <li>2 open alerts; 5 raised this week.</li>
                    <li>3 of 11 safety checks need attention.</li>
                  </ul>
                }
              >
                <Field name="Fix these">
                  <ul className="dc-lines">
                    <li>
                      <Dot level="red" /> New accounts can talk right away. Throwaway accounts get in easily.
                    </li>
                    <li>
                      <Dot level="yellow" /> Any member can ping @everyone, a favourite raid trick.
                    </li>
                    <li>
                      <Dot level="yellow" /> Explicit images are not filtered for all members.
                    </li>
                  </ul>
                </Field>
                <Field name="Risk">
                  <b>38/100</b> · C
                </Field>
              </Embed>
              <Buttons>
                <Btn kind="primary">Apply recommended settings</Btn>
              </Buttons>
            </Message>
          </div>
          <div className="gw-guard-say" data-reveal>
            <h3>Audit, grade, fix</h3>
            <p>
              <code>/guard audit</code> grades the server from A to F and says what to change. One button applies the
              recommended settings: verification, the media filter, AutoMod and who can ping @everyone.
            </p>
            <p>
              Observe mode only alerts. Protect mode also deletes the worst messages aimed at minors and times out red
              members until a moderator looks.
            </p>
            <p>
              <Link className="gw-textlink" href="/admins">
                Set up Guard on your server <span aria-hidden="true">→</span>
              </Link>
            </p>
          </div>
        </div>
      </section>

      <section className="gw-private" aria-labelledby="private-title">
        <div className="gw-private-text" data-reveal>
          <h2 id="private-title">Message text is never stored.</h2>
          <p className="gw-lead">
            Guildward reads a message only to check it, in memory, and then lets it go. It keeps the warning sign it
            found and the IDs involved, so a pattern can show without anyone&rsquo;s words being kept.
          </p>
        </div>
        <div className="gw-private-frag" data-reveal>
          <div className="gw-ledger" data-ui="">
            <table>
              <caption>What Guard keeps from the alert above</caption>
              <thead>
                <tr>
                  <th scope="col">When</th>
                  <th scope="col">Signal</th>
                  <th scope="col">From</th>
                  <th scope="col">To</th>
                  <th scope="col">Text</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>20:31</td>
                  <td>
                    <code>msg.isolation</code>
                  </td>
                  <td>…4127</td>
                  <td>…9001</td>
                  <td className="gw-ledger-none">not stored</td>
                </tr>
                <tr>
                  <td>20:31</td>
                  <td>
                    <code>msg.age_probe</code>
                  </td>
                  <td>…4127</td>
                  <td>…9001</td>
                  <td className="gw-ledger-none">not stored</td>
                </tr>
                <tr>
                  <td>20:24</td>
                  <td>
                    <code>behave.dm_request</code>
                  </td>
                  <td>…4127</td>
                  <td>…8812</td>
                  <td className="gw-ledger-none">not stored</td>
                </tr>
              </tbody>
            </table>
          </div>
          <ul className="gw-facts">
            <li>
              <b>Checked on Guildward&rsquo;s own server.</b> Every message check also runs through a small AI model on
              the same machine. No outside service sees the text.
            </li>
            <li>
              <b>One opt-in exception.</b> A kid can press Ask AI for a second opinion on one message, and the button
              says what it does: it sends that text to Anthropic.
            </li>
            <li>
              <b>Forget me.</b> <code>/guildward forget</code> erases everything Guildward knows about a kid.
            </li>
          </ul>
        </div>
      </section>

      <section className="gw-faq" id="questions" aria-labelledby="faq-title">
        <h2 id="faq-title">Questions parents ask</h2>
        <div className="gw-faq-list" data-reveal>
          {FAQ.map(([q, a], i) => (
            <details key={q} name="faq" open={i === 0}>
              <summary>
                <span>{q}</span>
                <span className="gw-plus" aria-hidden="true" />
              </summary>
              <div className="gw-faq-a">{a}</div>
            </details>
          ))}
        </div>
      </section>

      <section className="gw-install" id="install" aria-labelledby="install-title">
        <div className="gw-install-text">
          <h2 id="install-title">Start with one check.</h2>
          <p>
            {links
              ? "The button opens Discord's own install screen. You pick the account or the server, and Discord shows exactly what Guildward will be allowed to do before anything is added."
              : "Pick where Guildward should go. Discord's own install screen then shows exactly what it will be allowed to do before anything is added."}
          </p>
        </div>
        <InstallDialog links={links} />
      </section>
    </>
  );
}
