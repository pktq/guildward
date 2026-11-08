# Guildward site

The public site (`/`, `/stats`) and the Guard dashboard (`/dashboard`), built with Next.js (App Router).

## Run it

```bash
cd site
cp .env.example .env.local   # then edit if needed
npm install
npm run dev                  # http://localhost:3000
```

The site proxies `/api/*` to the Guard API, so start Guildward too (`uv run guildward`, or
`uv run guildward simulate` for demo data). Settings:

| Variable | What it does |
|---|---|
| `GUARD_API_URL` | Where the Guard API listens (default `http://localhost:8091`). |
| `NEXT_PUBLIC_DISCORD_CLIENT_ID` | Optional. Discord application ID for the install buttons; defaults to the hosted Guildward app. Set it only to point a staging site at a test app. |

If the Guard API can't be reached, `/stats` shows bundled sample numbers (`public/demo/stats.json`) and says so on the page.

## Where things are

- `app/(site)/`: the marketing pages and their header/footer layout. Styles are in `components/site/*.css`, scoped under `.gw-site`.
- `components/site/`: the page sections, the Discord-style fragments (`discord.tsx`) and the install links (`install.ts`, mirroring what the bot logs on `--sync`).
- `app/dashboard/`, `components/dashboard/`: the dashboard.
- `lib/guard.ts`: Guard API types and the cached public stats fetch.
