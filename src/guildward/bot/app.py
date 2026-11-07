from __future__ import annotations

import logging

import discord
from discord import app_commands

from guildward.bot import commands
from guildward.config import Settings
from guildward.intel.rules import is_private, rules

log = logging.getLogger(__name__)


USER_INSTALL_URL = "https://discord.com/oauth2/authorize?client_id={id}&integration_type=1&scope=applications.commands"
SERVER_INSTALL_URL = "https://discord.com/oauth2/authorize?client_id={id}&integration_type=0&scope=applications.commands"


class _DropIntentWarning(logging.Filter):
    """We run with no intents on purpose; discord.py warns about it on every start."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "Guilds intent seems to be disabled" not in record.getMessage()


class GuildwardBot(discord.Client):
    def __init__(self, settings: Settings, *, sync: bool = False) -> None:
        discord.VoiceClient.warn_nacl = discord.VoiceClient.warn_dave = False  # we never use voice
        logging.getLogger("discord.state").addFilter(_DropIntentWarning())
        # Interactions need no gateway intents; asking for none keeps us out of every server's data.
        super().__init__(intents=discord.Intents.none())
        self.settings = settings
        self.tree = app_commands.CommandTree(self)
        self._sync = sync

    async def setup_hook(self) -> None:
        if is_private():
            log.info("detection rules: private set (%s)", rules().__name__)
        else:
            log.warning("detection rules: PUBLIC EXAMPLE set only; set GUILDWARD_PRIVATE for real detection")
        await self.tree.set_translator(commands.Translator())
        commands.setup(self)
        if self._sync:
            synced = await self.tree.sync()
            log.info("synced %d global commands (can take a while to appear)", len(synced))
        if self.settings.dev_guild_id:
            await self._sync_dev_guild(self.settings.dev_guild_id)

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

    async def on_ready(self) -> None:
        log.info("ready as %s. Install on your account: %s", self.user, USER_INSTALL_URL.format(id=self.application_id))
