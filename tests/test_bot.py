"""Bot layer, offline: invite parsing, embeds, and that the command tree is built the way Discord needs."""

import asyncio
from types import SimpleNamespace

import discord
import pytest

from guildward.bot import commands, render
from guildward.bot.adapters import invite_facts, parse_invite_code, user_facts
from guildward.bot.app import GuildwardBot
from guildward.config import Settings
from guildward.core.models import Level
from guildward.intel.server import score_invite


@pytest.mark.parametrize(("text", "code"), [
    ("discord.gg/abc123", "abc123"),
    ("https://discord.gg/abc123", "abc123"),
    ("https://discord.com/invite/Minecraft-SE", "Minecraft-SE"),
    ("http://discordapp.com/invite/xyz?event=1", "xyz"),
    ("  abc123  ", "abc123"),
    ("https://evil.example/discord.gg/abc", None),
    ("discord.gg/", None),
    ("hello there", None),
])
def test_parse_invite_code(text, code):
    assert parse_invite_code(text) == code


def test_invite_adapter_and_embed():
    guild = object.__new__(discord.PartialInviteGuild)  # real type, no ConnectionState needed
    for k, val in dict(id=81384788765712384, name="Discord **API**", description=None,
                       verification_level=discord.VerificationLevel.high,
                       nsfw_level=discord.NSFWLevel.default, features=["COMMUNITY", "VERIFIED"]).items():
        setattr(guild, k, val)
    inv = SimpleNamespace(code="discord-developers", guild=guild, channel=SimpleNamespace(name="welcome"),
                          approximate_member_count=120_000, approximate_presence_count=20_000,
                          inviter=None, type=discord.InviteType.guild)
    facts = invite_facts(inv)
    assert facts.verification_level == 3 and facts.nsfw_level == 0 and "VERIFIED" in facts.features
    v = score_invite(facts)
    assert v.level is Level.GREEN

    for lang in ("en", "sv"):
        e = render.verdict_embed(v, lang, subject=facts.name)
        assert e.description == r"Discord \*\*API\*\*"  # names can't inject markdown
        assert [f.name for f in e.fields] and all(f.value for f in e.fields)
        assert len(e) <= 6000
    assert render.help_buttons(v, "en") is None


def test_user_adapter_counts_badges_not_bot_flags():
    flags = discord.PublicUserFlags._from_value(
        discord.UserFlags.hypesquad_bravery.value | discord.UserFlags.verified_bot.value)
    u = SimpleNamespace(id=1, name="x", global_name=None, avatar=None, banner=None, bot=True,
                        system=False, public_flags=flags)
    f = user_facts(u, invoker_id=2)
    assert f.badge_count == 1 and f.is_verified_bot and not f.is_self and not f.discord_spammer


def test_message_verdict_never_needs_content_back():
    v = commands.message_verdict("gg wp, that was a fun round", author_id=None)
    assert v.level is Level.GREEN


def test_command_tree_is_user_installable_everywhere():
    asyncio.run(_check_tree())


async def _check_tree():
    bot = GuildwardBot(Settings(token="x", dev_guild_id=None, log_level="INFO"))
    commands.setup(bot)
    cmds = {c.name: c for c in bot.tree.get_commands(type=None)}
    assert set(cmds) == {"check", "Safety check", "Is this sketchy?"}
    for c in cmds.values():
        assert c.allowed_installs.user and c.allowed_installs.guild
        assert c.allowed_contexts.guild and c.allowed_contexts.dm_channel and c.allowed_contexts.private_channel

    tr = commands.Translator()
    name = discord.app_commands.locale_str("Is this sketchy?", key="cmd.sketchy.name")
    assert await tr.translate(name, discord.Locale.swedish, None) == "Är det här skumt?"
    assert await tr.translate(name, discord.Locale.german, None) is None
    await bot.close()
