"""Guard's slash commands, context menus and persistent alert buttons. Admin commands are hidden from
members by default (Manage Server); "Report to mods" is for everyone. Every reply is ephemeral.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.app_commands import locale_str

from guildward.core.i18n import Lang, lang_for, t
from guildward.guard import render
from guildward.guard.bot import FIXES, INSTALL_URL, member_info, needed_permissions

if TYPE_CHECKING:
    from guildward.guard.bot import GuardBot

log = logging.getLogger(__name__)

_BUTTONS = (  # action, style, row
    ("timeout", discord.ButtonStyle.secondary, 0), ("kick", discord.ButtonStyle.secondary, 0),
    ("ban", discord.ButtonStyle.danger, 0), ("delete", discord.ButtonStyle.secondary, 0),
    ("watch", discord.ButtonStyle.secondary, 1), ("resolve", discord.ButtonStyle.success, 1),
    ("false_positive", discord.ButtonStyle.secondary, 1),
)


def _bot(i: discord.Interaction) -> GuardBot:
    return i.client  # type: ignore[return-value]


class AlertButton(discord.ui.DynamicItem[discord.ui.Button], template=r"gw:a:(?P<aid>\d+):(?P<act>[a-z_]+)"):
    """Survives restarts: the alert id and action live in the custom_id."""

    def __init__(self, aid: int, act: str, *, label: str = "",
                 style: discord.ButtonStyle = discord.ButtonStyle.secondary, row: int | None = None) -> None:
        super().__init__(discord.ui.Button(label=label or act, style=style, custom_id=f"gw:a:{aid}:{act}", row=row))
        self.aid, self.act = aid, act

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button,
                             match: re.Match[str]) -> AlertButton:
        return cls(int(match["aid"]), match["act"])

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = _bot(interaction)
        row = bot.store.alert(self.aid)
        lang = bot.lang(interaction.guild_id) if interaction.guild_id else "en"
        if row is None or row["guild_id"] != interaction.guild_id:
            await interaction.response.send_message(embed=render.notice("g.unknown_alert", lang), ephemeral=True)
            return
        actor = interaction.user if isinstance(interaction.user, discord.Member) else None
        if actor is None or not (actor.guild_permissions.moderate_members or actor.guild_permissions.manage_guild
                                 or actor.guild_permissions.manage_messages):
            await interaction.response.send_message(
                embed=render.notice("g.no_perm_user", lang, perm="Timeout Members"), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        ok, text = await bot.act(row["guild_id"], row["user_id"], self.act, by_id=actor.id, by_name=actor.display_name,
                                 alert_id=self.aid, actor=actor)
        if ok and self.act == "watch" and row["user_id"]:
            await bot.post_alert(self.aid, edit=True)
        await interaction.followup.send(embed=discord.Embed(description=text, color=0x2EA043 if ok else 0xDA3633),
                                        ephemeral=True)


class FixAllButton(discord.ui.DynamicItem[discord.ui.Button], template=r"gw:fix:(?P<gid>\d+)"):
    def __init__(self, gid: int, label: str = "Apply") -> None:
        super().__init__(discord.ui.Button(label=label, style=discord.ButtonStyle.primary, custom_id=f"gw:fix:{gid}"))
        self.gid = gid

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button,
                             match: re.Match[str]) -> FixAllButton:
        return cls(int(match["gid"]))

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = _bot(interaction)
        lang = bot.lang(self.gid)
        actor = interaction.user
        if not isinstance(actor, discord.Member) or not actor.guild_permissions.manage_guild:
            await interaction.response.send_message(embed=render.notice("g.no_perm_user", lang, perm="Manage Server"),
                                                    ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        overview = bot.reports.overview(self.gid, lang) or {"audit": []}
        wanted = [c["fix"] for c in overview["audit"] if not c["ok"] and c["fix"] in FIXES]
        done, failed = [], []
        for fix in wanted:
            ok, _ = await bot.apply_fix(self.gid, fix)
            (done if ok else failed).append(t(f"audit.{fix}.label", lang))
        await interaction.followup.send(embed=render.notice("g.fixes_applied", lang, done=", ".join(done) or "-",
                                                            failed=", ".join(failed) or "-"), ephemeral=True)


def alert_view(a: dict[str, Any], lang: Lang) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for act, style, row in _BUTTONS:
        if act == "delete" and not a.get("jump_url"):
            continue
        if act in ("timeout", "kick", "ban", "watch") and not a.get("user"):
            continue
        view.add_item(AlertButton(a["id"], act, label=t(f"g.btn_{act}", lang), style=style, row=row))
    return view


def _link_view(url: str, label: str) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label=label, url=url))
    return view


_SERVER_INSTALL = app_commands.AppInstallationType(guild=True, user=False)


class GuardGroup(app_commands.Group):
    async def interaction_check(self, i: discord.Interaction) -> bool:
        bot = _bot(i)
        if i.guild_id and bot.get_guild(i.guild_id) is None:
            # Added commands-only (no bot user): Guard can't see this server until the full bot is added.
            url = INSTALL_URL.format(id=bot.application_id, perms=needed_permissions().value)
            await i.response.send_message(embed=render.notice("g.bot_missing", lang_for(i.locale), url=url),
                                          ephemeral=True)
            return False
        return True


def setup(bot: GuardBot) -> None:
    bot.add_dynamic_items(AlertButton, FixAllButton)
    tree = bot.tree
    group = GuardGroup(name="guard", description=locale_str("Guildward Guard: server safety", key="gcmd.guard"),
                       guild_only=True, allowed_installs=_SERVER_INSTALL,
                       default_permissions=discord.Permissions(manage_guild=True))

    async def ready(i: discord.Interaction) -> bool:
        if bot.store.guild(i.guild_id) is None and i.guild:
            await bot._adopt(i.guild)
        return True

    @group.command(name="setup", description=locale_str("Set up Guard: alert channel and mode", key="gcmd.setup"))
    @app_commands.describe(channel=locale_str("Private channel where moderators get alerts", key="gcmd.setup.channel"),
                           mode=locale_str("observe = alerts only, protect = Guard also acts", key="gcmd.setup.mode"),
                           language=locale_str("Language of alerts", key="gcmd.setup.lang"))
    @app_commands.choices(mode=[app_commands.Choice(name="observe", value="observe"),
                                app_commands.Choice(name="protect", value="protect")],
                          language=[app_commands.Choice(name="English", value="en"),
                                    app_commands.Choice(name="Svenska", value="sv")])
    async def setup_cmd(i: discord.Interaction, channel: discord.TextChannel, mode: str = "observe",
                        language: str | None = None) -> None:
        await ready(i)
        lang = language or lang_for(i.locale)
        perms = channel.permissions_for(i.guild.me)
        if not (perms.send_messages and perms.embed_links and perms.view_channel):
            await i.response.send_message(embed=render.notice("g.cant_post", lang, channel=channel.mention),
                                          ephemeral=True)
            return
        if channel.permissions_for(i.guild.default_role).view_channel:
            await i.response.send_message(embed=render.notice("g.channel_public", lang, channel=channel.mention),
                                          ephemeral=True)
            return
        bot.store.update_settings(i.guild_id, {"alert_channel_id": str(channel.id), "mode": mode, "lang": lang})
        await i.response.defer(ephemeral=True, thinking=True)
        await bot.refresh_audit(i.guild)
        o = bot.reports.overview(i.guild_id, lang, missing=bot.missing(i.guild))
        view = discord.ui.View()
        view.add_item(FixAllButton(i.guild_id, label=t("g.btn_fix_all", lang)))
        await i.followup.send(content=t("g.setup_done", lang, channel=channel.mention, mode=mode),
                              embed=render.overview_embed(o, lang), view=view, ephemeral=True)

    @group.command(name="audit", description=locale_str("Safety report for this server", key="gcmd.audit"))
    async def audit_cmd(i: discord.Interaction) -> None:
        await ready(i)
        lang = lang_for(i.locale)
        await i.response.defer(ephemeral=True, thinking=True)
        await bot.refresh_audit(i.guild)
        o = bot.reports.overview(i.guild_id, lang, missing=bot.missing(i.guild))
        view = discord.ui.View()
        view.add_item(FixAllButton(i.guild_id, label=t("g.btn_fix_all", lang)))
        if bot.dashboard_url and bot.sign_link:
            view.add_item(discord.ui.Button(label=t("g.btn_dashboard", lang),
                                            url=bot.sign_link(i.user, i.guild_id, lang)))
        await i.followup.send(embed=render.overview_embed(o, lang), view=view, ephemeral=True)

    async def send_person(i: discord.Interaction, member: discord.Member | discord.User) -> None:
        await ready(i)
        lang = lang_for(i.locale)
        if bot.store.member(i.guild_id, member.id) is None:
            bot.engine.seed_member(i.guild_id, member_info(member, bot.minor_roles(i.guild_id)), None)
        r = bot.reports.person(i.guild_id, member.id, lang)
        view = None
        if bot.dashboard_url and bot.sign_link:
            view = _link_view(bot.sign_link(i.user, i.guild_id, lang, f"/g/{i.guild_id}/member/{member.id}"),
                              t("g.btn_dashboard", lang))
        await i.response.send_message(embed=render.person_embed(r, lang), view=view or discord.utils.MISSING,
                                      ephemeral=True)

    @group.command(name="report", description=locale_str("Risk report for one member", key="gcmd.report"))
    @app_commands.describe(member=locale_str("The member to check", key="gcmd.report.member"))
    async def report_cmd(i: discord.Interaction, member: discord.Member) -> None:
        await send_person(i, member)

    @group.command(name="dashboard", description=locale_str("Get a private sign-in link to the dashboard",
                                                            key="gcmd.dashboard"))
    async def dashboard_cmd(i: discord.Interaction) -> None:
        await ready(i)
        lang = lang_for(i.locale)
        if not (bot.dashboard_url and bot.sign_link):
            await i.response.send_message(embed=render.notice("g.dash_off", lang), ephemeral=True)
            return
        await i.response.send_message(embed=render.notice("g.dash_link", lang),
                                      view=_link_view(bot.sign_link(i.user, i.guild_id, lang),
                                                      t("g.btn_dashboard", lang)), ephemeral=True)

    @group.command(name="scan", description=locale_str("Learn from recent message history", key="gcmd.scan"))
    @app_commands.describe(days=locale_str("How many days back (1-30)", key="gcmd.scan.days"))
    async def scan_cmd(i: discord.Interaction, days: app_commands.Range[int, 1, 30] = 7) -> None:
        await ready(i)
        lang = lang_for(i.locale)
        if i.guild_id in bot._scanning:
            await i.response.send_message(embed=render.notice("g.scan_busy", lang), ephemeral=True)
            return
        await i.response.send_message(embed=render.notice("g.scan_start", lang, days=days), ephemeral=True)
        bot._scanning.add(i.guild_id)
        try:
            stats = await bot.scan(i.guild, days)
        finally:
            bot._scanning.discard(i.guild_id)
        await i.followup.send(embed=render.notice("g.scan_done", lang, **stats), ephemeral=True)

    def status_command(name: str, key: str, desc: str):
        @group.command(name=name, description=locale_str(desc, key=key))
        @app_commands.describe(member=locale_str("The member to check", key="gcmd.report.member"))
        async def cmd(i: discord.Interaction, member: discord.Member) -> None:
            await ready(i)
            if bot.store.member(i.guild_id, member.id) is None:
                bot.engine.seed_member(i.guild_id, member_info(member, bot.minor_roles(i.guild_id)), None)
            _, text = await bot.act(i.guild_id, member.id, name, by_id=i.user.id, by_name=i.user.display_name)
            await i.response.send_message(embed=discord.Embed(description=text), ephemeral=True)
        return cmd

    status_command("watch", "gcmd.watch", "Put a member on the watch list")
    status_command("trust", "gcmd.trust", "Mark a member as trusted")
    status_command("clear", "gcmd.clear", "Clear a member's watch/trust status")

    @group.command(name="erase", description=locale_str("Erase all data Guard holds about this server",
                                                        key="gcmd.erase"))
    async def erase_cmd(i: discord.Interaction) -> None:
        lang = lang_for(i.locale)
        if not (isinstance(i.user, discord.Member) and (i.user.guild_permissions.administrator
                                                        or i.user.id == i.guild.owner_id)):
            await i.response.send_message(embed=render.notice("g.no_perm_user", lang, perm="Administrator"),
                                          ephemeral=True)
            return
        view = discord.ui.View(timeout=60)
        button = discord.ui.Button(label=t("g.btn_confirm_erase", lang), style=discord.ButtonStyle.danger)

        async def confirm(ci: discord.Interaction) -> None:
            if ci.user.id != i.user.id:
                return
            bot.store.forget_guild(i.guild_id)
            await bot._adopt(i.guild)
            await ci.response.edit_message(embed=render.notice("g.erased", lang), view=None)

        button.callback = confirm
        view.add_item(button)
        await i.response.send_message(embed=render.notice("g.erase_confirm", lang), view=view, ephemeral=True)

    tree.add_command(group)

    @tree.context_menu(name=locale_str("Report to mods", key="gcmd.ctx_report"))
    @app_commands.guild_only()
    @app_commands.allowed_installs(guilds=True, users=False)
    async def report_to_mods(i: discord.Interaction, message: discord.Message) -> None:
        lang = lang_for(i.locale)
        if bot.store.guild(i.guild_id) is None or not bot.store.settings(i.guild_id)["alert_channel_id"]:
            await i.response.send_message(embed=render.notice("g.not_setup", lang), ephemeral=True)
            return
        reporter = i.user if isinstance(i.user, discord.Member) else i.guild.get_member(i.user.id)
        author = message.author
        outs = bot.engine.on_report(i.guild_id, member_info(reporter or i.user, bot.minor_roles(i.guild_id)),
                                    member_info(author, bot.minor_roles(i.guild_id)), channel_id=message.channel.id,
                                    message_id=message.id, content=message.content or None,
                                    channel_name=getattr(message.channel, "name", ""))
        await i.response.send_message(embed=render.notice("g.reported" if outs else "g.already_reported", lang),
                                      ephemeral=True)
        await bot.execute(outs)

    @tree.context_menu(name=locale_str("Guard report", key="gcmd.ctx_member"))
    @app_commands.guild_only()
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.default_permissions(moderate_members=True)
    async def guard_report(i: discord.Interaction, member: discord.Member) -> None:
        await send_person(i, member)

    @tree.error
    async def on_error(i: discord.Interaction, error: app_commands.AppCommandError) -> None:
        log.error("guard command failed: %s", type(getattr(error, "original", error)).__name__,
                  exc_info=getattr(error, "original", error))
        embed = render.notice("notice.error", lang_for(i.locale))
        try:
            if i.response.is_done():
                await i.followup.send(embed=embed, ephemeral=True)
            else:
                await i.response.send_message(embed=embed, ephemeral=True)
        except discord.HTTPException:
            pass
