"""Pocket data layer: shared flags, alt links, memory, watches, owner review, erasure."""

from __future__ import annotations

import time

from guildward.core.snowflake import DISCORD_EPOCH_MS
from guildward.guard.engine import Engine, MemberInfo, MessageEvent
from guildward.guard.store import Store
from guildward.pocket import Pocket


def sf(days_ago: float, n: int = 0) -> int:
    ms = int((time.time() - days_ago * 86_400) * 1000) - DISCORD_EPOCH_MS
    return (ms << 22) + n


def make() -> Pocket:
    p = Pocket(Store(":memory:"))
    return p


KIDS = [sf(800, i) for i in range(10)]
GROOMER = sf(20, 99)


def test_brigade_of_new_accounts_does_not_flag():
    p = make()
    p.see_account(GROOMER, "classmate", None, None)
    for i in range(6):
        kid = sf(1, 200 + i)  # day-old accounts
        p.touch_user(kid, "en")
        p.report(kid, GROOMER, "hate")
    assert p.level_of(GROOMER) == "none"


def test_credible_reports_plus_red_checks_flag_and_alert_watchers():
    p = make()
    p.see_account(GROOMER, "chill_gamer_19", None, None)
    watcher = KIDS[9]
    p.touch_user(watcher, "en")
    p.record_check(watcher, GROOMER, "person", "yellow")
    for kid in KIDS[:3]:
        p.touch_user(kid, "en")
        p.record_check(kid, GROOMER, "message", "red")
        p.report(kid, GROOMER, "age_pics")
    assert p.level_of(GROOMER) == "flagged"
    news = [p.watch_news(w) for w in p.watches_to_check() if w["kid_id"] == watcher]
    assert news == ["flagged"]
    p.watch_done(watcher, GROOMER, "flagged")
    assert [p.watch_news(w) for w in p.watches_to_check() if w["kid_id"] == watcher] == [None]
    codes = {s.code for s in p.account_signals(GROOMER)}
    assert "crowd.flagged" in codes


def test_owner_confirm_and_clear():
    p = make()
    p.see_account(GROOMER, "x", None, None)
    p.touch_user(KIDS[0], "en")
    p.report(KIDS[0], GROOMER, "threat")
    assert p.owner_action(GROOMER, "confirm", by=1)
    assert p.level_of(GROOMER) == "confirmed"
    rows = p.owner_accounts("confirmed")["accounts"]
    assert rows[0]["id"] == str(GROOMER) and rows[0]["reasons"] == {"threat": 1}
    assert "who" not in str(rows)  # reporter identities never leave the store
    assert p.owner_action(GROOMER, "clear", by=1)
    assert p.level_of(GROOMER) == "cleared"
    assert not p.owner_action(GROOMER, "nonsense", by=1)


def test_alt_pushing_same_snapchat_links_to_flagged_account():
    p = make()
    p.see_account(GROOMER, "chill_gamer_19", None, None)
    p.record_marks(GROOMER, "add me on snap: zebra.castle77 its more private", "pocket")
    p.owner_action(GROOMER, "confirm", by=1)
    alt = sf(2, 98)
    p.see_account(alt, "totally_new", None, None)
    p.record_marks(alt, "lets talk on snapchat, my snap is zebra.castle77", "pocket")
    links = p.links_of(alt)
    assert any(ln.kind == "handle" and ln.other_id == GROOMER and ln.other_level == "confirmed" for ln in links)
    assert any(s.code == "crowd.linked" for s in p.account_signals(alt))
    # A forwarded DM (no sender known) pushing the same handle matches too.
    assert [m[0] for m in p.match_text("hey add my snap zebra.castle77")] == ["handle"]
    assert p.match_text("gg wp see u tomorrow") == []


def test_guard_flagged_message_feeds_kid_side_matching():
    store = Store(":memory:")
    p = Pocket(store)
    eng = Engine(store)
    eng.pocket = p
    gid, cid = 900, 901
    store.upsert_guild(gid, name="kids", icon=None, owner_id=1, member_count=10)
    store.update_settings(gid, {"network_share": True})
    kid = MemberInfo(id=KIDS[0], username="kid")
    bad = MemberInfo(id=GROOMER, username="bad")
    t0 = int(time.time())
    eng.on_message(MessageEvent(gid, cid, 1, kid, "im 12 lol", t0))
    eng.on_message(MessageEvent(gid, cid, 2, bad, "how old r u? dont tell ur parents, add my snap zebra.castle77",
                                t0 + 5, reply_to=KIDS[0]))
    assert p.match_text("my snap is zebra.castle77") == []  # not confirmed yet: auto-flags never propagate
    p.see_account(GROOMER, "bad", None, None)
    p.owner_action(GROOMER, "confirm", by=1)
    assert any(m[1] == GROOMER for m in p.match_text("my snap is zebra.castle77"))
    store.forget_guild(gid)  # /guard erase also drops the hashed handles Guard shared
    assert p.match_text("my snap is zebra.castle77") == []


def test_pattern_memory_adds_up_and_forget_erases():
    p = make()
    kid = KIDS[0]
    p.touch_user(kid, "en")
    p.remember(kid, GROOMER, ["msg.age_probe"], event=1)
    assert p.pattern_signal(kid, GROOMER, "en") is None  # one check is not a pattern
    p.remember(kid, GROOMER, ["msg.age_probe"], event=1)
    assert p.pattern_signal(kid, GROOMER, "en") is None  # checking the same message again isn't a second sign
    p.remember(kid, GROOMER, ["msg.secrecy", "msg.isolation"], event=2)
    sig = p.pattern_signal(kid, GROOMER, "en")
    assert sig is not None and sig.params["n"] == 2 and sig.weight >= 20
    p.forget(kid)
    assert p.pattern_signal(kid, GROOMER, "en") is None
    assert p.user(kid) is None


def test_memory_off_only_clears_that_kid():
    p = make()
    a, b = KIDS[0], KIDS[1]
    for k in (a, b):
        p.touch_user(k, "en")
        p.remember(k, GROOMER, ["msg.age_probe"], event=1)
    p.set_pref(a, "memory", False)
    assert p.store.val("SELECT COUNT(*) FROM pair_signals") == 1


def test_trusted_adult_pairing():
    p = make()
    kid, adult = KIDS[0], KIDS[5]
    p.touch_user(kid, "en")
    code = p.new_pair_code(kid)
    assert p.claim_code("WRONG1", adult) is None
    assert p.claim_code(code.lower(), adult) == kid
    assert p.adult_of(kid) == adult
    assert p.claim_code(code, adult) is None  # one use
    p.remove_adult(kid)
    assert p.adult_of(kid) is None


def test_deleted_account_tells_kid_who_got_a_warning():
    p = make()
    kid = KIDS[0]
    p.touch_user(kid, "en")
    p.see_account(GROOMER, "bad", None, None)
    p.record_check(kid, GROOMER, "message", "red")
    p.see_account(GROOMER, f"deleted_user_{GROOMER}", None, None)
    news = [p.watch_news(w) for w in p.watches_to_check()]
    assert news == ["deleted"]
    assert [p.watch_news(w) for w in p.watches_to_check()] == ["deleted"]  # not lost until it was delivered
    p.watch_done(kid, GROOMER, "deleted")
    assert [p.watch_news(w) for w in p.watches_to_check()] == [None]
    assert p.store.val("SELECT username FROM accounts WHERE user_id=?", GROOMER) == "bad"  # name kept for the alert


def test_name_changes_recorded_and_stats():
    p = make()
    for i, name in enumerate(["a1", "b2", "c3", "d4"]):
        p.see_account(GROOMER, f"name_{name}", f"N{i}", None)
    assert p.facts(GROOMER).name_changes_30d == 3
    s = p.stats()
    assert set(s) == {"users", "accounts", "reports_7d", "review", "flagged", "confirmed", "watch_alerts_7d"}


def test_owner_overview_survives_pocket_metrics():
    from guildward.guard.engine import Engine
    from guildward.guard.reports import Reports

    p = make()
    for m in ("pocket.report", "pocket.ai.red", "pocket.message.red", "pocket.watch_alert"):
        p.store.bump(0, m)
    out = Reports(Engine(p.store)).owner("en", {})
    assert out["pocket"]["message"]["red"] == 1


def test_one_reporter_cannot_mass_report():
    p = make()
    kid = KIDS[0]
    p.touch_user(kid, "en")
    ok = [p.report(kid, sf(30, 500 + i), "other") for i in range(12)]
    assert ok.count(True) == 10


def test_forget_by_an_abuser_keeps_kids_watches_on_him():
    p = make()
    kid = KIDS[0]
    p.touch_user(kid, "en")
    p.touch_user(GROOMER, "en")
    p.record_check(kid, GROOMER, "message", "red")
    p.forget(GROOMER)
    assert [w["kid_id"] for w in p.watches_to_check()] == [kid]


def test_forget_withdraws_the_kids_reports_from_flags():
    p = make()
    p.see_account(GROOMER, "x", None, None)
    for kid in KIDS[:3]:
        p.touch_user(kid, "en")
        p.record_check(kid, GROOMER, "message", "red")
        p.report(kid, GROOMER, "age_pics")
    assert p.level_of(GROOMER) == "flagged"
    p.forget(KIDS[0])
    assert p.level_of(GROOMER) != "flagged"


def test_owner_clear_beats_network_bans():
    p = make()
    for gid in (1, 2):
        p.store.upsert_guild(gid, name=str(gid), icon=None, owner_id=1, member_count=5)
        p.store.update_settings(gid, {"network_share": True})
        p.store.flag_network(GROOMER, gid, "child_safety")
    p.see_account(GROOMER, "x", None, None)
    assert p.level_of(GROOMER) == "confirmed"
    p.owner_action(GROOMER, "clear", by=1)
    assert p.level_of(GROOMER) == "cleared" and p.account_signals(GROOMER) == []


def test_auto_flagged_account_cannot_frame_another_through_a_handle():
    p = make()
    plant, victim = sf(3, 700), sf(900, 701)
    for uid in (plant, victim):
        p.see_account(uid, f"u{uid}", None, None)
    p.record_marks(plant, "add my snap victim.handle", "pocket")
    for kid in KIDS[:3]:
        p.touch_user(kid, "en")
        p.record_check(kid, plant, "message", "red")
        p.report(kid, plant, "age_pics")
    assert p.level_of(plant) == "flagged"
    p.record_marks(victim, "my snap is victim.handle", "report")
    for kid in KIDS[3:6]:
        p.touch_user(kid, "en")
        p.report(kid, victim, "other")
    assert p.level_of(victim) != "flagged"  # the link only corroborates when the other account is confirmed
    assert p.match_text("victim.handle on snap") == []


def test_region_is_saved_beside_the_toggles():
    p = Pocket(Store(":memory:"))
    p.touch_user(5, "en")
    assert p.region(5) is None
    p.set_region(5, "gb")
    p.set_pref(5, "weekly", True)  # saving a toggle keeps the country
    assert p.region(5) == "gb"
    assert "region" not in p.prefs(5) and p.prefs(5)["weekly"] is True  # settings panel shows toggles only
    for bad in ("", "x" * 9, "g b", "se;--"):
        try:
            p.set_region(5, bad)
        except ValueError:
            continue
        raise AssertionError(bad)
