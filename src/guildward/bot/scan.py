"""Server scan: with the kid's OK (Discord OAuth, scopes identify + guilds), look over the servers they're in.

Discord only gives the list (name, icon, size, features), never channels or messages. We keep the refresh
token so the daily re-scan can tell the kid about risky servers they join later; /guildward forget drops it.
"""

from __future__ import annotations

import logging
import secrets
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

import discord

from guildward.core.i18n import Lang, register, t
from guildward.core.models import Level, Signal
from guildward.guard.web import secret_for, sign, verify
from guildward.intel.server import InviteFacts, score_invite

if TYPE_CHECKING:
    from guildward.bot.app import GuildwardBot

log = logging.getLogger(__name__)
API = "https://discord.com/api/v10"
SCOPES = "identify guilds"
STATE_TTL = 900


def redirect_uri(bot: GuildwardBot) -> str:
    return f"{bot.settings.dashboard_url}/pocket/callback"


def connect_url(bot: GuildwardBot, kid: int, lang: Lang) -> str | None:
    if not (bot.settings.client_secret and bot.pocket and bot.application_id):
        return None
    state = sign(secret_for(bot.store), {"t": "scan", "k": str(kid), "l": lang, "e": int(time.time()) + STATE_TTL,
                                         "x": secrets.token_hex(8)})
    return "https://discord.com/oauth2/authorize?" + urlencode({
        "client_id": bot.application_id, "response_type": "code", "redirect_uri": redirect_uri(bot),
        "scope": SCOPES, "state": state, "prompt": "consent"})


class TokenRevoked(Exception):
    """Discord said the grant is gone (400/401): stop scanning until the kid connects again."""


async def _token(bot: GuildwardBot, **form: str) -> dict[str, Any] | None:
    """None on a temporary failure (429, 5xx, network); TokenRevoked when the grant itself is invalid."""
    data = {"client_id": str(bot.application_id), "client_secret": bot.settings.client_secret, **form}
    async with bot.web.post(f"{API}/oauth2/token", data=data) as r:
        if r.status in (400, 401):
            raise TokenRevoked
        if r.status != 200:
            log.warning("oauth token exchange failed: %s", r.status)
            return None
        return await r.json()


async def _get(bot: GuildwardBot, path: str, access: str) -> Any:
    async with bot.web.get(f"{API}{path}", headers={"Authorization": f"Bearer {access}"}) as r:
        return await r.json() if r.status == 200 else None


def score_servers(bot: GuildwardBot, kid: int, guilds: list[dict[str, Any]], lang: Lang) -> list[dict[str, Any]]:
    from guildward.bot import flows  # flows imports commands-level modules; keep the import local

    out = []
    for g in guilds:
        gid = int(g["id"])
        facts = InviteFacts(code="", guild_id=gid, name=g.get("name"), features=frozenset(g.get("features") or ()),
                            member_count=g.get("approximate_member_count"))
        v = score_invite(facts)
        extra: list[Signal] = []
        if bot.pocket and (n := bot.pocket.server_red_checkers(gid)) >= 3:
            extra.append(Signal("pocket.server_reds", min(30, 10 + 5 * (n - 3)), {"n": n}))
        if (grade := flows.guard_grade(bot, gid, lang)) is not None:
            extra.append(Signal("pocket.guard_grade", flows.GRADE_WEIGHT[grade], {"grade": grade}))
        v = flows.with_signals(v, extra, base=20)
        top = v.risks[0] if v.risks else None
        out.append({"id": str(gid), "name": g.get("name") or "?", "level": v.level.value, "score": v.score,
                    "top": t(top.code, lang, **top.params) if top else None, "owner": bool(g.get("owner"))})
    return sorted(out, key=lambda s: -s["score"])


async def run_scan(bot: GuildwardBot, kid: int, access: str, lang: Lang) -> tuple[list[dict], list[dict]] | None:
    guilds = await _get(bot, "/users/@me/guilds?with_counts=true", access)
    if not isinstance(guilds, list):
        return None
    servers = score_servers(bot, kid, guilds, lang)
    new = bot.pocket.save_scan(kid, servers)
    bot.pocket.store.bump(0, "pocket.scan")
    return servers, new


async def finish(bot: GuildwardBot, code: str, state: str) -> str:
    """OAuth callback. Returns a short status key for the page; DMs the kid the scan result."""
    payload = verify(secret_for(bot.store), state)
    if payload is None or payload.get("t") != "scan" or not bot.store.use_nonce("scan:" + payload["x"], payload["e"]):
        return "expired"
    kid, lang = int(payload["k"]), payload.get("l", "en")
    try:
        tok = await _token(bot, grant_type="authorization_code", code=code, redirect_uri=redirect_uri(bot))
    except TokenRevoked:
        tok = None
    if tok is None:
        return "failed"
    me = await _get(bot, "/users/@me", tok["access_token"])
    if not me or int(me["id"]) != kid:
        return "wrong_account"  # someone else's account clicked this kid's link
    bot.pocket.touch_user(kid, lang)
    bot.pocket.set_oauth(kid, tok.get("refresh_token"))
    res = await run_scan(bot, kid, tok["access_token"], lang)
    if res is None:
        return "failed"
    from guildward.bot import flows

    if not await flows.try_dm(bot, kid, scan_embed(res[0], lang)):
        return "done_no_dm"
    return "done"


async def rescan(bot: GuildwardBot, row: Any) -> None:
    """Daily: refresh the token, re-read the server list, tell the kid about new risky servers."""
    from guildward.bot import flows

    lang: Lang = row["lang"] if row["lang"] in ("en", "sv") else "en"
    try:
        tok = await _token(bot, grant_type="refresh_token", refresh_token=row["oauth"])
    except TokenRevoked:
        bot.pocket.set_oauth(row["user_id"], None)  # revoked or expired: stop until they connect again
        return
    if tok is None:
        return  # temporary: try again tomorrow
    bot.pocket.set_oauth(row["user_id"], tok.get("refresh_token") or row["oauth"])
    res = await run_scan(bot, row["user_id"], tok["access_token"], lang)
    if res is None:
        return
    risky = [s for s in res[1] if s["level"] != Level.GREEN.value]
    if risky and bot.pocket.prefs(row["user_id"])["server_alerts"]:
        await flows.try_dm(bot, row["user_id"], scan_embed(risky, lang, new=True))


def scan_embed(servers: list[dict[str, Any]], lang: Lang, *, new: bool = False) -> discord.Embed:
    risky = [s for s in servers if s["level"] != "green"]
    dots = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
    title = t("scan.new_title" if new else "scan.title", lang, n=len(servers), risky=len(risky))
    embed = discord.Embed(title=title, color=0xDA3633 if any(s["level"] == "red" for s in risky)
                          else 0xD29922 if risky else 0x2EA043)
    lines = [f"{dots[s['level']]} **{discord.utils.escape_markdown(s['name'])[:60]}**"
             + (f": {s['top']}" if s["top"] else "") for s in (risky or servers)[:15]]
    embed.description = "\n".join(lines) or t("scan.none", lang)
    if not new:
        embed.add_field(name=t("ui.todo", lang), value=t("scan.todo" if risky else "scan.all_good", lang),
                        inline=False)
    embed.set_footer(text=t("scan.footer", lang))
    return embed


register({
    "scan.title": {"en": "Your {n} servers: {risky} need a closer look", "sv": "Dina {n} servrar: {risky} behöver kollas närmare"},
    "scan.new_title": {"en": "You joined a server that looks risky", "sv": "Du gick med i en server som verkar riskabel"},
    "scan.none": {"en": "No servers found.", "sv": "Inga servrar hittades."},
    "scan.todo": {
        "en": "For the yellow and red ones: turn off DMs from server members there, don't share personal things, "
              "and leave if anyone makes you uncomfortable. Ask an adult if you're unsure.",
        "sv": "För de gula och röda: stäng av DM från servermedlemmar där, dela inget personligt och lämna om "
              "någon får dig att känna dig obekväm. Fråga en vuxen om du är osäker.",
    },
    "scan.all_good": {"en": "Nothing stands out. Guildward checks again every day.",
                      "sv": "Inget sticker ut. Guildward kollar igen varje dag."},
    "scan.footer": {
        "en": "Based on what Discord shows from the outside. Stop scans: /guildward forget",
        "sv": "Baserat på vad Discord visar utifrån. Stoppa skanning: /guildward forget",
    },
    "scan.page.done": {"en": "Done! Check your Discord DMs from Guildward.", "sv": "Klart! Kolla dina DM från Guildward."},
    "scan.page.done_no_dm": {
        "en": "Scanned, but Guildward can't DM you yet. Run /guildward alerts in Discord.",
        "sv": "Skannat, men Guildward kan inte skicka DM till dig än. Kör /guildward alerts i Discord.",
    },
    "scan.page.expired": {"en": "This link expired. Run /guildward scan again.",
                          "sv": "Länken har gått ut. Kör /guildward scan igen."},
    "scan.page.failed": {"en": "Something went wrong. Try /guildward scan again later.",
                         "sv": "Något gick fel. Försök med /guildward scan igen senare."},
    "scan.page.wrong_account": {
        "en": "This link belongs to a different Discord account. Run /guildward scan from your own account.",
        "sv": "Länken tillhör ett annat Discord-konto. Kör /guildward scan från ditt eget konto.",
    },
})
