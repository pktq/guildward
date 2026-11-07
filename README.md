# Guildward

A free, open-source Discord safety app for kids, parents and server admins. A kid checks a server, a person or a message in two clicks and gets a plain answer: 🟢 / 🟡 / 🔴, why, and what to do. Nothing is secret, nothing is stored, and no one reads anything nobody chose to share.

## What works now (phase 1)

| Where | What the kid does | What they get |
|---|---|---|
| `/check <invite>` | Pastes an invite before joining | Server risk from what Discord shows without joining: age, 18+ flags, verification level, AutoMod, verified/partner status, size, who made the invite, red-flag names |
| Right-click a user → **Apps → Safety check** | Checks someone who added them | Account age, Discord's own spammer flag, no profile picture, age-bait / dating / fake-staff names |
| Right-click a message → **Apps → Is this sketchy?** | Checks one DM they're unsure about | Grooming signs in that message (age questions, moving to Snapchat, secrets, photo requests, gifts, meeting up, threats), plus how new the sender's account is |
| `web/wizard/` | Parent and kid set Discord up together | Step-by-step lockdown of Discord's own settings + Family Center, in Swedish and English |

Every reply is visible only to the person who asked, in their Discord language (Swedish or English). It works in DMs, group chats and servers where the bot isn't a member, because the kid installs it to their own account.

## Guard: server-admin mode

Admins invite **Guildward Guard** (a second bot) to watch their whole server. It reads every message in memory, stores only signal codes and IDs, and builds a profile of each member from many data vectors:

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

1. Developer Portal → **New Application** → *Guildward Guard*. **Bot** → Reset Token → paste as `GUARD_TOKEN` in `.env`. Turn on the privileged intents **Server Members** and **Message Content**.
2. Set `OWNER_IDS` to your Discord user ID.
3. `uv run guildward --sync`. The log prints Guard's invite link with exactly the permissions it needs (no Administrator).
4. In the server: `/guard setup channel:#mod-alerts mode:observe`, then `/guard scan`, then `/guard dashboard`.

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
2. **Installation** → Installation Contexts: tick **User Install** and **Guild Install**. Install Link: *Discord Provided Link*. Scopes: `applications.commands` only (phase 1 never joins servers as a bot).
3. **Bot** → **Reset Token** → copy it. No privileged intents are needed.
4. Copy `.env.example` to `.env` and paste the token as `DISCORD_TOKEN`. For instant testing, set `DEV_GUILD_ID` to your test server's ID.
5. Use the Install Link from step 2 to add the app to your own account.

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

Public tests run on the example rules. The private repo holds the 353-row labeled corpus (English + Swedish, 42% harmless messages that look scary to naive filters) and runs this public suite against the real rules too.

## Layout

```
src/guildward/
  core/      models (Signal, Verdict, Confidence), i18n (en/sv), text normalisation, snowflake ages
  intel/     server.py, person.py, message.py: scoring, no Discord types
  intel/rules/  rule loader (private set or public example)
  bot/       app.py (client), commands.py (3 checks), adapters.py (discord.py -> facts), render.py (embeds)
  guard/     server-admin bot: store.py (SQLite), engine.py (events -> observations/alerts/actions),
             reports.py (person/server/owner reports), bot.py + commands.py (Discord), web.py (dashboard API),
             simulate.py (demo server); intel/behavior.py + intel/audit.py hold its scoring
web/dashboard/  admin + owner dashboard SPA (no build step, no external requests); API in docs/GUARD_API.md
web/wizard/  static lockdown wizard (no build step, no trackers)
PRIVACY.md   draft privacy policy (needs legal review before launch)
```

## What's open and what's private

Everything is open source except the **detection rules**: the exact message and name patterns, their weights, and the labeled test corpus. Those live in a separate private repo, `guildward-private`, so abusers can't read them and phrase around them. The rules run only on Guildward's server, so they never reach users either.

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
