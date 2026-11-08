// Mirrors the three links the bot logs on `guildward --sync` (src/guildward/bot/app.py, guard/bot.py).
const AUTHORIZE = "https://discord.com/oauth2/authorize";
// guard/bot.py needed_permissions(): view channels, send, embed links, read history, manage messages,
// timeout, kick, ban, manage roles, manage server, view audit log. No Administrator.
const GUARD_PERMISSIONS = "1099780156582";

export type InstallLinks = { kid: string; checks: string; guard: string };

export function installLinks(): InstallLinks | null {
  const id = process.env.NEXT_PUBLIC_DISCORD_CLIENT_ID?.trim();
  if (!id) return null;
  return {
    kid: `${AUTHORIZE}?client_id=${id}&integration_type=1&scope=applications.commands`,
    checks: `${AUTHORIZE}?client_id=${id}&integration_type=0&scope=applications.commands`,
    guard: `${AUTHORIZE}?client_id=${id}&scope=bot+applications.commands&permissions=${GUARD_PERMISSIONS}&integration_type=0`,
  };
}

export const REPO_URL = "https://github.com/pktq/guildward";
