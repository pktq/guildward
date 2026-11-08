"""Background work for the pocket app: the automatic part of protecting kids who use it.

Every few minutes: tell kids when someone they checked gets flagged, confirmed or deletes their account;
re-read watched profiles (name changes, deletions); daily server re-scans; the weekly tip; retention purge.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import TYPE_CHECKING

import discord

from guildward.bot import flows, scan
from guildward.bot import help as kidhelp
from guildward.core.i18n import Lang, register, t

if TYPE_CHECKING:
    from guildward.bot.app import GuildwardBot

log = logging.getLogger(__name__)
TICK = 300
TIPS = 6


async def run(bot: GuildwardBot) -> None:
    await bot.wait_until_ready()
    last_purge = 0.0
    while not bot.is_closed():
        try:
            await watches(bot)
            await profiles(bot)
            for row in bot.pocket.scans_due():
                try:
                    await scan.rescan(bot, row)
                except Exception:  # one kid's scan must not stop alerts, tips and purge for everyone
                    log.warning("server rescan failed", exc_info=True)
            await weekly(bot)
            if time.time() - last_purge > 3600:
                bot.pocket.purge()
                last_purge = time.time()
        except Exception:
            log.exception("pocket background tick failed")
        await asyncio.sleep(TICK)


def _lang(bot: GuildwardBot, kid: int) -> Lang:
    row = bot.pocket.user(kid)
    return row["lang"] if row and row["lang"] in ("en", "sv") else "en"


async def watches(bot: GuildwardBot) -> None:
    for w in bot.pocket.watches_to_check():
        news = bot.pocket.watch_news(w)
        if news is None:
            continue
        lang = _lang(bot, w["kid_id"])
        name = (w["display"] or w["username"] or str(w["user_id"])) if w["username"] else str(w["user_id"])
        view = discord.ui.View(timeout=None)
        for label, url in kidhelp.quick_links(lang):
            view.add_item(discord.ui.Button(label=label, url=url))
        sent = await flows.try_dm(bot, w["kid_id"], flows.watch_embed(news, name, lang), view)
        if sent:
            bot.pocket.watch_done(w["kid_id"], w["user_id"], news)
        await asyncio.sleep(0.5)


async def profiles(bot: GuildwardBot) -> None:
    for uid in bot.pocket.stale_profiles():
        try:
            user = await bot.fetch_user(uid)
        except discord.NotFound:
            bot.pocket.see_account(uid, f"deleted_user_{uid}", None, None)
            continue
        except discord.HTTPException:
            return  # rate limited or Discord trouble: try next tick
        bot.pocket.see_account(uid, user.name, user.global_name, user.avatar.key if user.avatar else None)
        bot.pocket.refresh(uid)
        await asyncio.sleep(1)


async def weekly(bot: GuildwardBot) -> None:
    week = int(time.time() // (7 * 86_400))
    for row in bot.pocket.weekly_due():
        lang: Lang = row["lang"] if row["lang"] in ("en", "sv") else "en"
        f = bot.pocket.weekly_facts(row["user_id"])
        embed = discord.Embed(title=t("weekly.title", lang), color=0x2EA043,
                              description=t("weekly.body", lang, **f))
        embed.add_field(name=t("weekly.tip_title", lang), value=t(f"weekly.tip.{week % TIPS}", lang), inline=False)
        embed.set_footer(text=t("weekly.footer", lang))
        with contextlib.suppress(Exception):
            await flows.try_dm(bot, row["user_id"], embed)
        bot.pocket.weekly_done(row["user_id"])
        await asyncio.sleep(0.5)


register({
    "weekly.title": {"en": "Your Guildward week", "sv": "Din Guildward-vecka"},
    "weekly.body": {
        "en": "You checked {checks} account(s) this week. People you checked who are now flagged: {flagged}. "
              "Servers scanned: {servers} ({risky_servers} worth a closer look).",
        "sv": "Du kollade {checks} konto(n) den här veckan. Personer du kollat som nu är flaggade: {flagged}. "
              "Skannade servrar: {servers} ({risky_servers} värda att kolla närmare).",
    },
    "weekly.tip_title": {"en": "Tip of the week", "sv": "Veckans tips"},
    "weekly.tip.0": {
        "en": "Someone you only know online asking to move to Snapchat or another app is the most common first step "
              "in grooming. You can always say no.",
        "sv": "När någon du bara känner online vill flytta till Snapchat eller en annan app är det det vanligaste "
              "första steget i grooming. Du får alltid säga nej.",
    },
    "weekly.tip.1": {
        "en": "Nobody legit asks you to keep your chats secret from your parents.",
        "sv": "Ingen schysst person ber dig hålla era chattar hemliga för dina föräldrar.",
    },
    "weekly.tip.2": {
        "en": "Free Nitro, Robux or skins for logging in through a link is a scam. Open Discord or the game yourself.",
        "sv": "Gratis Nitro, Robux eller skins om du loggar in via en länk är bedrägeri. Öppna Discord eller spelet själv.",
    },
    "weekly.tip.3": {
        "en": "If someone threatens to share pictures of you: don't pay, don't send more, and tell an adult. "
              "It is never your fault.",
        "sv": "Om någon hotar att sprida bilder på dig: betala inte, skicka inget mer och säg till en vuxen. "
              "Det är aldrig ditt fel.",
    },
    "weekly.tip.4": {
        "en": "Turn off DMs from server members in big servers: Server name → Privacy Settings → Direct Messages.",
        "sv": "Stäng av DM från servermedlemmar i stora servrar: Servernamn → Integritetsinställningar → Direktmeddelanden.",
    },
    "weekly.tip.5": {
        "en": "Gifts out of nowhere (Nitro, skins, money) from someone online usually come with a price later.",
        "sv": "Presenter från ingenstans (Nitro, skins, pengar) från någon online har oftast ett pris senare.",
    },
    "weekly.footer": {"en": "Turn this off: /guildward settings", "sv": "Stäng av: /guildward settings"},
})
