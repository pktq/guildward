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
- **Message model:** `intel/message.py` is rules today. A local classifier (small ONNX encoder, escalating to an open safety LLM) slots in behind `analyze_message`, returning the same `msg.*` signals so tests and rendering stay valid.

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

- **Separate application.** Guard is its own Discord app with privileged intents; the pocket app keeps zero intents. One process runs both plus the dashboard (aiohttp, already a discord.py dependency) on one event loop.
- **engine.py never imports discord**, so the whole pipeline is tested with plain data (`tests/test_guard.py`) and the simulator.
- **Message text** exists only inside `Engine.on_message`. An alert's flagged excerpt goes to the server's own mod channel (if `quote_in_alerts`) and an in-memory LRU for the dashboard; it is never written to disk.
- **Member score** = layer-0 profile (account age at half weight) + behaviour per category, scaled by breadth (distinct targets, minors among them) and recency + cross-person patterns (adult→minor, many minors, stage escalation per contact) + reports, moderation, Safety Network − reassurance (long clean history, trusted). Kid→kid peer-normal signals are damped.
- **Server grade** = base + structural audit (saturating, max 35) + live incidents (saturating, max 45) − good practice.
- **Dashboard auth**: one-time HMAC-signed links minted by the bot after Discord checked the admin's permissions (`/guard dashboard`) → 12 h HttpOnly SameSite=Strict session, re-checked against live Manage Server on every request. Writes need `X-Guildward: 1` (CSRF). Strict CSP, no external requests.

## Privacy invariants (enforced in code review and tests)

1. Message text is only held in memory for the duration of one check. It is never logged, stored or echoed back (tests check that signal params never contain the input).
2. Logs: check kind, level, score. No user IDs, guild IDs, invite codes or content.
3. No images or attachments are ever fetched.
4. The user-install client requests no gateway intents.
5. Guard stores signal codes, weights, IDs and timestamps, never message text (`test_message_text_is_never_stored`). Data is per server, purged after `retention_days` (default 90), and erasable with `/guard erase`.
6. The Safety Network shares only "banned for child safety in N servers" between servers that opted in; opting out withdraws a server's flags.
