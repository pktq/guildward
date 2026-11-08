# Security Policy

## Supported versions

Guildward is a hosted service run from the `main` branch. Only the current `main` (the code running in production) receives security fixes.

## Reporting a vulnerability

**Do not open a public issue, pull request or discussion for a vulnerability.**

Report it privately through GitHub: open the repository's **Security** tab, choose **Report a vulnerability**, and describe the problem. Include steps to reproduce, what an attacker gains, and the affected files or endpoints if you know them. Do not include real user data.

We aim to acknowledge a report within a few days, keep you updated while we fix it, and credit you in the fix if you want. Please give us reasonable time to fix the problem before disclosing it.

## Scope

In scope:

- The bot (`src/guildward/`), including the Guard server-admin mode and its dashboard API.
- The website and dashboard in `site/`, and the static pages in `web/`.
- Authentication and sign-in links, permission checks (who may see which server's data), and rate limits.
- Anything that could leak, or let someone read or alter, **child-safety data**: member scores and alerts, saved evidence, shared flags, trusted-adult links, reports, or any message-derived signal. Message text must never be stored or logged; a path that does so is a vulnerability.
- Ways to bypass or abuse the detection or reporting pipeline to harm a user (for example falsely flagging an account, or exposing who reported).

Out of scope:

- The private detection rules and model weights, which are not in this repository. Methods for evading detection are not security vulnerabilities; please report them as a missed detection instead, without real messages.
- Findings that need a compromised server, a stolen bot token, or physical access.
- Automated scanner output with no demonstrated impact, and missing best-practice headers without an exploit.
- Denial of service through sheer traffic volume.

Secrets (bot token, database passwords, OAuth client secret) are not in this repository. If you find one committed, report it the same way.
