from datetime import UTC, datetime, timedelta

import pytest

from guildward.core.i18n import LANGS, has, missing_translations, t
from guildward.core.models import Confidence, Kind, Level, Signal, build_verdict
from guildward.core.snowflake import DISCORD_EPOCH_MS
from guildward.intel.patterns import NameFlag, flags_in
from guildward.intel.person import UserFacts, score_user
from guildward.intel.server import InviteFacts, score_invite

NOW = datetime(2026, 11, 7, tzinfo=UTC)


def sf(days_old: float) -> int:
    """A snowflake created `days_old` days before NOW."""
    ms = int((NOW - timedelta(days=days_old)).timestamp() * 1000) - DISCORD_EPOCH_MS
    return ms << 22


def invite(**kw) -> InviteFacts:
    base = dict(code="abc", guild_id=sf(400), name="Minecraft Builders", verification_level=2,
                nsfw_level=0, member_count=800, inviter_id=sf(900))
    return InviteFacts(**(base | kw))


def user(**kw) -> UserFacts:
    base = dict(id=sf(1200), username="steve_builds", has_avatar=True)
    return UserFacts(**(base | kw))


# --- servers -----------------------------------------------------------------

def test_ordinary_server_is_green():
    v = score_invite(invite(), now=NOW)
    assert v.level is Level.GREEN and v.confidence is Confidence.LOW


def test_verified_big_server_scores_low():
    v = score_invite(invite(features=frozenset({"VERIFIED", "DISCOVERABLE", "AUTO_MODERATION"}),
                            guild_id=sf(2000), member_count=500_000), now=NOW)
    assert v.score == 0 and v.level is Level.GREEN


def test_new_tiny_open_dm_bait_server_is_red():
    v = score_invite(invite(guild_id=sf(3), name="chill hangout dms open", verification_level=0,
                            member_count=9, inviter_id=sf(2)), now=NOW)
    assert v.level is Level.RED
    codes = {s.code for s in v.risks}
    assert {"server.age_days", "server.verify_none", "server.name_dm_bait", "server.tiny",
            "server.inviter_new"} <= codes


@pytest.mark.parametrize("nsfw", [1, 3])
def test_discord_nsfw_flag_forces_red_even_if_verified(nsfw):
    v = score_invite(invite(nsfw_level=nsfw, features=frozenset({"VERIFIED", "PARTNERED"})), now=NOW)
    assert v.level is Level.RED


@pytest.mark.parametrize("name", ["Teen E-Dating 13-17", "13f looking for friends",
                                  "tonåringar dejting", "n5fw teens"])
def test_minor_sexualised_names_are_severe(name):
    v = score_invite(invite(name=name), now=NOW)
    assert v.level is Level.RED
    assert any(s.code == "server.name_minor_sexual" for s in v.signals)


def test_group_dm_invite():
    v = score_invite(InviteFacts(code="x", guild_id=None, is_group_dm=True, channel_name="fun",
                                 inviter_id=sf(5)), now=NOW)
    assert {"server.group_dm", "server.inviter_new"} <= {s.code for s in v.signals}
    assert v.level is not Level.GREEN


# --- people ------------------------------------------------------------------

def test_old_normal_account_green():
    assert score_user(user(), now=NOW).level is Level.GREEN


def test_fresh_faceless_account_yellow_or_worse():
    v = score_user(user(id=sf(3), has_avatar=False), now=NOW)
    assert v.level in (Level.YELLOW, Level.RED)


def test_fresh_impersonator_red():
    v = score_user(user(id=sf(1), username="discord_staff_support", has_avatar=False), now=NOW)
    assert v.level is Level.RED


def test_age_bait_username_red():
    assert score_user(user(username="14f_dms_open"), now=NOW).level is Level.RED


def test_system_account_green():
    assert score_user(user(is_system=True, username="Discord"), now=NOW).score == 0


def test_verified_bot_named_giveaway_not_flagged_as_impersonation():
    v = score_user(user(username="GiveawayBot", is_bot=True, is_verified_bot=True), now=NOW)
    assert not any(s.code == "person.name_impersonation" for s in v.signals)


# --- core --------------------------------------------------------------------

def test_severe_floor_and_clamp():
    v = build_verdict(Kind.MESSAGE, [Signal("x", -50, severe=True)], base=0, confidence=Confidence.LOW)
    assert v.score >= 65 and v.level is Level.RED
    assert build_verdict(Kind.MESSAGE, [Signal("x", 500)], base=0,
                         confidence=Confidence.LOW).score == 100


def test_name_flags():
    assert NameFlag.ADULT in flags_in("𝓝𝓢𝓕𝓦 chat")
    assert NameFlag.ADULT in flags_in("18+ only")
    assert flags_in("Bedwars EU", None, "") == frozenset()


def test_every_signal_code_is_translated():
    import guildward.bot.render  # noqa: F401  (registers UI strings)

    assert missing_translations() == []
    for v in (score_invite(invite(guild_id=sf(1), nsfw_level=3, name="teen dating dm me giveaway",
                                  member_count=3, verification_level=0, inviter_id=sf(1)), now=NOW),
              score_user(user(id=sf(1), username="13f nsfw discord staff dms open"), now=NOW)):
        for s in v.signals:
            assert has(s.code), s.code
            for lang in LANGS:
                assert "{" not in t(s.code, lang, **s.params)
