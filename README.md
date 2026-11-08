<div align="center">

<img src="site/app/icon.svg" alt="Guildward" width="72" height="72">

# Guildward

**A worldwide sextortion and grooming guard for Discord.**
Kids check a server, a person, a message or a link in two clicks. Server admins get a Guard that watches for grooming patterns.

[![CI](https://github.com/pktq/guildward/actions/workflows/ci.yml/badge.svg)](https://github.com/pktq/guildward/actions/workflows/ci.yml)
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB.svg)
![discord.py](https://img.shields.io/badge/discord.py-2.7-5865F2.svg)

</div>

<!-- TODO: add screenshots of a check result and the Guard dashboard here (e.g. docs/img/*.png). -->

## Why

Sextortion is a global crime against kids. Organized groups run it as a script: a friendly profile, a picture sent first, one asked back, then a demand for money. The FBI, the UK National Crime Agency and police in Australia, Canada and New Zealand [warned about it together](https://www.fbi.gov/news/press-releases/international-law-enforcement-agencies-issue-joint-warning-about-global-financial-sextortion-crisis) as a global crisis.

- The FBI counted more than **12,600 minor victims** in a year and a half, with more than 20 suicides linked to it ([FBI](https://www.fbi.gov/news/stories/the-financially-motivated-sextortion-threat)).
- About **90%** of financial sextortion victims in NCMEC's reports are boys aged 14 to 17, and an average of **812** sextortion reports reach NCMEC every week ([Thorn & NCMEC, 2024](https://info.thorn.org/hubfs/Research/Thorn_TrendsInFinancialSextortion_June2024.pdf)).

Guildward gives kids a plain answer (green, yellow or red, why, and what to do) before a conversation gets that far, and gives server admins early warning of the patterns behind it.

## Add Guildward

Guildward is a **hosted** product: you add the official bot to Discord from the website. There is nothing to host yourself.

<!-- TODO: link the website's install section once the site is deployed. -->
**[Add Guildward to your Discord account](https://discord.com/oauth2/authorize?client_id=1568659844003668059&integration_type=1&scope=applications.commands)**. Server installs (checks only, or full Guard) are offered on the website.

This repository is public so anyone can read what the bot does. The detection rules and the message model's weights are private (see [What's open and what's private](#whats-open-and-whats-private)).

## What it does

### The kids' app

Kids install Guildward on their own Discord account, so it works in DMs, group chats and any server. Every reply is visible only to them, in English or Swedish.

| Where | What they get |
|---|---|
| `/check <invite or link>` | Server risk from what Discord shows without joining, or a link verdict (look-alike sites, IP loggers, downloads, brand-new domains, shorteners expanded safely) |
| Right-click a user, **Apps > Safety check** | Account age, Discord's spammer flag, red-flag names, shared flags from other Guildward users, Guard child-safety bans, links to flagged accounts |
| Right-click a message, **Apps > Is this sketchy?** | Grooming signs (age questions, moving to another app, secrets, photo requests, gifts, meeting up, threats), links, the sender's shared flags, and memory ("3rd warning sign from this person in two weeks") |
| Forward a message to Guildward's DM | The same check without opening a menu |
| **Report to Guildward** | Anonymous report that feeds the shared flags |
| Buttons under a result | Save evidence, I need help, Tell my trusted adult, optional Ask AI second opinion |
| `/help` | Step-by-step help for sextortion, picture requests, someone wanting to meet, scams and bullying, with local helplines: the kid picks their country (Sweden, US, UK, Australia, Canada, or services that work anywhere) |

Also: watch alerts when a checked account is later flagged, an opt-in server scan, an opt-in weekly tip, and `forget` to erase everything about the user.

### Guard (for server admins)

Admins add the same bot to their server to switch on Guard. It reads messages in memory, stores only signal codes and IDs, and scores each member from profile, stated age, message patterns, who a message is aimed at, grooming stages per contact, reports and server structure. Out of that come:

- A **member score** with reasons, a rising/falling prediction, and a **server grade A to F**.
- **Alerts** in a private mod channel (one growing alert per person and target) with buttons for timeout, kick, ban, delete, watch and false alarm.
- **Protect mode** (optional) that deletes the worst messages aimed at minors and times out members who turn red. **Observe mode** only alerts.
- A calm safety tip DM to an under-18 member who receives a red message.
- A **server audit** with one-click recommended settings, and an **admin dashboard** and **owner dashboard** (API in [docs/GUARD_API.md](docs/GUARD_API.md)).

### Roadmap

Not shipped yet: a guardian link with parent alerts, a parent app, and a cross-server "Safety Network" of child-safety bans. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Privacy

- **Text only, never images**, so Guildward can never hold abuse material.
- **No message text is stored or logged.** Logs hold the check type and result level.
- **Inference only.** Discord content is never used to train models.
- **The kid sees everything** a parent would see. It is a tool kids use, not one aimed at them.
- The message model runs on Guildward's own CPU. No outside API sees message text.

Details, including exactly what is received and stored: [PRIVACY.md](PRIVACY.md) (draft, pending legal review).

## How it works

Every check produces `Signal`s that are combined into a verdict with a **confidence level** that grows with the data behind it (outside view, crowd reports, admin audit, content audit). Word rules and a small local multilingual model ([multilingual-e5-small](https://huggingface.co/Xenova/multilingual-e5-small), 8-bit ONNX) both feed the score, with the usual context applied (who sent it to whom, kid-to-kid damping, memory, patterns). Kids' checks always queue ahead of Guard's server traffic.

```
src/guildward/
  core/      models (Signal, Verdict, Confidence), i18n (en/sv), text normalisation
  intel/     scoring with no Discord types; local message model; rules loader
  bot/       Discord client, commands, adapters (discord.py -> facts), embeds
  guard/     server-admin bot: store (SQLite), engine, reports, dashboard API, simulate
site/        Next.js site: landing page, parents page, stats, dashboard
web/         static lockdown wizard and the original dashboard (no build step)
tools/       load tests and helper scripts
```

Full design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Dashboard API: [docs/GUARD_API.md](docs/GUARD_API.md).

## What's open and what's private

Everything is open source except the **detection rules**: the exact message and name patterns, their weights, the message model's classifier weights, and the labeled training and test data. They live in a separate private repository so abusers cannot read them and phrase around them, and they run only on Guildward's server.

- This repo ships a small **example rule set** (`src/guildward/intel/rules/example.py`) that catches only blatant cases, so tests, CI and local development work without the private set.
- Secrets (bot token, database passwords, OAuth client secret) are in neither repo.
- Production data lives only in the production database, never in git.

## Development

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), and Node.js for the site. Contributors run the bot locally against their own test Discord application; this is for development, not for hosting Guildward.

```bash
uv sync
cp .env.example .env     # set DISCORD_TOKEN (and DEV_GUILD_ID for instant command updates)
uv run guildward --sync  # first run, or after changing commands
uv run guildward         # start the bot and the dashboard API
```

`.env.example` explains each setting, including the privileged intents (Server Members, Message Content) Guard needs; the startup log prints the exact install links for your test app.

Try Guard without Discord:

```bash
uv run guildward simulate     # fill the database with a simulated server (a groomer, a reported member, a scam raid)
uv run guildward dashboard    # run only the dashboard API, no Discord connection
```

Tests and lint (the same as CI):

```bash
uv run pytest
uv run ruff check src tests
```

The public tests run on the example rules and a fake model. `GUILDWARD_MODEL=off` runs without the local model.

The site (Next.js, App Router) lives in `site/`; see [site/README.md](site/README.md):

```bash
cd site
cp .env.example .env.local
npm install
npm run dev     # http://localhost:3000
npm run build
```

## Contributing, security, license

- Contributions are welcome: read [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).
- Found a vulnerability? Do not open an issue; follow [SECURITY.md](SECURITY.md).
- Licensed under [AGPL-3.0-or-later](LICENSE).
