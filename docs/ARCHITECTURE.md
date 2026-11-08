# Architecture

## Layers

```
Discord interaction
      │
bot/commands.py      parse input, defer, call intel, reply ephemerally; no scoring logic here
      │
bot/adapters.py      discord.Invite / discord.User  ->  InviteFacts / UserFacts (plain dataclasses)
      │
intel/*.py           facts -> Signals -> build_verdict(...)  ->  Verdict(score, level, confidence, signals)
      │
bot/render.py        Verdict -> embed in the user's language (+ report / Bris buttons on yellow/red)
```

- **intel never imports discord.** That keeps scoring deterministic and testable with plain data, and lets the same scoring run behind the future FastAPI gateway (parent app, guardian watcher) unchanged.
- **Signals carry i18n codes, not text.** Each intel module registers its own en/sv strings next to its rules; `tests` fail if any key misses a language.
- **One scoring scale for everything** (`core/models.py`): base + sum of weights, clamped 0–100; ≥35 yellow, ≥65 red; a `severe` signal forces at least 75. Green/yellow/red mean the same thing for servers, people and messages.

## Public code, private rules

`intel/rules/__init__.py` loads a rule set (any module with `analyze_message` and `NAME_PATTERNS`): the private `guildward_private.rules` package if `GUILDWARD_PRIVATE` points at it or it's installed, else the public example set. If `GUILDWARD_PRIVATE` is set but wrong, startup fails rather than quietly running weak rules. User-facing strings for every `msg.*` code stay public in `intel/message.py`: what a kid is told isn't secret, but how we detect it is. Later private pieces (model weights, Safety Network data) follow the same rule: open interface, private content.

## Confidence = which layer produced the data

| Confidence | Layer | Source | Phase |
|---|---|---|---|
| LOW | L0 outside view | invite lookup, public profile, the one message shared | 1 (now) |
| MEDIUM | L1 crowd view | kid/parent reports, flagged inviters, invite churn | 2 |
| HIGH | L2 structural audit | admin-invited bot: permissions, AutoMod, new-account share, mod activity | 3 |
| HIGHEST | L3 content audit | in-memory grooming-stage detection, stores only message_id + category | 4 |

Adding a layer means: a new function that returns `Signal`s from its data, merged into the existing `score_*` call, with the confidence raised to the highest layer that contributed. The bot and embeds don't change.

## How later phases attach

- **Phase 2 (guardian link + parent web):** a FastAPI app beside the bot, PostgreSQL for parent↔kid links and refresh tokens, Redis workers polling `/users/@me/guilds` with the kid's OAuth token and calling `intel.server` for each new join. Alerts go out on yellow/red only.
- **Phase 3–4 (admin bot):** a separate gateway client with `GUILDS`, `GUILD_MEMBERS` and `MESSAGE_CONTENT` intents, only in servers whose admins invited it. Kept apart from the user-install client so the kid-facing app never holds server data.
- **Message model (built):** see "Local message model" below. Escalating to an open safety LLM would slot in the same way: more `msg.*` signals into `analyze_message(text, model)`.

## Local message model

`intel/semantic.py`: multilingual-e5-small (int8 ONNX, pinned revision + SHA-256, downloaded once to `data/models/`) → mean-pooled, L2-normalised 384-d embedding (e5 `query: ` prefix, text folded by `core/text.fold` so fancy fonts and look-alike letters read normally) → classifier head (an ensemble of small MLPs merged into one, sigmoid per `msg.*` category). The head ships with the rule set (`SEMANTIC_HEAD` in `guildward_private.rules`; a tiny public example otherwise) and is trained by `guildward-private/tools/train_semantic.py`.

- **Signals:** p ≥ threshold → the category's weight × (0.6 at the threshold … 1.0 at p = 1); soft ≤ p < threshold → a weight-8 hint that feeds pocket memory and Guard's per-contact stages but can't alert alone. A model "isolation" hit with no app named becomes `msg.isolation_private` (same stage, no `{app}` to fill).
- **Fusion** (`intel/message.fuse`): rules ∪ model, strongest weight per code; a rule's params and `severe` flag survive; `msg.multi_stage` is added when the fused set has ≥ 2 stages above hint weight. Everything after (Guard's `message_verdict`, `flows.check_message` with sender, crowd flags, memory) is unchanged.
- **Never on the event loop.** One shared ONNX session (intra-op 1 thread) served by one worker thread per core; onnxruntime releases the GIL. Workers take micro-batches (≤ 32, waiting ≤ 4 ms for a burst to fill) from two FIFO queues: kids' checks (context menu, forwards) first, then Guard messages. A request already waiting always goes into the next batch ahead of newer ones of its priority.
- **Load policy:** Guard requests are shed (rules only) if their queue holds 512 or one waited > 5 s; kids' checks are never shed or downgraded for load. A kid's check not started after 3 s gets a "busy, you're number N, kids go first" edit of its deferred response, replaced by the full result. Only a model failure or the 60 s ceiling gives the rules-only result, with an `ai.unfinished` note and a **Check again** button.
- **Failure:** download/load errors leave `state=failed` (owner dashboard → System → AI model); the bot runs on rules only.

## Guard (server-admin mode, layers 2–3)

```
discord.py events ──> guard/bot.py ──> MessageEvent / JoinEvent / ... (plain dataclasses)
                                          │
                                   guard/engine.py ── intel/message.py + intel/behavior.py per message
                                          │   observations, contacts (grooming stages), events → guard/store.py (SQLite)
                                          │   rescore member: intel/behavior.score_member + predict
                                          ▼
                       Out(alert | alert_update | delete | timeout | quarantine | warn_dm) → guard/bot.py executes

                       guard/reports.py ──> /guard embeds and the dashboard API (guard/web.py)
```

- **One application.** `bot/app.py` `GuildwardBot` extends `guard/bot.py` `GuardBot`: kids install it on their account (user install, no server data), admins add it to servers (guild install). Guard's privileged intents only deliver data from servers that added the full bot; a commands-only server install gives members the checks and the bot reads nothing there. `/guard` and the mod context menus are guild-install only. One process runs the bot plus the dashboard (aiohttp, already a discord.py dependency) on one event loop.
- **engine.py never imports discord**, so the whole pipeline is tested with plain data (`tests/test_guard.py`) and the simulator.
- **Message text** exists only inside `Engine.on_message`. An alert's flagged excerpt goes to the server's own mod channel (if `quote_in_alerts`) and an in-memory LRU for the dashboard; it is never written to disk.
- **Member score** = layer-0 profile (account age at half weight) + behaviour per category, scaled by breadth (distinct targets, minors among them) and recency + cross-person patterns (adult→minor, many minors, stage escalation per contact) + reports, moderation, Safety Network − reassurance (long clean history, trusted). Kid→kid peer-normal signals are damped.
- **Server grade** = base + structural audit (saturating, max 35) + live incidents (saturating, max 45) − good practice.
- **Dashboard auth**: one-time HMAC-signed links minted by the bot after Discord checked the admin's permissions (`/guard dashboard`) → 12 h HttpOnly SameSite=Strict session, re-checked against live Manage Server on every request. Writes need `X-Guildward: 1` (CSRF). Strict CSP, no external requests.

## Pocket app: shared flags across users

```
kid's check / report / forward ──> bot/commands.py, bot/dm.py ──> bot/flows.py
                                        │ intel/message, links, person, server (+ optional intel/ai on a button)
                                        │ pocket.Pocket (SQLite, same file as Guard):
                                        │   accounts + account_checks/account_reports (checker = keyed hash)
                                        │   marks: hashed handles / payment tags / MinHash script bands / avatar / name
                                        │   pair_signals (14-day memory per kid+sender), watches, pocket_users
                                        ▼
                     intel/crowd.py: auto_flag + crowd.* signals ──> shown to the next kid who checks
bot/tasks.py (every 5 min): watch alerts, profile re-reads, daily server re-scan (bot/scan.py OAuth), weekly tip
Guard engine ──> red/yellow messages in Safety-Network servers add hashed marks; child-safety bans floor the flag
owner dashboard #/owner/accounts ──> confirm / clear / watch / reset
```

- **Alts:** identity links are only the strong, cheap ones: the same off-platform handle or payment tag (strong), the same copy-paste script (MinHash bands, matched per message pair, medium), the same avatar hash or a distinctive name skeleton (weak; two weak kinds count as medium). Full writing-style fingerprinting was rejected: on short chat messages it is unreliable and would link kids who share slang.
- **Anti-brigading:** reporter weight by account age (0 under 7 days), flagged reporters count 0, reports decay (90-day half-life), "flagged" needs 3+ reports *and* corroboration, only the owner or a Guard ban confirms.
- **DMs:** a bot can only DM someone it shares a server with or who DMed it; `try_dm` records which works, and `HOME_INVITE` gives kids a server to join for alerts.

## Privacy invariants (enforced in code review and tests)

1. Message text is only held in memory for the duration of one check. It is never logged, stored or echoed back (tests check that signal params never contain the input).
2. Logs: check kind, level, score. No user IDs, guild IDs, invite codes or content.
3. No images or attachments are ever fetched.
4. A user install gives the bot nothing beyond the interaction and DMs sent to Guildward itself; server and member data only arrive from servers whose admins added the full bot.
4b. The message model runs in-process on our CPU: text → numbers → signal codes. No text is sent anywhere or written down, and Discord content is never used to train it (training rows are synthetic).
5. Guard stores signal codes, weights, IDs and timestamps, never message text (`test_message_text_is_never_stored`). Data is per server, purged after `retention_days` (default 90), and erasable with `/guard erase`.
7. Pocket data stores no message text; who checked/reported is a keyed hash; handles and scripts are keyed hashes; `/guildward forget` erases a kid's data.
6. The Safety Network shares only "banned for child safety in N servers" between servers that opted in; opting out withdraws a server's flags.
