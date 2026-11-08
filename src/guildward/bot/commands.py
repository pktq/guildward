"""Kid-facing commands. All are user-installable, work in servers, DMs and group DMs, and reply ephemerally
(only the person who asked sees it). Content is never logged or stored; see pocket.py for what is.
"""

from __future__ import annotations

import contextlib
import dataclasses
import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands import locale_str

from guildward.bot import flows, render, scan
from guildward.bot import help as kidhelp
from guildward.bot.adapters import display_name, invite_facts, parse_invite_code, user_facts
from guildward.core.i18n import Lang, has, lang_for, register, t
from guildward.core.models import Confidence, Kind, Signal, Verdict, build_verdict
from guildward.intel import links
from guildward.intel.message import MESSAGE_BASE, analyze_message
from guildward.intel.person import account_age_signals, score_user
from guildward.intel.server import score_invite

if TYPE_CHECKING:
    from guildward.bot.app import GuildwardBot

log = logging.getLogger(__name__)
_INSTALLS = app_commands.AppInstallationType(guild=True, user=True)
_CONTEXTS = app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True)


def _everywhere(func):
    """User + server installs, usable in servers, the bot's DM and any group DM / DM."""
    func = app_commands.allowed_installs(guilds=True, users=True)(func)
    func = app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)(func)
    return app_commands.checks.cooldown(6, 60.0, key=lambda i: i.user.id)(func)


async def _reply(interaction: discord.Interaction, embed: discord.Embed,
                 view: discord.ui.View | None = None, *, replace: bool = False) -> None:
    """replace=True: overwrite the deferred response (it already shows a "busy" note)."""
    if replace:
        await interaction.edit_original_response(embed=embed, view=view)
        return
    kwargs = {"embed": embed, "ephemeral": True}
    if view is not None:
        kwargs["view"] = view
    if interaction.response.is_done():
        await interaction.followup.send(**kwargs)
    else:
        await interaction.response.send_message(**kwargs)


def _count(bot: GuildwardBot, v: Verdict) -> None:
    log.info("check kind=%s level=%s score=%d", v.kind, v.level, v.score)  # no IDs, no content
    if bot.store is not None:
        bot.store.bump(0, f"pocket.{v.kind}.{v.level}")  # daily count per kind+level for the owner dashboard


async def _send_verdict(interaction: discord.Interaction, v: Verdict, lang: Lang, subject: str,
                        view: discord.ui.View | None = None, *, replace: bool = False) -> None:
    _count(interaction.client, v)
    await _reply(interaction, render.verdict_embed(v, lang, subject=subject),
                 view if view is not None else render.help_buttons(v, lang), replace=replace)


def message_verdict(text: str, author_id: int | None, *, author_spammer: bool = False) -> Verdict:
    """Message rules + who sent it. Sender signals count half: a new account saying 'gg' is not red."""
    sigs: list[Signal] = list(analyze_message(text))
    if author_id is not None:
        sigs += [dataclasses.replace(s, weight=s.weight // 2) for s in account_age_signals(author_id)
                 if s.weight > 0]
    if author_spammer:
        sigs.append(Signal("person.discord_spammer", 30))
    return build_verdict(Kind.MESSAGE, sigs, base=MESSAGE_BASE, confidence=Confidence.LOW)


def _touch(bot: GuildwardBot, interaction: discord.Interaction) -> Lang:
    lang = lang_for(interaction.locale)
    if bot.pocket is not None:
        bot.pocket.touch_user(interaction.user.id, lang)
    return lang


# --- the checks, reusable from DMs ----------------------------------------------------------
async def invite_result(bot: GuildwardBot, kid: int, lang: Lang, code: str
                        ) -> tuple[discord.Embed, discord.ui.View | None] | None:
    try:
        inv = await bot.fetch_invite(code, with_counts=True)
    except discord.NotFound:
        return None
    facts = invite_facts(inv)
    if facts.is_friend_invite and inv.inviter:
        subject = t("subject.friend", lang, name=display_name(inv.inviter))
    elif facts.guild_id is None:
        subject = t("subject.group_dm", lang)
    else:
        subject = t("subject.server", lang, name=facts.name or "?",
                    members=facts.member_count if facts.member_count is not None else "?")
    v = flows.check_server(bot, kid, lang, facts.guild_id, facts.inviter_id, score_invite(facts))
    _count(bot, v)
    return render.verdict_embed(v, lang, subject=subject), flows.result_view(bot, kid=kid, lang=lang, v=v)


async def link_result(bot: GuildwardBot, kid: int, lang: Lang, url: str) -> tuple[discord.Embed, discord.ui.View]:
    r = await links.check_url(url, session=bot.web, safe_browsing_key=bot.settings.safe_browsing_key or None)
    _count(bot, r.verdict)
    subject = t("pocket.subject_link", lang, domain=r.domain or "?")
    return (render.verdict_embed(r.verdict, lang, subject=subject),
            flows.result_view(bot, kid=kid, lang=lang, v=r.verdict))


def setup(bot: GuildwardBot) -> None:
    tree = bot.tree

    @tree.command(name="check", description=locale_str(
        "Check an invite or a link before you join or click", key="cmd.check.desc"))
    @app_commands.describe(invite=locale_str("An invite (discord.gg/abc123) or any link", key="cmd.check.invite"))
    @_everywhere
    async def check(interaction: discord.Interaction, invite: str) -> None:
        lang = _touch(bot, interaction)
        code = parse_invite_code(invite)
        url = None if code else next(iter(links.extract_urls(invite, limit=1)), None)
        if code is None and url is None:
            await _reply(interaction, render.notice_embed("notice.bad_invite", lang))
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        if url is not None:
            embed, view = await link_result(bot, interaction.user.id, lang, url)
            await _reply(interaction, embed, view)
            return
        res = await invite_result(bot, interaction.user.id, lang, code)
        if res is None:
            await _reply(interaction, render.notice_embed("notice.invite_gone", lang))
            return
        await _reply(interaction, *res)

    @tree.context_menu(name=locale_str("Safety check", key="cmd.safety.name"))
    @_everywhere
    async def safety_check(interaction: discord.Interaction, user: discord.User) -> None:
        lang = _touch(bot, interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        with contextlib.suppress(discord.HTTPException):  # else score what the interaction gave us
            user = await bot.fetch_user(user.id)  # full profile: banner, flags
        v = flows.check_person(bot, interaction.user.id, lang, user,
                               score_user(user_facts(user, invoker_id=interaction.user.id)))
        await _send_verdict(interaction, v, lang, t("subject.person", lang, name=display_name(user)),
                            flows.result_view(bot, kid=interaction.user.id, lang=lang, v=v, account=user))

    @tree.context_menu(name=locale_str("Is this sketchy?", key="cmd.sketchy.name"))
    @_everywhere
    async def is_this_sketchy(interaction: discord.Interaction, message: discord.Message) -> None:
        lang = _touch(bot, interaction)
        if not message.content.strip():
            await _reply(interaction, render.notice_embed("notice.no_text", lang))
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        author, kid = message.author, interaction.user.id
        subject = t("subject.message", lang, name=display_name(author))

        async def run(busy: flows.BusyNote | None = None) -> tuple[Verdict, discord.ui.View]:
            v = await flows.check_message(bot, kid, lang, [message.content], author=author, memory_key=author.id,
                                          event=message.id, on_wait=busy)
            return v, flows.result_view(bot, kid=kid, lang=lang, v=v, account=author, message=message,
                                        texts=[message.content], recheck=recheck)

        async def recheck() -> tuple[discord.Embed, discord.ui.View]:
            v, view = await run()
            _count(bot, v)
            return render.verdict_embed(v, lang, subject=subject), view

        busy = flows.BusyNote(lang, lambda e: interaction.edit_original_response(embed=e))
        v, view = await run(busy)
        await _send_verdict(interaction, v, lang, subject, view, replace=busy.shown)

    @tree.context_menu(name=locale_str("Report to Guildward", key="cmd.report_user.name"))
    @_everywhere
    async def report_user(interaction: discord.Interaction, user: discord.User) -> None:
        lang = _touch(bot, interaction)
        if bot.pocket is None or user.id == interaction.user.id or user.bot:
            await _reply(interaction, render.notice_embed("pocket.cant_report", lang))
            return
        bot.pocket.see_account(user.id, user.name, user.global_name, user.avatar.key if user.avatar else None)
        await interaction.response.send_message(**flows.report_picker(bot, interaction.user.id, user, lang),
                                                ephemeral=True)

    @tree.context_menu(name=locale_str("Report to Guildward", key="cmd.report_msg.name"))
    @_everywhere
    async def report_message(interaction: discord.Interaction, message: discord.Message) -> None:
        lang = _touch(bot, interaction)
        author = message.author
        if bot.pocket is None or author.id == interaction.user.id or author.bot:
            await _reply(interaction, render.notice_embed("pocket.cant_report", lang))
            return
        p = bot.pocket
        p.see_account(author.id, author.name, author.global_name, author.avatar.key if author.avatar else None)
        await interaction.response.send_message(
            **flows.report_picker(bot, interaction.user.id, author, lang, message.content or None), ephemeral=True)

    @tree.command(name="help", description=locale_str("Something happened and you need help", key="cmd.help.desc"))
    @_everywhere
    async def help_cmd(interaction: discord.Interaction) -> None:
        lang = _touch(bot, interaction)
        embed, view = kidhelp.help_menu(lang)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    gw = app_commands.Group(name="guildward", description=locale_str("Your Guildward settings and tools",
                                                                     key="cmd.gw.desc"),
                            allowed_installs=_INSTALLS, allowed_contexts=_CONTEXTS)

    @gw.command(name="settings", description=locale_str("Automatic alerts, memory and weekly tips",
                                                        key="cmd.gw.settings"))
    async def gw_settings(interaction: discord.Interaction) -> None:
        lang = _touch(bot, interaction)
        if bot.pocket is None:
            await _reply(interaction, render.notice_embed("pocket.off", lang))
            return
        embed, view = settings_panel(bot, interaction.user.id, lang)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @gw.command(name="adult", description=locale_str("Link a trusted adult who gets told when you ask for help",
                                                     key="cmd.gw.adult"))
    @app_commands.describe(code=locale_str("Are you the adult? Paste the kid's code here", key="cmd.gw.adult_code"),
                           remove=locale_str("Remove your trusted adult", key="cmd.gw.adult_remove"))
    async def gw_adult(interaction: discord.Interaction, code: str | None = None, remove: bool = False) -> None:
        lang = _touch(bot, interaction)
        p, me = bot.pocket, interaction.user.id
        if p is None:
            await _reply(interaction, render.notice_embed("pocket.off", lang))
            return
        if remove:
            p.remove_adult(me)
            await _reply(interaction, render.notice_embed("pocket.adult_removed", lang))
        elif code:
            kid = p.claim_code(code, me)
            if kid is None:
                await _reply(interaction, render.notice_embed("pocket.adult_bad_code", lang))
                return
            await _reply(interaction, render.notice_embed("pocket.adult_linked_adult", lang))
            await flows.try_dm(bot, kid, render.notice_embed("pocket.adult_linked_kid", lang,
                                                             name=display_name(interaction.user)))
        else:
            current = p.adult_of(me)
            key = "pocket.adult_code_replace" if current else "pocket.adult_code"
            await _reply(interaction, render.notice_embed(key, lang, code=p.new_pair_code(me)))

    @gw.command(name="scan", description=locale_str("Let Guildward look over the servers you're in",
                                                    key="cmd.gw.scan"))
    async def gw_scan(interaction: discord.Interaction) -> None:
        lang = _touch(bot, interaction)
        url = scan.connect_url(bot, interaction.user.id, lang)
        if url is None:
            await _reply(interaction, render.notice_embed("pocket.scan_off", lang))
            return
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label=t("pocket.scan_btn", lang), url=url))
        await _reply(interaction, render.notice_embed("pocket.scan_intro", lang), view)

    @gw.command(name="alerts", description=locale_str("Make sure Guildward can message you", key="cmd.gw.alerts"))
    async def gw_alerts(interaction: discord.Interaction) -> None:
        lang = _touch(bot, interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        ok = await flows.try_dm(bot, interaction.user.id, render.notice_embed("pocket.dm_test", lang))
        view = None
        if not ok and bot.settings.home_invite:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label=t("pocket.home_btn", lang), url=bot.settings.home_invite))
        await _reply(interaction, render.notice_embed("pocket.dm_ok" if ok else
                                                      ("pocket.dm_blocked_home" if view else "pocket.dm_blocked"),
                                                      lang), view)

    @gw.command(name="safety", description=locale_str("Turn on Discord's own safety settings, step by step",
                                                      key="cmd.gw.safety"))
    async def gw_safety(interaction: discord.Interaction) -> None:
        lang = _touch(bot, interaction)
        embed, view = kidhelp.settings_embed(lang)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @gw.command(name="forget", description=locale_str("Erase what Guildward keeps about you", key="cmd.gw.forget"))
    async def gw_forget(interaction: discord.Interaction) -> None:
        lang = lang_for(interaction.locale)
        if bot.pocket is not None:
            bot.pocket.forget(interaction.user.id)
        await _reply(interaction, render.notice_embed("pocket.forgotten", lang))

    tree.add_command(gw)

    @tree.error
    async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        lang = lang_for(interaction.locale)
        if isinstance(error, app_commands.CheckFailure) and not isinstance(error, app_commands.CommandOnCooldown):
            return  # e.g. Guard without the full bot: the check already explained it
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


def settings_panel(bot: GuildwardBot, kid: int, lang: Lang) -> tuple[discord.Embed, discord.ui.View]:
    prefs = bot.pocket.prefs(kid)
    adult = bot.pocket.adult_of(kid)
    embed = discord.Embed(title=t("pocket.settings_title", lang), color=0x57606A)
    for key in prefs:
        embed.add_field(name=("✅ " if prefs[key] else "⬜ ") + t(f"pocket.pref.{key}", lang),
                        value=t(f"pocket.pref.{key}.help", lang), inline=False)
    embed.add_field(name=t("pocket.pref.adult", lang),
                    value=t("pocket.pref.adult_on" if adult else "pocket.pref.adult_off", lang), inline=False)
    embed.set_footer(text=t("ui.footer", lang))
    view = discord.ui.View(timeout=flows.VIEW_TIMEOUT)
    for key, on in prefs.items():
        button = discord.ui.Button(label=t(f"pocket.pref.{key}", lang),
                                   style=discord.ButtonStyle.success if on else discord.ButtonStyle.secondary)

        async def toggle(interaction: discord.Interaction, key: str = key) -> None:
            if interaction.user.id != kid:
                return
            bot.pocket.set_pref(kid, key, not bot.pocket.prefs(kid)[key])
            embed, view = settings_panel(bot, kid, lang)
            await interaction.response.edit_message(embed=embed, view=view)

        button.callback = toggle
        view.add_item(button)
    return embed, view


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
        "en": "Check an invite or a link before you join or click",
        "sv": "Kolla en inbjudan eller länk innan du går med eller klickar",
    },
    "cmd.check.invite": {
        "en": "An invite (discord.gg/abc123) or any link",
        "sv": "En inbjudan (discord.gg/abc123) eller valfri länk",
    },
    "cmd.safety.name": {"en": "Safety check", "sv": "Säkerhetskoll"},
    "cmd.sketchy.name": {"en": "Is this sketchy?", "sv": "Är det här skumt?"},
    "cmd.report_user.name": {"en": "Report to Guildward", "sv": "Rapportera till Guildward"},
    "cmd.report_msg.name": {"en": "Report to Guildward", "sv": "Rapportera till Guildward"},
    "cmd.help.desc": {"en": "Something happened and you need help", "sv": "Något har hänt och du behöver hjälp"},
    "cmd.gw.desc": {"en": "Your Guildward settings and tools", "sv": "Dina Guildward-inställningar och verktyg"},
    "cmd.gw.settings": {"en": "Automatic alerts, memory and weekly tips",
                        "sv": "Automatiska varningar, minne och veckotips"},
    "cmd.gw.adult": {"en": "Link a trusted adult who gets told when you ask for help",
                     "sv": "Koppla en trygg vuxen som får veta när du ber om hjälp"},
    "cmd.gw.adult_code": {"en": "Are you the adult? Paste the kid's code here",
                          "sv": "Är du den vuxna? Klistra in barnets kod här"},
    "cmd.gw.adult_remove": {"en": "Remove your trusted adult", "sv": "Ta bort din trygga vuxna"},
    "cmd.gw.scan": {"en": "Let Guildward look over the servers you're in",
                    "sv": "Låt Guildward titta igenom servrarna du är med i"},
    "cmd.gw.alerts": {"en": "Make sure Guildward can message you", "sv": "Se till att Guildward kan skicka meddelanden"},
    "cmd.gw.safety": {"en": "Turn on Discord's own safety settings, step by step",
                      "sv": "Slå på Discords egna säkerhetsinställningar, steg för steg"},
    "cmd.gw.forget": {"en": "Erase what Guildward keeps about you", "sv": "Radera det Guildward sparar om dig"},
    "pocket.subject_link": {"en": "Link to {domain}", "sv": "Länk till {domain}"},
    "pocket.off": {"en": "This part of Guildward isn't switched on here.", "sv": "Den här delen av Guildward är inte påslagen."},
    "pocket.cant_report": {"en": "You can't report this one.", "sv": "Den här går inte att rapportera."},
    "pocket.settings_title": {"en": "Your Guildward settings", "sv": "Dina Guildward-inställningar"},
    "pocket.pref.watch_alerts": {"en": "Alerts about people I checked", "sv": "Varningar om personer jag kollat"},
    "pocket.pref.watch_alerts.help": {
        "en": "If someone you checked gets flagged or confirmed dangerous later, Guildward messages you.",
        "sv": "Om någon du kollat flaggas eller bekräftas farlig senare skickar Guildward ett meddelande.",
    },
    "pocket.pref.memory": {"en": "Remember warning signs", "sv": "Kom ihåg varningstecken"},
    "pocket.pref.memory.help": {
        "en": "Adds up warning signs from the same person over two weeks (only codes, never the text).",
        "sv": "Räknar ihop varningstecken från samma person i två veckor (bara koder, aldrig texten).",
    },
    "pocket.pref.server_alerts": {"en": "Alerts about new servers", "sv": "Varningar om nya servrar"},
    "pocket.pref.server_alerts.help": {
        "en": "After /guildward scan: tells you when you join a server that looks risky.",
        "sv": "Efter /guildward scan: säger till när du går med i en server som verkar riskabel.",
    },
    "pocket.pref.weekly": {"en": "Weekly safety tip", "sv": "Veckans säkerhetstips"},
    "pocket.pref.weekly.help": {
        "en": "A short message once a week with what Guildward noticed and one tip.",
        "sv": "Ett kort meddelande i veckan med vad Guildward märkt och ett tips.",
    },
    "pocket.pref.adult": {"en": "Trusted adult", "sv": "Trygg vuxen"},
    "pocket.pref.adult_on": {"en": "Linked. Remove with /guildward adult remove:True",
                             "sv": "Kopplad. Ta bort med /guildward adult remove:True"},
    "pocket.pref.adult_off": {"en": "None yet. Add one with /guildward adult", "sv": "Ingen än. Lägg till med /guildward adult"},
    "pocket.adult_code": {
        "en": "Your code is **{code}** (works for 30 minutes). Ask a parent or another adult you trust to add "
              "Guildward and type `/guildward adult code:{code}`. They will only hear from Guildward when *you* "
              "press \"Tell my trusted adult\". They never see your messages.",
        "sv": "Din kod är **{code}** (gäller i 30 minuter). Be en förälder eller annan vuxen du litar på att lägga "
              "till Guildward och skriva `/guildward adult code:{code}`. Hen hör bara från Guildward när *du* "
              "trycker \"Säg till min trygga vuxna\". Hen ser aldrig dina meddelanden.",
    },
    "pocket.adult_code_replace": {
        "en": "You already have a trusted adult. New code: **{code}** (30 minutes). Whoever uses it replaces them.",
        "sv": "Du har redan en trygg vuxen. Ny kod: **{code}** (30 minuter). Den som använder den ersätter hen.",
    },
    "pocket.adult_bad_code": {"en": "That code doesn't work. Codes last 30 minutes.",
                              "sv": "Koden fungerar inte. Koder gäller i 30 minuter."},
    "pocket.adult_linked_adult": {
        "en": "Done. You're now this kid's trusted adult. Guildward messages you only when they ask for help.",
        "sv": "Klart. Du är nu barnets trygga vuxna. Guildward hör bara av sig när barnet ber om hjälp.",
    },
    "pocket.adult_linked_kid": {"en": "{name} is now your trusted adult.", "sv": "{name} är nu din trygga vuxna."},
    "pocket.adult_removed": {"en": "Your trusted adult is removed.", "sv": "Din trygga vuxna är borttagen."},
    "pocket.scan_off": {"en": "Server scans aren't switched on yet.", "sv": "Serverskanning är inte påslagen än."},
    "pocket.scan_intro": {
        "en": "Guildward can look at the list of servers you're in (names and sizes only, never messages) and "
              "warn you about risky ones, now and when you join new ones. Discord will ask you to allow it.",
        "sv": "Guildward kan titta på listan över servrar du är med i (bara namn och storlek, aldrig meddelanden) "
              "och varna för riskabla, nu och när du går med i nya. Discord frågar om du tillåter det.",
    },
    "pocket.scan_btn": {"en": "Connect and scan", "sv": "Koppla och skanna"},
    "pocket.dm_test": {"en": "Test: Guildward can message you. Alerts will arrive here.",
                       "sv": "Test: Guildward kan skicka meddelanden till dig. Varningar kommer hit."},
    "pocket.dm_ok": {"en": "All set: alerts will arrive in your DMs.", "sv": "Klart: varningar kommer i dina DM."},
    "pocket.home_btn": {"en": "Join the Guildward server", "sv": "Gå med i Guildward-servern"},
    "pocket.forgotten": {
        "en": "Done. Your settings, watches, memory and your own reports and checks are erased.",
        "sv": "Klart. Dina inställningar, bevakningar, minne och dina egna rapporter och kollar är raderade.",
    },
})
