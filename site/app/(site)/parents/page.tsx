import type { Metadata } from "next";
import type { ReactNode } from "react";
import { SetupSteps } from "@/components/site/SetupSteps";
import { installLinks } from "@/components/site/install";
import { STEPS } from "@/lib/parents";
import "@/components/site/parents.css";

export const metadata: Metadata = {
  title: "For parents",
  description:
    "How sextortion on Discord and social media actually happens, what to tell your kid before it does, and the Discord settings to set up together.",
};

// Every claim on this page links to one of these. Keep the numbers in step with the text.
const SOURCES: [title: string, href: string][] = [
  [
    "Thorn & NCMEC, Trends in Financial Sextortion (June 2024)",
    "https://info.thorn.org/hubfs/Research/Thorn_TrendsInFinancialSextortion_June2024.pdf",
  ],
  ["Polisen region Öst, Sextortion ökar (2 November 2026)", "https://polisen.se/aktuellt/nyheter/ost/2026/november/sextortion-okar/"],
  [
    "TV4 Nyheterna, interview with a police inspector at NOA (3 September 2025)",
    "https://www.tv4.se/artikel/6rXKxnOD0i41vGnMMSV7mV/unga-pressas-pa-pengar-foer-nakenbilder-vaeldigt-brutalt",
  ],
  [
    "SVT Nyheter, Ligor lurar unga pojkar att skicka nakenbilder (8 September 2024)",
    "https://www.svt.se/nyheter/inrikes/ligor-lurar-unga-pojkar-att-skicka-nakenbilder-online",
  ],
  [
    "ECPAT Sverige, “Then ‘she’ took a screenshot and it all began” (15 March 2024)",
    "https://ecpat.se/blog/report-then-she-took-a-screenshot-and-it-all-began/",
  ],
  ["FBI, The Financially Motivated Sextortion Threat", "https://www.fbi.gov/news/stories/the-financially-motivated-sextortion-threat"],
  [
    "Upper Michigan's Source, student was victim of sextortion hours before suicide (29 March 2022)",
    "https://www.uppermichiganssource.com/2022/03/29/investigators-mshs-student-was-victim-sextortion-hours-before-suicide",
  ],
  [
    "NCMEC, Sextortion: What Parents Should Know (2024)",
    "https://www.missingkids.org/content/dam/netsmartz/downloadable/tipsheets/sextortion-what-parents-should-know.pdf",
  ],
  [
    "FBI and international partners, joint warning about a global financial sextortion crisis (7 February 2023)",
    "https://www.fbi.gov/news/press-releases/international-law-enforcement-agencies-issue-joint-warning-about-global-financial-sextortion-crisis",
  ],
  [
    "Australian Federal Police, AFP joins international law enforcement agencies to deliver joint warning (7 February 2023)",
    "https://afp.gov.au/news-centre/media-release/afp-joins-international-law-enforcement-agencies-deliver-joint-warning",
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

const HOW: [string, ReactNode][] = [
  [
    "It starts as a normal chat.",
    <>
      A profile that looks like a girl the same age adds them, is friendly, and turns flirty quickly. The person
      behind it often sends a nude first, of someone else or made with AI, and asks for one back.
      <Ref n={2} />
      <Ref n={4} />
    </>,
  ],
  [
    "Then the demand.",
    <>
      As soon as a picture arrives: pay, or it goes to your family, friends and followers. ECPAT has seen demands from
      about $100 to several thousand dollars.
      <Ref n={5} />
    </>,
  ],
  [
    "It is fast.",
    <>
      NCMEC notes that in financial sextortion the abuse happens quickly after first contact.
      <Ref n={8} /> In a 2022 case in Michigan, a 17-year-old died by suicide within hours of the first message.
      <Ref n={7} />
    </>,
  ],
  [
    "Paying doesn't end it.",
    <>
      In NCMEC reports where a victim said they had paid, 27% described new demands afterwards.
      <Ref n={1} /> Police say not to pay: the picture is still out there either way.
      <Ref n={3} />
    </>,
  ],
  [
    "It is organized, worldwide, and it targets boys.",
    <>
      The FBI counted more than 12,600 minor victims in the US in a year and a half, mostly boys, and knows of more than
      20 suicides linked to it.
      <Ref n={6} /> 90% of financial sextortion victims in NCMEC&rsquo;s data were boys aged 14 to 17.
      <Ref n={1} /> Police describe organized groups based abroad, which makes the cases very hard to investigate.
      <Ref n={2} />
      <Ref n={9} />
    </>,
  ],
];

const TELL: [string, ReactNode][] = [
  [
    "How the scam goes, step by step.",
    "A stranger who is suddenly very interested, a picture sent first, a request for one back. Knowing the pattern is what lets a kid recognize it while it's happening.",
  ],
  [
    "That it is a crime against them.",
    <>
      Not something they did wrong. Responsibility lies with the person doing it, never the child.
      <Ref n={5} />
      <Ref n={8} />
    </>,
  ],
  [
    "That the threats are a script.",
    <>
      Investigators find the same, often identical, threats across many cases. They are written to make it feel like
      the end of the world, so kids pay before they have time to think or get help.
      <Ref n={1} />
    </>,
  ],
  [
    "Exactly what you will do if they come to you.",
    "Help them stop it, keep the evidence and report it. Say plainly that you won't take their phone or Discord away for telling you. Then keep to it.",
  ],
];

const IF_IT_HAPPENS: [string, ReactNode][] = [
  ["Don't pay, and stop replying.", <>Paying doesn&rsquo;t remove the picture and often brings more demands.<Ref n={1} /><Ref n={3} /></>],
  [
    "Don't delete anything.",
    "Screenshot the chat and the profile, and write down their username and user ID. Guildward's Save evidence button sends these details to your kid's DMs so they survive if the account disappears.",
  ],
  ["Report the account to Discord, then block it.", <>Thorn&rsquo;s advice is the same: don&rsquo;t pay, report, block.<Ref n={1} /></>],
  [
    "Report it to the police.",
    <>
      Call your local police, or your emergency number if your kid is in danger right now. In the US, also report to the
      FBI at tips.fbi.gov and to NCMEC&rsquo;s CyberTipline. Police say more reports make these cases easier to
      investigate.
      <Ref n={3} />
      <Ref n={6} />
    </>,
  ],
  [
    "Get pictures taken down.",
    <>
      NCMEC&rsquo;s Take It Down service helps get nude pictures of under-18s removed from platforms.
      <Ref n={8} />
    </>,
  ],
  [
    "Watch how they are doing, not just the case.",
    <>
      In NCMEC reports that describe how the victim was affected, 17.5% mention suicidal thoughts or self-harm.
      <Ref n={1} /> If your kid talks about not wanting to live, call your emergency number or a crisis line now.
    </>,
  ],
];

const HELP: [region: string, items: [name: string, text: string, href: string][]][] = [
  [
    "Anywhere",
    [
      ["Child Helpline International", "Free child helplines, country by country.", "https://childhelplineinternational.org/helplines/"],
      ["Take It Down", "NCMEC's service for getting nude pictures of under-18s removed.", "https://takeitdown.ncmec.org/"],
    ],
  ],
  [
    "United States",
    [
      ["NCMEC CyberTipline", "Report online exploitation of a child. 1-800-THE-LOST.", "https://report.cybertip.org/"],
      ["FBI", "Report at tips.fbi.gov or 1-800-CALL-FBI.", "https://tips.fbi.gov/"],
    ],
  ],
  [
    "Australia",
    [
      ["ACCCE", "Report online child sexual exploitation to the Australian Federal Police.", "https://www.accce.gov.au/report"],
      ["Kids Helpline", "1800 55 1800.", "https://kidshelpline.com.au/"],
    ],
  ],
  [
    "Sweden",
    [
      ["Bris", "116 111, call or chat, every day. Anonymous, for anyone under 18.", "https://www.bris.se/"],
      ["Polisen", "114 14. In an emergency, 112.", "https://polisen.se/"],
      ["Mind Självmordslinjen", "90101, phone and chat.", "https://mind.se/"],
    ],
  ],
];

export default function ParentsPage() {
  const install = installLinks().kid;
  return (
    <>
      <section className="pa-intro" aria-labelledby="pa-title">
        <h1 id="pa-title">Discord and your kid</h1>
        <p className="gw-lead">
          How sextortion actually happens, what to tell your kid before it does, and the settings to change together. It
          takes about half an hour.
        </p>
        <nav className="pa-toc" aria-label="On this page">
          <a href="#how">How it happens</a>
          <a href="#tell">What to tell them</a>
          <a href="#setup">Set up Discord</a>
          <a href="#happens">If it happens</a>
        </nav>
      </section>

      <section className="pa-how" id="how" aria-labelledby="how-title">
        <div className="pa-side">
          <h2 id="how-title">How sextortion actually happens</h2>
          <p>
            It is rarely what parents picture. It is a scripted scam run at scale, built to get one picture and then
            money, as fast as possible. The FBI, the UK&rsquo;s National Crime Agency and police in Australia, Canada and
            New Zealand have warned about it together as a global crisis.
            <Ref n={9} />
          </p>
        </div>
        <ol className="pa-facts">
          {HOW.map(([t, d]) => (
            <li key={t}>
              <b>{t}</b>
              <p>{d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="pa-why" aria-labelledby="why-title">
        <div className="pa-side">
          <h2 id="why-title">Why kids don&rsquo;t tell</h2>
        </div>
        <div className="pa-why-body">
          <p className="pa-big">
            The blackmailer&rsquo;s whole plan depends on your kid believing they can&rsquo;t come to you.
          </p>
          <p>
            Real messages from these cases tell kids they will be labeled a pedophile, that they will go to jail, and that
            their parents won&rsquo;t love them anymore.
            <Ref n={1} /> Shame and guilt are why so many never report it. Australian police estimate fewer than a
            quarter of young victims go to the police.
            <Ref n={4} />
            <Ref n={10} />
          </p>
          <p>
            Thorn&rsquo;s research found that these threats stand in the way of asking for help, and that this is
            especially true when a kid has heard similar things from their own parents or caregivers.
            <Ref n={1} /> If the only thing your kid has ever heard from you is that sending a nude will ruin their life,
            the blackmailer is just repeating you.
          </p>
        </div>
      </section>

      <section className="pa-tell" id="tell" aria-labelledby="tell-title">
        <div className="pa-side">
          <h2 id="tell-title">What to tell them, before anything happens</h2>
          <p>Plainly, once, and again now and then. It doesn&rsquo;t have to be a big talk.</p>
        </div>
        <ol className="pa-facts">
          {TELL.map(([t, d]) => (
            <li key={t}>
              <b>{t}</b>
              <p>{d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="pa-setup" id="setup" aria-labelledby="setup-title">
        <div className="pa-setup-head">
          <h2 id="setup-title">Set up Discord together</h2>
          <p>Nine steps. Do them with your kid holding the phone, so they see everything that changes.</p>
        </div>
        <SetupSteps steps={STEPS} install={{ kid: install }} storageKey="gw-parents" />
      </section>

      <section className="pa-happens" id="happens" aria-labelledby="happens-title">
        <div className="pa-side">
          <h2 id="happens-title">If it happens</h2>
          <p>
            Police give parents the same first advice: let your kid tell you what happened, listen, and stay calm. They
            are the victim of a crime, and won&rsquo;t be blamed for it.
            <Ref n={3} />
            <Ref n={10} />
          </p>
        </div>
        <ol className="pa-facts pa-facts-num">
          {IF_IT_HAPPENS.map(([t, d]) => (
            <li key={t}>
              <b>{t}</b>
              <p>{d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="pa-help" aria-labelledby="help-title">
        <h2 id="help-title">Where to get help</h2>
        <div className="pa-help-regions">
          {HELP.map(([region, items]) => (
            <div key={region}>
              <h3>{region}</h3>
              <ul>
                {items.map(([name, text, href]) => (
                  <li key={name}>
                    <a href={href} rel="noopener">
                      {name}
                    </a>
                    <span>{text}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <p className="pa-help-note">In immediate danger, call your local emergency number.</p>
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
