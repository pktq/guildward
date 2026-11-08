"""The one Guildward bot. Kids install it on their own account (checks, forwards, alerts); server admins
add the same bot to a server for Guard (whole-server monitoring). One application, one token.

Admins can also add it commands-only (no bot user, reads nothing) so members get the checks in that server;
Guard features need the full install.
"""

from __future__ import annotations

import logging
from pathlib import Path

import aiohttp
import discord

from guildward.bot import commands, dm, tasks
from guildward.bot import help as kidhelp
from guildward.config import Settings
from guildward.guard import commands as guard_commands
from guildward.guard.bot import INSTALL_URL, GuardBot, needed_permissions
from guildward.guard.store import Store
from guildward.intel import semantic
from guildward.intel.links import make_session
from guildward.intel.rules import is_private, rules
from guildward.pocket import Pocket

log = logging.getLogger(__name__)

USER_INSTALL_URL = "https://discord.com/oauth2/authorize?client_id={id}&integration_type=1&scope=applications.commands"
SERVER_INSTALL_URL = "https://discord.com/oauth2/authorize?client_id={id}&integration_type=0&scope=applications.commands"


class GuildwardBot(GuardBot):
    def __init__(self, settings: Settings, store: Store | None = None, *, sync: bool = False) -> None:
        discord.VoiceClient.warn_nacl = discord.VoiceClient.warn_dave = False  # we never use voice
        store = store if store is not None else Store()
        super().__init__(store, dashboard_url=settings.dashboard_url, dev_guild_id=settings.dev_guild_id, sync=sync)
        self.settings = settings
        self.pocket = Pocket(store)
        self.engine.pocket = self.pocket  # Guard's flagged handles help kids' checks (Safety Network servers only)
        self.guard = self  # kids' checks read Guard grades from the same bot
        self.web: aiohttp.ClientSession | None = None  # links, AI, OAuth (Client.http is discord.py's own)

    async def setup_hook(self) -> None:
        if is_private():
            log.info("detection rules: private set (%s)", rules().__name__)
        else:
            log.warning("detection rules: PUBLIC EXAMPLE set only; set GUILDWARD_PRIVATE for real detection")
        self.web = make_session()  # public addresses only: link checks fetch attacker-chosen URLs
        if self.settings.model:  # loads in the background (first start downloads ~135 MB); rules work meanwhile
            semantic.install(semantic.Service(cache=Path(self.settings.database).parent / "models")).start()
        else:
            log.warning("message model off (GUILDWARD_MODEL=off): rules only")
        await self.tree.set_translator(commands.Translator())
        guard_commands.setup(self)
        commands.setup(self)  # after Guard: its error handler is the one that stays
        for view in kidhelp.persistent_views():  # help menus keep working after a restart
            self.add_view(view)
        self.loop.create_task(tasks.run(self))
        self.loop.create_task(self._housekeeping())
        if self._sync:
            synced = await self.tree.sync()
            log.info("synced %d global commands (can take a while to appear)", len(synced))
        if self._dev_guild:
            await self._sync_dev_guild(self._dev_guild)

    async def _sync_dev_guild(self, guild_id: int) -> None:
        # Guild copy shows up instantly for testing; user installs only come from the global set.
        guild = discord.Object(guild_id)
        self.tree.copy_global_to(guild=guild)
        try:
            synced = await self.tree.sync(guild=guild)
        except discord.Forbidden:
            log.warning("can't add commands to DEV_GUILD_ID %s: the app isn't installed there. Add it with %s "
                        "or leave DEV_GUILD_ID empty.", guild_id, SERVER_INSTALL_URL.format(id=self.application_id))
            return
        log.info("synced %d commands to dev guild", len(synced))

    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            if not message.author.bot:
                await dm.on_dm(self, message)
            return
        await super().on_message(message)  # Guard, in servers that added the full bot

    async def close(self) -> None:
        if (svc := semantic.service()) is not None:
            svc.stop()
        if self.web:
            await self.web.close()
        await super().close()

    async def on_ready(self) -> None:
        aid = self.application_id
        log.info("ready as %s. Kids install on their account: %s", self.user, USER_INSTALL_URL.format(id=aid))
        log.info("Server, checks only (reads nothing): %s", SERVER_INSTALL_URL.format(id=aid))
        log.info("Server, full Guard: %s", INSTALL_URL.format(id=aid, perms=needed_permissions().value))
        await super().on_ready()
