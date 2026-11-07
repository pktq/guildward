"""The three phase-1 checks. All are user-installable, work in servers, DMs and group DMs, and
reply ephemerally (only the person who asked sees it). Nothing is stored; content is never logged.
"""

from __future__ import annotations

import contextlib
import dataclasses
import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands import locale_str

from guildward.bot import render
from guildward.bot.adapters import display_name, invite_facts, parse_invite_code, user_facts
from guildward.core.i18n import Lang, has, lang_for, register, t
from guildward.core.models import Confidence, Kind, Signal, Verdict, build_verdict
from guildward.intel.message import MESSAGE_BASE, analyze_message
from guildward.intel.person import account_age_signals, score_user
from guildward.intel.server import score_invite

if TYPE_CHECKING:
    from guildward.bot.app import GuildwardBot

log = logging.getLogger(__name__)


def _everywhere(func):
    """User + server installs, usable in servers, the bot's DM and any group DM / DM."""
    func = app_commands.allowed_installs(guilds=True, users=True)(func)
    func = app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)(func)
    return app_commands.checks.cooldown(6, 60.0, key=lambda i: i.user.id)(func)


async def _reply(interaction: discord.Interaction, embed: discord.Embed,
                 view: discord.ui.View | None = None) -> None:
    kwargs = {"embed": embed, "ephemeral": True}
    if view is not None:
        kwargs["view"] = view
    if interaction.response.is_done():
        await interaction.followup.send(**kwargs)
    else:
        await interaction.response.send_message(**kwargs)


async def _send_verdict(interaction: discord.Interaction, v: Verdict, lang: Lang, subject: str) -> None:
    log.info("check kind=%s level=%s score=%d", v.kind, v.level, v.score)  # no IDs, no content
    if (store := getattr(interaction.client, "store", None)) is not None:
        store.bump(0, f"pocket.{v.kind}.{v.level}")  # daily count per kind+level for the owner dashboard
    await _reply(interaction, render.verdict_embed(v, lang, subject=subject), render.help_buttons(v, lang))


def message_verdict(text: str, author_id: int | None, *, author_spammer: bool = False) -> Verdict:
    """Message rules + who sent it. Sender signals count half: a new account saying 'gg' is not red."""
    sigs: list[Signal] = list(analyze_message(text))
    if author_id is not None:
        sigs += [dataclasses.replace(s, weight=s.weight // 2) for s in account_age_signals(author_id)
                 if s.weight > 0]
    if author_spammer:
        sigs.append(Signal("person.discord_spammer", 30))
    return build_verdict(Kind.MESSAGE, sigs, base=MESSAGE_BASE, confidence=Confidence.LOW)


def setup(bot: GuildwardBot) -> None:
    tree = bot.tree

    @tree.command(name="check", description=locale_str(
        "Check if a Discord invite is safe before you join", key="cmd.check.desc"))
    @app_commands.describe(invite=locale_str("The invite link, like discord.gg/abc123",
                                             key="cmd.check.invite"))
    @_everywhere
    async def check(interaction: discord.Interaction, invite: str) -> None:
        lang = lang_for(interaction.locale)
        code = parse_invite_code(invite)
        if code is None:
            await _reply(interaction, render.notice_embed("notice.bad_invite", lang))
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            inv = await bot.fetch_invite(code, with_counts=True)
        except discord.NotFound:
            await _reply(interaction, render.notice_embed("notice.invite_gone", lang))
            return
        facts = invite_facts(inv)
        if facts.is_friend_invite and inv.inviter:
            subject = t("subject.friend", lang, name=display_name(inv.inviter))
        elif facts.guild_id is None:
            subject = t("subject.group_dm", lang)
        else:
            subject = t("subject.server", lang, name=facts.name or "?",
                        members=facts.member_count if facts.member_count is not None else "?")
        await _send_verdict(interaction, score_invite(facts), lang, subject)

    @tree.context_menu(name=locale_str("Safety check", key="cmd.safety.name"))
    @_everywhere
    async def safety_check(interaction: discord.Interaction, user: discord.User) -> None:
        lang = lang_for(interaction.locale)
        await interaction.response.defer(ephemeral=True, thinking=True)
        with contextlib.suppress(discord.HTTPException):  # else score what the interaction gave us
            user = await bot.fetch_user(user.id)  # full profile: banner, flags
        v = score_user(user_facts(user, invoker_id=interaction.user.id))
        await _send_verdict(interaction, v, lang, t("subject.person", lang, name=display_name(user)))

    @tree.context_menu(name=locale_str("Is this sketchy?", key="cmd.sketchy.name"))
    @_everywhere
    async def is_this_sketchy(interaction: discord.Interaction, message: discord.Message) -> None:
        lang = lang_for(interaction.locale)
        if not message.content.strip():
            await _reply(interaction, render.notice_embed("notice.no_text", lang))
            return
        author = message.author
        own = author.id == interaction.user.id
        v = message_verdict(message.content, None if own else author.id,
                            author_spammer=author.public_flags.spammer)
        await _send_verdict(interaction, v, lang, t("subject.message", lang, name=display_name(author)))

    @tree.error
    async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        lang = lang_for(interaction.locale)
        if isinstance(error, app_commands.CommandOnCooldown):
            embed = render.notice_embed("notice.cooldown", lang, seconds=int(error.retry_after) + 1)
        else:
            log.error("command failed: %s", type(getattr(error, "original", error)).__name__,
                      exc_info=getattr(error, "original", error))
            embed = render.notice_embed("notice.error", lang)
        try:
            await _reply(interaction, embed)
        except discord.HTTPException:
            log.warning("could not deliver error notice")


class Translator(app_commands.Translator):
    """Swedish command names/descriptions from the same i18n catalog as everything else."""

    async def translate(self, string: locale_str, locale: discord.Locale,
                        context: app_commands.TranslationContextTypes) -> str | None:
        key = string.extras.get("key")
        if key and has(key) and lang_for(locale) != "en":
            return t(key, lang_for(locale))
        return None


register({
    "cmd.check.desc": {
        "en": "Check if a Discord invite is safe before you join",
        "sv": "Kolla om en Discord-inbjudan är säker innan du går med",
    },
    "cmd.check.invite": {
        "en": "The invite link, like discord.gg/abc123",
        "sv": "Inbjudningslänken, t.ex. discord.gg/abc123",
    },
    "cmd.safety.name": {"en": "Safety check", "sv": "Säkerhetskoll"},
    "cmd.sketchy.name": {"en": "Is this sketchy?", "sv": "Är det här skumt?"},
})
