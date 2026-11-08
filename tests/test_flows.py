"""Kid-side check flow with a fake bot: crowd flags, memory, forwards, handles linked to flagged accounts."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

from guildward.bot import dm, flows
from guildward.config import Settings
from guildward.core.models import Level
from guildward.guard.store import Store
from guildward.pocket import Pocket


def sf(days_ago: float, n: int = 0) -> int:
    from guildward.core.snowflake import DISCORD_EPOCH_MS

    return ((int((time.time() - days_ago * 86_400) * 1000) - DISCORD_EPOCH_MS) << 22) + n


KIDS = [sf(800, i) for i in range(5)]
GROOMER = sf(20, 99)


def fake_bot() -> SimpleNamespace:
    store = Store(":memory:")
    return SimpleNamespace(store=store, pocket=Pocket(store), web=None, guard=None,
                           settings=Settings(token="x", dev_guild_id=None, log_level="INFO"))


def author(uid: int, name: str = "chill_gamer_19") -> SimpleNamespace:
    return SimpleNamespace(id=uid, name=name, global_name=None, avatar=None,
                           public_flags=SimpleNamespace(spammer=False))


def run(coro):
    return asyncio.run(coro)


def test_flagged_sender_raises_a_harmless_looking_message():
    bot = fake_bot()
    bot.pocket.see_account(GROOMER, "chill_gamer_19", None, None)
    bot.pocket.owner_action(GROOMER, "confirm", by=1)
    v = run(flows.check_message(bot, KIDS[0], "en", ["hey whats up"], author=author(GROOMER), memory_key=GROOMER))
    assert v.level is Level.RED and any(s.code == "crowd.confirmed" for s in v.signals)


def test_memory_turns_separate_checks_into_a_pattern():
    bot = fake_bot()
    kid = KIDS[0]
    bot.pocket.touch_user(kid, "en")
    a = author(GROOMER)
    run(flows.check_message(bot, kid, "en", ["how old r u btw"], author=a, memory_key=GROOMER))
    time.sleep(1.01)
    v = run(flows.check_message(bot, kid, "en", ["dont tell ur parents ok"], author=a, memory_key=GROOMER))
    assert any(s.code == "pocket.pattern" for s in v.signals)
    # The check was recorded for the shared flags, and the kid now watches this account.
    assert bot.pocket.facts(GROOMER).checkers == 1
    assert [w["user_id"] for w in bot.pocket.watches_to_check()] == [GROOMER]


def test_forwarded_conversation_reads_stages_together():
    bot = fake_bot()
    # Phrases the public example rules know too, so this runs on both rule sets.
    texts = ["how old r u", "dont tell ur parents ok", "send me a pic of u", "where do u live"]
    v = run(flows.check_message(bot, KIDS[0], "en", texts, author=None, memory_key="c:123"))
    convo = [s for s in v.signals if s.code == "pocket.convo"]
    assert convo and v.level is Level.RED


def test_forward_with_handle_of_flagged_account_is_flagged():
    bot = fake_bot()
    bot.pocket.see_account(GROOMER, "bad", None, None)
    bot.pocket.record_marks(GROOMER, "add me on snap: zebra.castle77", "pocket")
    bot.pocket.owner_action(GROOMER, "confirm", by=1)
    v = run(flows.check_message(bot, KIDS[0], "en", ["my snap is zebra.castle77 hmu"], author=None, memory_key=None))
    assert any(s.code == "pocket.handle_known" for s in v.signals) and v.level is Level.RED


def test_own_message_is_not_recorded_against_the_kid():
    bot = fake_bot()
    kid = KIDS[0]
    run(flows.check_message(bot, kid, "en", ["how old r u"], author=author(kid, "me"), memory_key=kid))
    assert bot.pocket.facts(kid).checkers == 0


def test_dm_texts_reads_forward_snapshots():
    msg = SimpleNamespace(reference=SimpleNamespace(channel_id=555), content="",
                          message_snapshots=[SimpleNamespace(content="whats ur snap")])
    assert dm._texts(msg) == [("whats ur snap", 555)]
    plain = SimpleNamespace(reference=None, content="discord.gg/abc", message_snapshots=[])
    assert dm._texts(plain) == [("discord.gg/abc", None)]
