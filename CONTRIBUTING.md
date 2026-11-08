# Contributing to Guildward

Thanks for helping. Guildward protects kids from sextortion and grooming on Discord, so changes are reviewed with care. By taking part you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Before you start

- For anything bigger than a small fix, open an issue first so we can agree on the approach.
- **Vulnerabilities go through [SECURITY.md](SECURITY.md), never a public issue.**
- Guildward is a hosted product. This repo is public for transparency and so you can run it locally for development; it is not a self-hosting distribution.

## What is out of scope

- **Detection rules.** The real message and name patterns, their weights, the message model's classifier weights and the labeled data are private on purpose, so abusers cannot phrase around them. Pull requests that add, publish or reconstruct rule patterns from real abuse will be declined. The public `example.py` rule set stays small and only catches blatant cases. Changes to the rule *engine* (loading, scoring, context) are welcome.
- Features that store message text, collect images, or train on Discord content (see the principles in the [README](README.md#privacy)).
- Anything that makes the kid see less than a parent would see.

## Reporting a false positive or a missed detection

Use the "False positive / missed detection" issue template. **Never paste real messages from children or any personal data** (names, user IDs, invite links, screenshots). Describe the pattern in your own words or use an invented example, and say which check showed it (message check, person check, Guard alert). Real examples can be passed on privately through the maintainers; they are not for public issues.

## Development setup

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/) and, for the site, Node.js.

```bash
uv sync
cp .env.example .env      # DISCORD_TOKEN of your own test application; DEV_GUILD_ID for instant command sync
uv run guildward --sync
uv run guildward
```

No Discord app handy? `uv run guildward simulate` fills a demo database and `uv run guildward dashboard` serves the dashboard API without connecting to Discord.

Checks that CI runs, run them before you push:

```bash
uv run ruff check src tests
uv run pytest
```

Site (`site/`, Next.js):

```bash
cd site
cp .env.example .env.local
npm install
npm run dev      # http://localhost:3000
npm run lint
npm run build
```

New non-trivial logic gets a small test. Tests must not need the private rules or the real model; use the example rules and the fake model like the existing ones.

## Branches and pull requests

- Branch from `main`, one change per branch, named for what it does (`fix-link-expansion`, `guard-audit-checklist`).
- Keep commits focused with a short imperative message. Keep the diff small; do not mix refactors with behavior changes.
- Open a pull request against `main` and fill in the template. CI must be green.
- Never commit secrets, `.env`, databases (`data/`), or personal information (real names, emails, local paths).
- Contributions are licensed under [AGPL-3.0-or-later](LICENSE), the project's license.
