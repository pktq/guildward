# Guildward Privacy Policy / Integritetspolicy

> **Draft: needs legal review before launch.** / **Utkast: måste juridiskt granskas före lansering.**

Applies to the Guildward Discord app, Guildward Guard and the lockdown wizard web page. / Gäller Guildward-appen, Guildward Guard och guidens webbsida.

---

# English

**Last updated:** 2026-11-07

## Who we are
Guildward is a free, open-source child-safety tool. The data controller is **[Name, Sweden]**. Contact: **privacy@guildward.example**.

## What we receive and why
When you use Guildward, Discord sends us only what that action needs:

| Action | What Discord sends us |
|---|---|
| `/check <invite or link>` | your Discord user ID, your locale, the invite or link you typed |
| "Safety check" / "Report to Guildward" on a user | your user ID, your locale, that user's public profile |
| "Is this sketchy?" / "Report to Guildward" on a message | your user ID, your locale, the one message you chose and its author's public profile |
| A message you send or forward to Guildward's DM | that message (a forward contains the text, not who wrote it) |
| `/guildward scan` (only if you allow it on Discord's own page) | the list of servers you are in: name, icon, size. Never channels or messages |

Nothing else is read: we never see your other messages or DMs. The same bot can also be added to servers by their admins (Guard, below); that never gives it access to your DMs.

## What we store, and why

**Message text is never stored.** It is checked in memory and discarded. To protect other kids, Guildward pools what its users find, so the next kid gets warned about the same person:

| What | Why | How long |
|---|---|---|
| Accounts that Guildward users checked or reported: their user ID, username, display name, avatar ID, name changes | so a kid who checks the same account sees "N Guildward users reported this account" | until 1 year after the last check or report |
| That *a* user checked or reported an account, the result level and the report reason. **Who** checked or reported is stored only as a keyed hash, never as your ID | counting distinct reporters without keeping who reported whom | checks 180 days, reports 1 year |
| Off-platform handles (Snapchat, Instagram, phone…) and "copy-paste script" fingerprints pushed by a risky message, **as keyed hashes only** | recognising the same person behind a new account | 1 year |
| Your warning-sign memory: codes such as "asked your age" per person you checked, keyed by a hash | to tell you "this is the 3rd warning sign from this person" | 14 days |
| Watches: that you checked an account (your ID + theirs) | to message you if that account is later flagged, confirmed or deleted | 60 days after your last check |
| Your settings, language, trusted adult (if you link one), whether we can DM you | to run the features you turned on | until you run `/guildward forget` |
| Your server list scan and a Discord login token limited to "read my server list" (only after `/guildward scan`) | daily check of new servers | until `/guildward forget` or you revoke it in Discord's Authorized Apps |
| Operational logs: command name, result level, timestamp. No IDs, no content | running the service | 14 days |
| Daily counts (how many checks of each kind and level) | the operator's statistics | 400 days |

The wizard web page has no trackers, no cookies and no analytics.

**Flags shown to other kids.** An account is flagged only when several established Guildward users independently report it *and* something else backs it up (red results from several users, a Guard child-safety ban, or a link to a flagged account). Brand-new reporter accounts don't count. "Confirmed" is set only by the Guildward operator after review, or by a child-safety ban in Guard servers. Kids only ever see counts, never who reported. If you think your account is flagged wrongly, write to **privacy@guildward.example** and we will review it.

**Built-in safety model.** Every checked message is also read by a small AI model that runs on our own server in the EU. The text never leaves that server, isn't stored, and isn't used to train anything: the model only turns it into numbers and returns warning-sign codes, the same way the word rules do.

**"Ask AI" (optional).** Only when you press that button on one checked message, its text is sent to Anthropic (Claude) for a second opinion and the answer is shown to you. We don't store it; Anthropic processes it under its API terms. If you don't press it, nothing is sent.

**Link checks.** To check a link we may contact the link's website (no cookies, nothing about you), a public domain registry (RDAP) and, if switched on, Google Safe Browsing.

## Guildward Guard (server-admin bot)

Guard is the server mode of the same Guildward bot. It only runs in servers whose admins add the full bot (adding it "checks only" reads nothing). In those servers only:

| What | Stored? |
|---|---|
| Message text | **No.** Read in memory to check it, then discarded. A flagged excerpt may be posted in the server's own private moderator channel (admins can turn this off); Guard does not keep it. |
| Member ID, username, display name, avatar link, join date, roles | Yes, to show moderators who is who |
| An age a member said about themselves ("I'm 13"), or an age role | Yes, as a number or "under 18 / adult", to protect younger members first |
| Warning signs: a code such as "asked someone's age", its weight, the message/channel IDs, who it was aimed at, when | Yes |
| Reports from members, moderation actions, alerts and how they were handled | Yes |
| Risk scores per member and per day | Yes |
| Safety Network: "banned for child safety in this server" | Only if the server opted in; shared as a count with other opted-in servers and shown to Guildward users who check that account |
| Hashed handles/scripts from flagged messages | Only if the server opted in to the Safety Network, so kids' checks can recognise the same person |

**Retention:** 90 days by default (admins can choose 7–365), aggregated daily counts up to 400 days. **Erasure:** admins can erase everything with `/guard erase`; members can ask the server's admins or us. **Who sees it:** that server's admins and moderators (Manage Server for the dashboard), and the Guildward operator.

## Where and who
Hosted in the EU (Hetzner, Germany or Finland). We do not sell data or show ads. Nothing is used to train AI, and Discord's Developer Policy also forbids training on message content. The built-in safety model runs on our own server; the only outside AI service is the optional "Ask AI" button above.

## Legal basis (GDPR)
Legitimate interest (Art. 6(1)(f)) in protecting children from grooming, sextortion and scams. We balance it by never storing message text, hashing who reported whom and every handle, short retention, flags that need several independent reports plus corroboration, operator review before anything is "confirmed", and easy erasure. Data about the accounts kids check is processed for the same purpose; their owners can object and ask for review. In Sweden the age of digital consent is 13; we recommend that users under 13 do not use Discord at all (Discord's own minimum age is 13).

## Your rights
You can ask for access, correction, erasure, restriction, or object to processing, and you can complain to the Swedish Authority for Privacy Protection (IMY, imy.se). `/guildward forget` erases your settings, watches, memory, your trusted-adult link, your scan and your own checks and reports right away. For anything else, or to contest a flag on your account, write to **privacy@guildward.example**.

## Changes
Material changes will be announced in the repository and on this page before they apply.

---

# Svenska

**Senast uppdaterad:** 2026-11-07

## Vilka vi är
Guildward är ett gratis barnsäkerhetsverktyg med öppen källkod. Personuppgiftsansvarig är **[Namn, Sverige]**. Kontakt: **privacy@guildward.example**.

## Vad vi tar emot och varför
När du använder Guildward skickar Discord bara det som behövs:

| Handling | Det Discord skickar till oss |
|---|---|
| `/check <inbjudan eller länk>` | ditt Discord-användar-ID, ditt språk, inbjudan eller länken du skrev |
| "Säkerhetskoll" / "Rapportera till Guildward" på en användare | ditt användar-ID, ditt språk, användarens publika profil |
| "Är det här skumt?" / "Rapportera till Guildward" på ett meddelande | ditt användar-ID, ditt språk, det meddelande du valde och avsändarens publika profil |
| Ett meddelande du skickar eller vidarebefordrar till Guildwards DM | meddelandet (en vidarebefordran innehåller texten, inte vem som skrev) |
| `/guildward scan` (bara om du tillåter det på Discords egen sida) | listan över servrar du är med i: namn, ikon, storlek. Aldrig kanaler eller meddelanden |

Vi läser inget annat: vi ser aldrig dina andra meddelanden eller DM. Samma bot kan också läggas till i servrar av deras admins (Guard, nedan); det ger den aldrig tillgång till dina DM.

## Vad vi sparar och varför

**Meddelandetext sparas aldrig.** Den kollas i minnet och raderas. För att skydda andra barn samlar Guildward det användarna hittar, så att nästa barn varnas för samma person:

| Vad | Varför | Hur länge |
|---|---|---|
| Konton som Guildward-användare kollat eller rapporterat: användar-ID, användarnamn, visningsnamn, avatar-ID, namnbyten | så att den som kollar samma konto ser "N Guildward-användare har rapporterat kontot" | till 1 år efter senaste koll eller rapport |
| Att *en* användare kollat eller rapporterat ett konto, resultatnivå och anledning. **Vem** sparas bara som en nyckelad hash, aldrig ditt ID | räkna olika rapportörer utan att spara vem som rapporterade vem | kollar 180 dagar, rapporter 1 år |
| Konton i andra appar (Snapchat, Instagram, telefon …) och "kopierad text"-fingeravtryck från ett riskabelt meddelande, **bara som nyckelade hashar** | känna igen samma person bakom ett nytt konto | 1 år |
| Ditt minne av varningstecken: koder som "frågade om din ålder" per person du kollat, nyckelat med en hash | för att kunna säga "det här är tredje varningstecknet från personen" | 14 dagar |
| Bevakningar: att du kollat ett konto (ditt ID + deras) | för att meddela dig om kontot senare flaggas, bekräftas eller raderas | 60 dagar efter din senaste koll |
| Dina inställningar, språk, trygg vuxen (om du kopplar en), om vi kan skicka DM till dig | för att köra funktionerna du slagit på | tills du kör `/guildward forget` |
| Din serverskanning och en Discord-inloggning som bara får "läsa min serverlista" (bara efter `/guildward scan`) | daglig koll av nya servrar | tills `/guildward forget` eller du tar bort den under Auktoriserade appar i Discord |
| Driftloggar: kommandonamn, resultatnivå, tid. Inga ID, inget innehåll | drift | 14 dagar |
| Dagliga antal (hur många kollar av varje sort och nivå) | statistik för operatören | 400 dagar |

Guidens webbsida har inga spårare, inga cookies och ingen analys.

**Flaggor som andra barn ser.** Ett konto flaggas bara när flera etablerade Guildward-användare rapporterat det oberoende av varandra *och* något annat styrker det (röda resultat från flera, en barnsäkerhetsavstängning i Guard eller en koppling till ett flaggat konto). Helt nya konton räknas inte som rapportörer. "Bekräftad" sätts bara av Guildwards operatör efter granskning, eller av en barnsäkerhetsavstängning i Guard-servrar. Barn ser bara antal, aldrig vem som rapporterade. Tror du att ditt konto flaggats felaktigt, skriv till **privacy@guildward.example** så granskar vi det.

**Inbyggd säkerhetsmodell.** Varje kollat meddelande läses också av en liten AI-modell som körs på vår egen server inom EU. Texten lämnar aldrig servern, sparas inte och används inte för att träna något: modellen gör bara om den till siffror och ger tillbaka koder för varningstecken, precis som ordreglerna.

**"Fråga AI" (frivilligt).** Bara när du trycker på knappen för ett kollat meddelande skickas texten till Anthropic (Claude) för en andra åsikt, och svaret visas för dig. Vi sparar den inte; Anthropic behandlar den enligt sina API-villkor. Trycker du inte skickas inget.

**Länkkoll.** För att kolla en länk kan vi kontakta länkens webbplats (inga cookies, inget om dig), ett publikt domänregister (RDAP) och, om det är påslaget, Google Safe Browsing.

## Guildward Guard (botten för serveradmins)

Guard är serverläget i samma Guildward-bot. Det körs bara i servrar där admins lagt till hela botten ("bara kollar" läser ingenting). Bara i de servrarna:

| Vad | Sparas? |
|---|---|
| Meddelandetext | **Nej.** Läses i minnet och raderas. Ett flaggat utdrag kan skickas till serverns egen privata moderatorkanal (admins kan stänga av det); Guard sparar det inte. |
| Medlems-ID, användarnamn, visningsnamn, avatarlänk, gick med, roller | Ja, så att moderatorer ser vem som är vem |
| En ålder som medlemmen själv sagt ("jag är 13") eller en åldersroll | Ja, som tal eller "under 18 / vuxen", för att skydda yngre först |
| Varningstecken: en kod som "frågade om ålder", vikt, meddelande-/kanal-ID, vem det riktades mot, när | Ja |
| Rapporter, moderatoråtgärder, larm och hur de hanterades | Ja |
| Riskpoäng per medlem och dag | Ja |
| Säkerhetsnätverket: "avstängd för barnsäkerhet i den här servern" | Bara om servern valt det; delas som ett antal med andra servrar som valt det och visas för Guildward-användare som kollar kontot |
| Hashade konton/texter från flaggade meddelanden | Bara om servern är med i Säkerhetsnätverket, så att barns kollar kan känna igen samma person |

**Lagring:** 90 dagar som standard (admins kan välja 7–365), dagliga antal upp till 400 dagar. **Radering:** admins kan radera allt med `/guard erase`; medlemmar kan fråga serverns admins eller oss. **Vem ser det:** serverns admins och moderatorer (Hantera server för panelen) och Guildwards operatör.

## Var och hur
Hostas inom EU (Hetzner, Tyskland eller Finland). Vi säljer inga uppgifter och visar inga annonser. Inget används för att träna AI, och Discords utvecklarpolicy förbjuder också träning på meddelandeinnehåll. Den inbyggda säkerhetsmodellen körs på vår egen server; den enda externa AI-tjänsten är den frivilliga knappen "Fråga AI" ovan.

## Rättslig grund (GDPR)
Berättigat intresse (art. 6.1 f) av att skydda barn mot grooming, sextortion och bedrägerier. Vi väger upp det genom att aldrig spara meddelandetext, hasha vem som rapporterat vem och alla konton i andra appar, kort lagring, flaggor som kräver flera oberoende rapporter plus stöd, granskning av operatören innan något blir "bekräftat" och enkel radering. Uppgifter om konton som barn kollar behandlas för samma syfte; kontoinnehavaren kan invända och begära granskning. I Sverige är åldersgränsen för samtycke i digitala tjänster 13 år; vi rekommenderar att barn under 13 inte använder Discord alls (Discords egen lägsta ålder är 13).

## Dina rättigheter
Du kan begära tillgång, rättelse, radering, begränsning eller invända mot behandling, och du kan klaga hos Integritetsskyddsmyndigheten (IMY, imy.se). `/guildward forget` raderar direkt dina inställningar, bevakningar, minne, din trygga vuxna, din skanning och dina egna kollar och rapporter. För allt annat, eller för att bestrida en flagga på ditt konto, skriv till **privacy@guildward.example**.

## Ändringar
Väsentliga ändringar meddelas i repot och på den här sidan innan de börjar gälla.
