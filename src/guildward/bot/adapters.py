"""discord.py objects -> plain facts for the intel layer. The only place intel meets Discord types."""

from __future__ import annotations

import re

import discord

from guildward.intel.person import UserFacts
from guildward.intel.server import InviteFacts

# discord.gg/x, discord.com/invite/x, discordapp.com/invite/x, or a bare code.
_INVITE_RX = re.compile(
    r"^(?:(?:https?://)?(?:www\.)?(?:discord\.gg|discord(?:app)?\.com/invite)/)?([A-Za-z0-9-]{2,32})/?$"
)
# Badges that say nothing about trust, or that we score separately.
_NOT_BADGES = {"spammer", "verified_bot", "bot_http_interactions", "system", "team_user"}


def parse_invite_code(text: str) -> str | None:
    m = _INVITE_RX.match(text.strip().split("?", 1)[0])
    return m.group(1) if m else None


def invite_facts(inv: discord.Invite) -> InviteFacts:
    g = inv.guild if isinstance(inv.guild, discord.PartialInviteGuild | discord.Guild) else None
    nsfw = getattr(g, "nsfw_level", None)
    verify = getattr(g, "verification_level", None)
    return InviteFacts(
        code=inv.code,
        guild_id=g.id if g else None,
        name=g.name if g else None,
        description=getattr(g, "description", None),
        channel_name=getattr(inv.channel, "name", None),
        verification_level=verify.value if verify is not None else None,
        nsfw_level=nsfw.value if nsfw is not None else None,
        features=frozenset(str(f) for f in (getattr(g, "features", None) or ())),
        member_count=inv.approximate_member_count,
        presence_count=inv.approximate_presence_count,
        inviter_id=inv.inviter.id if inv.inviter else None,
        is_group_dm=inv.type is discord.InviteType.group_dm,
        is_friend_invite=inv.type is discord.InviteType.friend,
    )


def user_facts(user: discord.User | discord.Member, *, invoker_id: int) -> UserFacts:
    flags = user.public_flags
    return UserFacts(
        id=user.id,
        username=user.name,
        global_name=user.global_name,
        has_avatar=user.avatar is not None,
        has_banner=getattr(user, "banner", None) is not None,
        is_bot=user.bot,
        is_verified_bot=flags.verified_bot,
        is_system=user.system,
        badge_count=sum(1 for name, on in flags if on and name not in _NOT_BADGES),
        is_self=user.id == invoker_id,
        discord_spammer=flags.spammer,
    )


def display_name(user: discord.User | discord.Member) -> str:
    """Shows the real @username too: impersonators copy display names, not usernames."""
    if user.global_name and user.global_name != user.name:
        return f"{user.global_name} (@{user.name})"
    return f"@{user.name}"
