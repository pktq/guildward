"""Guildward Guard: the server-admin side of the one Guildward bot (bot/app.py builds on this class).
Active only in servers whose admins added the full bot; uses the GUILDS, GUILD_MEMBERS, MESSAGE_CONTENT
and moderation intents there. Kids' DMs to the bot are handled by bot/dm.py.

This file is the only place Guard meets discord.py: events -> engine events, engine outputs -> Discord
actions, and the operations the dashboard and buttons call (act on a member, apply a fix).
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import logging
import time
import zlib
from datetime import timedelta
from typing import Any

import discord

from guildward.bot import helplines
from guildward.core.i18n import Lang, t
from guildward.guard import render
from guildward.guard.engine import Engine, JoinEvent, MemberInfo, MessageEvent, Out
from guildward.guard.reports import Reports
from guildward.guard.store import Store
from guildward.intel import semantic
from guildward.intel.audit import AM_MENTION, AM_PRESET, AM_SPAM, GuildFacts
from guildward.intel.behavior import role_age

log = logging.getLogger(__name__)

NEEDED = {
    "view_channel": "View Channels", "send_messages": "Send Messages", "embed_links": "Embed Links",
    "read_message_history": "Read Message History", "manage_messages": "Manage Messages",
    "moderate_members": "Timeout Members", "kick_members": "Kick Members", "ban_members": "Ban Members",
    "manage_roles": "Manage Roles", "manage_guild": "Manage Server", "view_audit_log": "View Audit Log",
}
ACTION_PERM = {"timeout": "moderate_members", "kick": "kick_members", "ban": "ban_members",
               "delete": "manage_messages", "quarantine": "manage_roles"}
INSTALL_URL = ("https://discord.com/oauth2/authorize?client_id={id}&scope=bot+applications.commands"
               "&permissions={perms}&integration_type=0")
SCAN_CHUNK = 64
FIXES = ("verification", "content_filter", "automod_presets", "automod_mentions", "automod_spam", "everyone_mentions")


def needed_permissions() -> discord.Permissions:
    return discord.Permissions(**dict.fromkeys(NEEDED, True))


def member_info(m: discord.Member | discord.User, minor_roles: set[int] | frozenset[int] = frozenset()) -> MemberInfo:
    roles = [r for r in getattr(m, "roles", []) if not r.is_default()]
    age = "minor" if any(r.id in minor_roles for r in roles) else role_age([r.name for r in roles])
    return MemberInfo(
        id=m.id, username=m.name, display=m.display_name if m.display_name != m.name else m.global_name,
        avatar=m.display_avatar.url if m.avatar else None, has_avatar=m.avatar is not None, is_bot=m.bot,
        spammer=m.public_flags.spammer, role_age=age, roles=tuple(r.name for r in roles),
    )


def webhook_persona(msg: discord.Message) -> MemberInfo:
    """Test persona for a webhook message: one member per webhook name.

    Stable id per name; its timestamp is the webhook's, so personas look like new accounts."""
    name = msg.author.name
    return MemberInfo(id=(msg.webhook_id >> 22 << 22) | (zlib.crc32(name.encode()) & 0x3FFFFF), username=name,
                      has_avatar=msg.author.avatar is not None)


class GuardBot(discord.Client):
    def __init__(self, store: Store, *, dashboard_url: str | None, dev_guild_id: int | None = None,
                 sync: bool = False) -> None:
        intents = discord.Intents.none()
        intents.guilds = intents.members = intents.guild_messages = intents.message_content = True
        intents.moderation = intents.invites = intents.auto_moderation_execution = True
        intents.dm_messages = True  # kids forward messages to the bot to check them
        super().__init__(intents=intents, chunk_guilds_at_startup=True)
        self.store = store
        self.engine = Engine(store)
        self.reports = Reports(self.engine)
        self.dashboard_url = dashboard_url
        self.tree = discord.app_commands.CommandTree(self)
        self._sync, self._dev_guild = sync, dev_guild_id
        self._invites: dict[int, dict[str, tuple[int, int | None]]] = {}
        self._scanning: set[int] = set()
        self.started = time.time()
        self.sign_link = None  # set by the web layer: (user, guild, owner, lang) -> URL

    # --- lifecycle --------------------------------------------------------------------------
    async def setup_hook(self) -> None:
        from guildward.bot.commands import Translator
        from guildward.guard import commands  # circular: commands needs the bot type

        await self.tree.set_translator(Translator())
        commands.setup(self)
        if self._sync:
            log.info("guard: synced %d global commands", len(await self.tree.sync()))
        if self._dev_guild:
            guild = discord.Object(self._dev_guild)
            self.tree.copy_global_to(guild=guild)
            with contextlib.suppress(discord.HTTPException):
                await self.tree.sync(guild=guild)
        self.loop.create_task(self._housekeeping())

    async def on_ready(self) -> None:
        log.info("guard ready as %s in %d servers. Invite: %s", self.user, len(self.guilds),
                 INSTALL_URL.format(id=self.application_id, perms=needed_permissions().value))
        for g in self.guilds:
            await self._adopt(g)

    async def _adopt(self, g: discord.Guild) -> None:
        self.store.upsert_guild(g.id, name=g.name, icon=g.icon.url if g.icon else None, owner_id=g.owner_id,
                                member_count=g.member_count or len(g.members))
        minor_roles = self.minor_roles(g.id)
        with self.store.tx():
            for m in g.members:
                self.engine.seed_member(g.id, member_info(m, minor_roles),
                                        int(m.joined_at.timestamp()) if m.joined_at else None)
        await self._cache_invites(g)
        await self.refresh_audit(g)

    async def _housekeeping(self) -> None:
        await self.wait_until_ready()
        while not self.is_closed():
            await asyncio.sleep(3600)
            try:
                self.store.purge()
                for g in self.guilds:
                    await self.refresh_audit(g)
            except Exception:
                log.exception("guard housekeeping failed")

    async def on_guild_join(self, g: discord.Guild) -> None:
        log.info("guard joined a server (%d members)", g.member_count or 0)
        await self._adopt(g)
        channel = g.system_channel
        if channel and channel.permissions_for(g.me).send_messages:
            with contextlib.suppress(discord.HTTPException):
                await channel.send(embed=render.notice("g.welcome", self.lang(g.id)))

    async def on_guild_remove(self, g: discord.Guild) -> None:
        self.store.guild_left(g.id)

    async def on_guild_update(self, _: discord.Guild, g: discord.Guild) -> None:
        self.store.upsert_guild(g.id, name=g.name, icon=g.icon.url if g.icon else None, owner_id=g.owner_id,
                                member_count=g.member_count or 0)
        await self.refresh_audit(g)

    # --- helpers ----------------------------------------------------------------------------
    def lang(self, gid: int) -> Lang:
        return self.store.settings(gid)["lang"]

    def minor_roles(self, gid: int) -> frozenset[int]:
        return frozenset(self.store.settings(gid)["minor_role_ids"]) if self.store.guild(gid) else frozenset()

    def missing(self, g: discord.Guild) -> list[str]:
        perms = g.me.guild_permissions
        return [name for attr, name in NEEDED.items() if not getattr(perms, attr)]

    def guild_meta(self, gid: int) -> dict[str, Any] | None:
        g = self.get_guild(gid)
        if g is None:
            return None
        ch_id = self.store.settings(gid)["alert_channel_id"]
        ch = g.get_channel(ch_id) if ch_id else None
        return {
            "missing": self.missing(g),
            "alert_channel": f"#{ch.name}" if ch else None,
            "channels": [{"id": str(c.id), "name": c.name} for c in g.text_channels],
            "roles": [{"id": str(r.id), "name": r.name} for r in reversed(g.roles) if not r.is_default()
                      and not r.managed],
        }

    def is_admin(self, gid: int, uid: int) -> bool:
        g = self.get_guild(gid)
        m = g.get_member(uid) if g else None
        return bool(m and (m.guild_permissions.manage_guild or m.id == g.owner_id))

    async def refresh_audit(self, g: discord.Guild) -> GuildFacts:
        triggers: set[int] = set()
        if g.me.guild_permissions.manage_guild:
            with contextlib.suppress(discord.HTTPException):
                triggers = {r.trigger.type.value for r in await g.fetch_automod_rules() if r.enabled}
        humans = [m for m in g.members if not m.bot]
        facts = GuildFacts(
            member_count=g.member_count or len(g.members), verification_level=g.verification_level.value,
            content_filter=g.explicit_content_filter.value, mfa_level=g.mfa_level.value,
            nsfw_level=g.nsfw_level.value, automod_triggers=frozenset(triggers),
            nsfw_channels=sum(c.is_nsfw() for c in g.text_channels),
            everyone_mentions=g.default_role.permissions.mention_everyone,
            admin_humans=sum(m.guild_permissions.administrator for m in humans),
            admin_bots=sum(m.guild_permissions.administrator for m in g.members if m.bot and m.id != self.user.id),
            mods=sum(1 for m in humans if (p := m.guild_permissions).kick_members or p.ban_members
                     or p.moderate_members or p.manage_messages or p.administrator),
            has_rules_channel=g.rules_channel is not None, guard_missing=tuple(self.missing(g)),
            alert_channel_public=bool((ch := g.get_channel(self.store.settings(g.id)["alert_channel_id"] or 0))
                                      and ch.permissions_for(g.default_role).view_channel),
        )
        raw = dataclasses.asdict(facts)
        raw["automod_triggers"] = sorted(facts.automod_triggers)
        self.store.save_audit(g.id, {"facts": raw})
        return facts

    async def _cache_invites(self, g: discord.Guild) -> None:
        if not g.me.guild_permissions.manage_guild:
            return
        with contextlib.suppress(discord.HTTPException):
            self._invites[g.id] = {i.code: (i.uses or 0, i.inviter.id if i.inviter else None)
                                   for i in await g.invites()}

    async def _which_invite(self, g: discord.Guild) -> tuple[str | None, int | None]:
        before = self._invites.get(g.id)
        await self._cache_invites(g)
        after = self._invites.get(g.id)
        if before is None or after is None:
            return None, None
        used = [(code, inviter) for code, (uses, inviter) in after.items() if uses > before.get(code, (0, None))[0]]
        if not used and g.vanity_url_code:
            return g.vanity_url_code, None
        return used[0] if len(used) == 1 else (None, None)

    # --- events -----------------------------------------------------------------------------
    async def on_member_join(self, m: discord.Member) -> None:
        code, inviter = await self._which_invite(m.guild)
        self.store.upsert_guild(m.guild.id, name=m.guild.name, icon=m.guild.icon.url if m.guild.icon else None,
                                owner_id=m.guild.owner_id, member_count=m.guild.member_count or 0)
        outs = self.engine.on_join(JoinEvent(m.guild.id, member_info(m, self.minor_roles(m.guild.id)),
                                             int(time.time()), code, inviter))
        await self.execute(outs)

    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent) -> None:
        self.engine.on_leave(payload.guild_id, payload.user.id)

    async def on_member_update(self, _: discord.Member, m: discord.Member) -> None:
        self.engine.on_member_update(m.guild.id, member_info(m, self.minor_roles(m.guild.id)))

    async def on_user_update(self, _: discord.User, u: discord.User) -> None:
        for g in u.mutual_guilds:
            if (m := g.get_member(u.id)) is not None:
                self.engine.on_member_update(g.id, member_info(m, self.minor_roles(g.id)))

    async def on_invite_create(self, inv: discord.Invite) -> None:
        if inv.guild and isinstance(inv.guild, discord.Guild):
            inviter = inv.inviter.id if inv.inviter else None
            self._invites.setdefault(inv.guild.id, {})[inv.code] = (inv.uses or 0, inviter)

    async def on_message(self, msg: discord.Message) -> None:
        if msg.guild is None or not msg.content:
            return
        if not self._test_webhook(msg) and (msg.author.bot or not isinstance(msg.author, discord.Member)):
            return
        if self.store.guild(msg.guild.id) is None:
            return
        ev = self._message_event(msg)
        (model,) = await semantic.guard_check([ev.content])  # off the event loop; shed under load
        await self.execute(self.engine.on_message(dataclasses.replace(ev, model=model) if model else ev))

    def _test_webhook(self, msg: discord.Message) -> bool:
        """Dev server only: plain webhook messages play members, so one person can test Guard (tools/testdrive.py)."""
        return bool(msg.webhook_id and msg.guild and msg.guild.id == self._dev_guild
                    and msg.interaction_metadata is None)

    def _message_event(self, msg: discord.Message, *, backfill: bool = False) -> MessageEvent:
        reply_to = None
        ref = msg.reference.resolved if msg.reference else None
        if isinstance(ref, discord.Message):
            reply_to = ref.author.id
        author = msg.author if isinstance(msg.author, discord.Member) else msg.guild.get_member(msg.author.id)
        return MessageEvent(
            guild_id=msg.guild.id, channel_id=msg.channel.id, message_id=msg.id,
            author=webhook_persona(msg) if self._test_webhook(msg)
            else member_info(author or msg.author, self.minor_roles(msg.guild.id)), content=msg.content,
            at=int(msg.created_at.timestamp()), reply_to=reply_to,
            mentions=tuple(u.id for u in msg.mentions if not u.bot), channel_name=getattr(msg.channel, "name", ""),
            backfill=backfill,
        )

    async def on_raw_message_delete(self, p: discord.RawMessageDeleteEvent) -> None:
        if p.guild_id:
            self.engine.on_delete(p.guild_id, p.message_id)

    async def on_raw_bulk_message_delete(self, p: discord.RawBulkMessageDeleteEvent) -> None:
        if p.guild_id:
            for mid in p.message_ids:
                self.engine.on_delete(p.guild_id, mid)

    async def on_audit_log_entry_create(self, e: discord.AuditLogEntry) -> None:
        if e.user_id == self.user.id or e.target is None:
            return
        kind = {discord.AuditLogAction.ban: "ban", discord.AuditLogAction.kick: "kick"}.get(e.action)
        if e.action is discord.AuditLogAction.member_update and getattr(e.after, "timed_out_until", None):
            kind = "timeout"
        if kind:
            by = e.guild.get_member(e.user_id) if e.user_id else None
            self.engine.on_mod_action(e.guild.id, e.target.id, kind, by=e.user_id,
                                      by_name=by.display_name if by else None)

    async def on_automod_action(self, ex: discord.AutoModAction) -> None:
        if ex.rule_trigger_type in (discord.AutoModRuleTriggerType.keyword_preset,
                                    discord.AutoModRuleTriggerType.keyword):
            self.store.observe(ex.guild_id, ex.user_id, "behave.automod", 10, channel_id=ex.channel_id)
            self.engine.rescore(ex.guild_id, ex.user_id)

    # --- doing things -----------------------------------------------------------------------
    def dashboard_member_url(self, gid: int, uid: int | None) -> str | None:
        if not self.dashboard_url:
            return None
        return f"{self.dashboard_url}/#/g/{gid}/member/{uid}" if uid else f"{self.dashboard_url}/#/g/{gid}"

    async def post_alert(self, aid: int, *, edit: bool = False) -> None:
        from guildward.guard.commands import alert_view

        row = self.store.alert(aid)
        if row is None:
            return
        gid = row["guild_id"]
        settings = self.store.settings(gid)
        g = self.get_guild(gid)
        channel = g.get_channel(settings["alert_channel_id"]) if g and settings["alert_channel_id"] else None
        if not isinstance(channel, discord.TextChannel | discord.Thread):
            return
        if channel.permissions_for(g.default_role).view_channel:
            log.warning("guard: alert channel %s in %s is public; alert %s kept off Discord", channel.id, gid, aid)
            return  # alerts name kids and quote messages; still on the dashboard
        lang = settings["lang"]
        a = self.reports.alert_dict(row, lang)
        embed = render.alert_embed(a, lang, dashboard_url=self.dashboard_member_url(gid, row["user_id"]),
                                   quote=settings["quote_in_alerts"])
        view = alert_view(a, lang) if a["status"] == "open" else None
        try:
            if row["post_id"] and (edit or a["status"] != "open"):
                msg = channel.get_partial_message(row["post_id"])
                await msg.edit(embed=embed, view=view)
                return
            ping = f"<@&{settings['ping_role_id']}>" if settings["ping_role_id"] and a["level"] == "red" else None
            msg = await channel.send(content=ping, embed=embed, view=view,
                                     allowed_mentions=discord.AllowedMentions(roles=True, users=False))
            self.store.x("UPDATE alerts SET post_id=?, post_channel_id=? WHERE id=?", msg.id, channel.id, aid)
        except discord.HTTPException as e:
            log.warning("guard: could not post alert (%s)", e.status)

    async def execute(self, outs: list[Out]) -> None:
        for o in outs:
            try:
                if o.kind == "alert":
                    await self.post_alert(o.alert_id)
                elif o.kind == "alert_update":
                    await self.post_alert(o.alert_id, edit=True)
                elif o.kind == "warn_dm":
                    await self._warn(o.guild_id, o.user_id)
                else:
                    ok, _ = await self.act(o.guild_id, o.user_id, o.kind, by_id=None, by_name="Guard",
                                           alert_id=o.alert_id, channel_id=o.channel_id, message_id=o.message_id,
                                           seconds=o.seconds, resolve=False)
                    if not ok:
                        log.info("guard: automatic %s not possible", o.kind)
            except Exception:
                log.exception("guard: output %s failed", o.kind)

    async def _warn(self, gid: int, uid: int | None) -> None:
        g = self.get_guild(gid)
        m = g.get_member(uid) if g and uid else None
        if m is None:
            return
        lang = "sv" if str(getattr(m, "locale", "") or g.preferred_locale).startswith("sv") else self.lang(gid)
        with contextlib.suppress(discord.HTTPException):
            talk = helplines.phrases(helplines.region_for(self, m.id, lang), lang)["talk"]
            await m.send(embed=render.warn_embed(g.name, lang, talk))
            self.store.bump(gid, "warned")

    async def act(self, gid: int, uid: int | None, action: str, *, by_id: int | None, by_name: str | None,
                  alert_id: int | None = None, channel_id: int | None = None, message_id: int | None = None,
                  seconds: int = 3600, resolve: bool = True, actor: discord.Member | None = None) -> tuple[bool, str]:
        """One entry point for buttons, dashboard and automatic actions. Returns (ok, translated text)."""
        lang = self.lang(gid)
        g = self.get_guild(gid)
        if g is None:
            return False, t("g.gone", lang)
        if alert_id and (row := self.store.alert(alert_id)):
            uid = uid or row["user_id"]
            channel_id = channel_id or row["channel_id"]
            message_id = message_id or row["message_id"]
        perm = ACTION_PERM.get(action)
        if perm:
            if actor is not None and not getattr(actor.guild_permissions, perm):
                return False, t("g.no_perm_user", lang, perm=NEEDED.get(perm, perm))
            if not getattr(g.me.guild_permissions, perm):
                return False, t("g.no_perm_bot", lang, perm=NEEDED.get(perm, perm))
        member = g.get_member(uid) if uid else None
        reason = f"Guildward Guard{f' alert #{alert_id}' if alert_id else ''}{f' by {by_name}' if by_name else ''}"
        try:
            if action in ("timeout", "kick", "ban", "quarantine") and member is not None and \
                    member.top_role >= g.me.top_role:
                return False, t("g.hierarchy", lang)
            if action == "timeout":
                if member is None:
                    return False, t("g.gone", lang)
                await member.timeout(timedelta(seconds=seconds or 3600), reason=reason)
            elif action == "kick":
                if member is None:
                    return False, t("g.gone", lang)
                await member.kick(reason=reason)
            elif action == "ban":
                await g.ban(discord.Object(uid), reason=reason, delete_message_seconds=3600)
            elif action == "delete":
                ch = g.get_channel_or_thread(channel_id) if channel_id else None
                if ch is None or not message_id:
                    return False, t("g.gone", lang)
                await ch.get_partial_message(message_id).delete()
            elif action == "quarantine":
                role = g.get_role(self.store.settings(gid)["quarantine_role_id"] or 0)
                if member is None or role is None:
                    return False, t("g.gone", lang)
                await member.add_roles(role, reason=reason)
            elif action in ("watch", "trust", "clear"):
                status = {"watch": "watch", "trust": "trusted", "clear": "none"}[action]
                self.store.set_member(gid, uid, status=status, status_by=by_id)
                self.store.event(gid, uid, "status", {"status": status, "by": by_name})
                self.engine.rescore(gid, uid)
            elif action not in ("resolve", "false_positive"):
                return False, t("g.fix_unknown", lang)
        except discord.NotFound:
            return False, t("g.gone", lang)
        except discord.HTTPException:
            return False, t("g.failed", lang)

        if action in ("timeout", "kick", "ban", "quarantine") and uid:
            self.engine.on_mod_action(gid, uid, action, by=by_id, by_name=by_name, source="guard")
        if alert_id and resolve:
            status = "false_positive" if action == "false_positive" else "resolved" if action != "watch" else None
            if status:
                self.store.resolve_alert(alert_id, status=status, by=by_id, by_name=by_name, action=action)
                if action == "false_positive" and uid:
                    self.engine.rescore(gid, uid)
                await self.post_alert(alert_id, edit=True)
        return True, t("g.done", lang, action=t(f"g.act_{action}", lang))

    async def apply_fix(self, gid: int, fix: str) -> tuple[bool, str]:
        lang = self.lang(gid)
        g = self.get_guild(gid)
        if g is None:
            return False, t("g.gone", lang)
        if fix not in FIXES:
            return False, t("g.fix_unknown", lang)
        reason = "Guildward Guard recommended safety setting"
        rule = {"automod_presets": AM_PRESET, "automod_spam": AM_SPAM, "automod_mentions": AM_MENTION}
        try:
            if fix == "verification":
                if g.verification_level.value < 2:
                    await g.edit(verification_level=discord.VerificationLevel.medium, reason=reason)
            elif fix == "content_filter":
                await g.edit(explicit_content_filter=discord.ContentFilter.all_members, reason=reason)
            elif fix == "everyone_mentions":
                perms = g.default_role.permissions
                perms.update(mention_everyone=False)
                await g.default_role.edit(permissions=perms, reason=reason)
            else:
                trigger = {
                    AM_PRESET: discord.AutoModTrigger(type=discord.AutoModRuleTriggerType.keyword_preset,
                                                      presets=discord.AutoModPresets.all()),
                    AM_SPAM: discord.AutoModTrigger(type=discord.AutoModRuleTriggerType.spam),
                    AM_MENTION: discord.AutoModTrigger(type=discord.AutoModRuleTriggerType.mention_spam,
                                                       mention_limit=5),
                }[rule[fix]]
                await g.create_automod_rule(
                    name=f"Guildward: {fix.removeprefix('automod_')}",
                    event_type=discord.AutoModRuleEventType.message_send, trigger=trigger,
                    actions=[discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)],
                    enabled=True, reason=reason)
        except discord.Forbidden:
            return False, t("g.no_perm_bot", lang, perm="Manage Server / Manage Roles")
        except discord.HTTPException:
            return False, t("g.failed", lang)
        await self.refresh_audit(g)
        return True, t(f"g.fix_ok_{fix}", lang)

    async def scan(self, g: discord.Guild, days: int) -> dict[str, int]:
        """Read recent history so scores reflect the past, not just from install. Never alerts on it."""
        after = discord.utils.utcnow() - timedelta(days=days)
        stats = {"msgs": 0, "channels": 0, "flagged": 0, "members": 0}
        before_flagged = sum(self.store.series(g.id, "flagged", 31))
        authors: set[int] = set()
        for ch in g.text_channels:
            if not ch.permissions_for(g.me).read_message_history:
                continue
            stats["channels"] += 1
            chunk: list[MessageEvent] = []
            try:
                async for msg in ch.history(limit=2000, after=after, oldest_first=True):
                    if not msg.content or (msg.author.bot and not self._test_webhook(msg)):
                        continue
                    chunk.append(ev := self._message_event(msg, backfill=True))
                    authors.add(ev.author.id)
                    stats["msgs"] += 1
                    if len(chunk) >= SCAN_CHUNK:
                        await self._backfill(chunk)
                        chunk = []
            except discord.HTTPException:
                pass
            await self._backfill(chunk)
        stats["flagged"] = sum(self.store.series(g.id, "flagged", 31)) - before_flagged
        stats["members"] = len(authors)
        return stats

    async def _backfill(self, events: list[MessageEvent]) -> None:
        """History in order; the model reads a chunk at a time at Guard priority (kids' checks go first)."""
        models = await semantic.guard_check([e.content for e in events])
        for ev, model in zip(events, models, strict=True):
            self.engine.on_message(dataclasses.replace(ev, model=model) if model else ev)

    def system(self) -> dict[str, Any]:
        return {"guard_online": self.is_ready(), "latency_ms": round(self.latency * 1000) if self.is_ready() else None,
                "events_per_min": self.engine.events_per_min(), "model": semantic.status()}
