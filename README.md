# Guildward

A free, open-source Discord safety app for kids, parents and server admins. A kid checks a server, a person, a message or a link in two clicks and gets a plain answer: 🟢 / 🟡 / 🔴, why, and what to do. Message text is never stored, and no one reads anything nobody chose to share.

## The kids' app

Kids install Guildward on their own account, so it works in DMs, group chats and any server. Every reply is visible only to them, in Swedish or English.

**Checks (one tap):**

| Where | What they get |
|---|---|
| `/check <invite or link>` | Server risk from what Discord shows without joining (age, 18+ flags, verification, size, who made the invite, red-flag names, the server's Guard grade if it uses Guard), or a link verdict: fake Discord/Steam/Roblox look-alikes, IP loggers, downloads, brand-new domains, shorteners expanded safely |
| Right-click a user → **Apps → Safety check** | Account age, Discord's spammer flag, red-flag names, **shared flags from other Guildward users**, Guard child-safety bans, links to flagged accounts (same Snapchat, same payment tag, same copy-paste script) |
| Right-click a message → **Apps → Is this sketchy?** | Grooming signs (age questions, moving to Snapchat, secrets, photo requests, gifts, meeting up, threats), links in it, the sender's shared flags, and **memory**: "3rd warning sign from this person in two weeks" |
| **Forward** any message to Guildward's DM | The same check without opening any menu; several forwards are read together as one conversation |
| **Report to Guildward** (user or message) | Anonymous report that feeds the shared flags |
| Buttons under a result | **Save evidence** (user ID, account date, message link, sent to their DMs so it survives deletion), **I need help**, **Tell my trusted adult**, optional **Ask AI** second opinion |
| `/help` | Step-by-step help for sextortion, picture requests, someone wanting to meet, scams, bullying; Bris, Polisen, ECPAT, Take It Down, Discord reporting |

**Automatic (after one-time setup):**
- **Watch alerts:** if an account the kid checked is later flagged, confirmed dangerous, or deleted, Guildward DMs them.
- **Server scan** (`/guildward scan`, with the kid's OK on Discord's page): flags risky servers they're in, and every day the new ones they join.
- **Weekly tip** (opt-in) and **trusted adult** (`/guildward adult`): the adult hears from Guildward only when the kid presses the button.
- `/guildward settings`, `alerts` (make sure DMs work), `safety` (Discord's own settings, step by step), `forget` (erase everything about me).

**Shared flags** are the network that grows with users: an account is flagged only when several established users report it *and* something backs it up (red results, a Guard child-safety ban, or a strong link to a flagged account). Brand-new reporter accounts count for nothing, reports fade over 90 days, and only the operator (owner dashboard → Accounts) or a Guard ban can mark one "confirmed".

The `web/wizard/` page helps a parent and kid lock Discord down together.

## Guard: server-admin mode

Admins add the **same Guildward bot** to their server to switch on **Guard**, which watches the whole server. It reads every message in memory, stores only signal codes and IDs, and builds a profile of each member from many data vectors:

| Vector | What Guard uses |
|---|---|
| Profile | account age, avatar, Discord's spammer flag, red-flag names, name changes |
| Age | what members say about their own age ("im 13", "jag är 12"), age roles, admin-marked minor roles |
| Messages | the grooming rules (age probes, isolation, secrecy, photo requests, gifts, meeting, threats), DM requests, invite links, cross-channel spam, mass mentions, AutoMod blocks |
| Context | who a message is aimed at (reply, mention, the conversation), adult→minor vs kid→kid (peer chat is damped), new accounts, watch list |
| Patterns | how many different people they probed or pulled to DMs, how many were minors, grooming **stages per contact** (trust → risk check → secrecy → isolation → sexual → meeting), deleted flagged messages |
| People | member reports ("Report to mods"), moderation history, the **Safety Network** (child-safety bans in other Guard servers, opt-in) |
| Server | join raids, invite used, structural audit (verification, media filter, AutoMod, @everyone, 2FA, NSFW channels next to kids, mod coverage, admin sprawl, Guard's permissions), mod response time |

Out of that come a **member score with reasons, a prediction** (rising/falling, escalation none/possible/likely) and a **server grade A–F**, plus:

- **Alerts** in a private mod channel: one growing alert per person+target instead of a stream, with buttons for timeout, kick, ban, delete, watch, resolved and false alarm (false alarms feed the owner's signal-quality table).
- **Protect mode** (optional): deletes the worst messages aimed at minors, times out members who turn red, quarantines or times out raid accounts. **Observe mode** only alerts.
- **Kid-facing safety tip**: a member under 18 who receives a red message gets a calm DM (you did nothing wrong, don't reply, tell an adult, Bris 116 111).
- **Commands**: `/guard setup`, `audit` (with one-click "apply recommended settings"), `report @member`, `scan` (learn from recent history without alerting), `watch` / `trust` / `clear`, `dashboard`, `erase`; right-click a message → **Report to mods** (everyone), right-click a member → **Guard report** (mods).
- **Server admin dashboard** (`web/dashboard`): health gauge, KPIs, 30-day charts, synthesised summary, recommendations with Fix buttons, audit checklist, alert queue, members table, full person reports (timeline, contacts with grooming stages, prediction), settings, printable report.
- **Bot-owner dashboard**: system health, every server's grade, pocket-app usage by kind and level, signal false-positive rates, Safety Network flags.

### Try it without Discord

```bash
uv run guildward simulate     # a simulated kids' server: a groomer, a reported member, a scam raid
uv run guildward dashboard    # prints an owner sign-in link; open it
```

### Set up Guard

Guard is the same bot and token as the kids' app (see "Set up the Discord app" below).

1. Developer Portal → your app → **Bot**: turn on the privileged intents **Server Members** and **Message Content** (Guard only uses them in servers that add the full bot).
2. Set `OWNER_IDS` to your Discord user ID.
3. `uv run guildward --sync`. The log prints three install links: kids' account install, server *checks only* (the bot reads nothing there), and *full Guard* with exactly the permissions it needs (no Administrator).
4. In the server: `/guard setup channel:#mod-alerts mode:observe`, then `/guard scan`, then `/guard dashboard`. The Safety Network (sharing child-safety bans between servers) is off until an admin turns it on in the dashboard settings.

The dashboard listens on `127.0.0.1:8080` by default. To let admins in from outside, put it behind HTTPS (for example Caddy) and set `DASHBOARD_URL` to the public address.

## Where it's going

The final product has four ways in:

1. **Kid's pocket tool** (this release): checks anything, anywhere, on demand.
2. **Guardian link**: the kid connects their account with a parent present; a new server join triggers a score and, on yellow/red only, a parent alert.
3. **Admin audit**: admins invite the bot for a structural and conversation-level safety audit, get live grooming alerts and earn a public "Audited" score.
4. **Parent app**: web dashboard, then mobile, with alerts, contact checker, talk prompts and one-tap reports to Discord, ECPAT, Polisen and Bris.

Scores always come with a **confidence level** that grows with the data behind them: outside view → crowd reports → admin audit → content audit. The code is built around that already: every check emits `Signal`s, and later layers add more signals and raise confidence without changing the bot or the embeds. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Set up the Discord app

1. [Developer Portal](https://discord.com/developers/applications) → **New Application** → name it *Guildward*.
2. **Installation** → Installation Contexts: tick **User Install** and **Guild Install**. Install Link: *Discord Provided Link*. Scopes: `applications.commands` for User Install; `applications.commands` + `bot` for Guild Install (the startup log also prints exact links).
3. **Bot** → **Reset Token** → copy it. For Guard, turn on **Server Members** and **Message Content** here too.
4. Copy `.env.example` to `.env` and paste the token as `DISCORD_TOKEN`. For instant testing, set `DEV_GUILD_ID` to your test server's ID.
5. Use the Install Link from step 2 to add the app to your own account.

## The message model (runs locally)

Word rules alone miss risky messages worded in ways nobody anticipated ("my car is outside ur school", "only u and me can see this chat"). So every message check also goes through a small **local AI model**: [multilingual-e5-small](https://huggingface.co/Xenova/multilingual-e5-small) (8-bit ONNX, ~118 MB, English + Swedish and ~90 more languages) turns the text into an embedding, and a small classifier turns that into a probability per warning sign. Rules and model are combined (strongest signal per category wins), and the usual context still applies (who sent it to whom, kid-to-kid damping, memory, patterns).

- **It runs on Guildward's own CPU.** No GPU, no outside API: message text never leaves the server and is never stored. The only download is the model itself, once, from Hugging Face, checked against a pinned SHA-256 (`data/models/`).
- **Kids' checks always come first.** Guard's server messages queue behind them and may be skipped by the model under heavy load (the rules still run on them); a kid's check never is. If a kid's check has to wait more than a few seconds, they see their place in line, then the full result in the same message. Only if the model actually breaks (60 s ceiling) do they get the rules-only result, clearly marked, with a **Check again** button.
- **Sizing**: with 2 worker threads, 200 simultaneous checks finish with p95 ≈ 0.3 s on a desktop CPU (`tools/loadtest_semantic.py`). The model adds ~500 MB of RAM (≈260 MB of that is the tokenizer).
- If the model can't be downloaded or loaded, the bot keeps running on rules only and the owner dashboard says why. `GUILDWARD_MODEL=off` turns it off.
- The classifier's weights are private like the rules (see below); this repo ships a tiny example head trained on a few obvious lines (`intel/rules/example_head.jsonl`).
- The optional **Ask AI** button (Claude, opt-in per message) is separate and unchanged.

## Run

```bash
uv sync
uv run guildward --sync   # first run, or after changing commands
uv run guildward          # normal start
```

Global commands can take a while to appear in Discord the first time; the `DEV_GUILD_ID` copy shows up immediately.

## Test

```bash
uv run pytest
uv run ruff check src tests
```

Public tests run on the example rules and a fake model. The private repo holds the labeled corpus, the model's ~5,000-row training set and a separately written ~650-row held-out benchmark (rules only vs rules + model, per category), and runs this public suite against the real rules too.

```bash
uv run --no-sync python tools/loadtest_semantic.py --workers 2 --guard 400   # real model, 200 kids' checks
```

## Layout

```
src/guildward/
  core/      models (Signal, Verdict, Confidence), i18n (en/sv), text normalisation, snowflake ages
  intel/     server.py, person.py, message.py: scoring, no Discord types
             semantic.py: local message model (download, encoder, classifier head, priority queue)
  intel/rules/  rule loader (private set or public example, incl. the model's classifier head)
  bot/       app.py (client), commands.py (3 checks), adapters.py (discord.py -> facts), render.py (embeds)
  guard/     server-admin bot: store.py (SQLite), engine.py (events -> observations/alerts/actions),
             reports.py (person/server/owner reports), bot.py + commands.py (Discord), web.py (dashboard API),
             simulate.py (demo server); intel/behavior.py + intel/audit.py hold its scoring
web/dashboard/  admin + owner dashboard SPA (no build step, no external requests); API in docs/GUARD_API.md
web/wizard/  static lockdown wizard (no build step, no trackers)
PRIVACY.md   draft privacy policy (needs legal review before launch)
```

## What's open and what's private

Everything is open source except the **detection rules**: the exact message and name patterns, their weights, the message model's classifier weights, and the labeled training and test data. Those live in a separate private repo, `guildward-private`, so abusers can't read them and phrase around them. The rules run only on Guildward's server, so they never reach users either.

- This repo ships a small **example rule set** (`intel/rules/example.py`) that catches only blatant cases, so CI, tests and self-hosting work without the private one.
- Set `GUILDWARD_PRIVATE=<path to guildward-private/src>` and the bot loads the private set instead. It logs which one it loaded at startup.
- **Secrets** (bot token, later database passwords and the OAuth client secret) are in neither repo. They live in `.env` locally (git-ignored) and in the server's environment in production.
- **Data** (later: Safety Network flags, parent links) lives only in the production database, never in git.

## Principles

- **Text only, never images**, so Guildward can never hold abuse material.
- **Inference only**: Discord content is never used to train models (Discord Developer Policy).
- **No message text stored or logged.** Logs hold the check type and result level, nothing else.
- **The kid sees everything** a parent would see. It's a tool kids use, not one aimed at them.

License: AGPL-3.0-or-later.
