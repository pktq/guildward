"""Guard (server-admin mode), offline: detectors, engine pipeline, scoring, reports, privacy, dashboard API."""

import asyncio
import json
import time

import pytest
from aiohttp.test_utils import TestClient, TestServer

from guildward.core.snowflake import DISCORD_EPOCH_MS
from guildward.guard.engine import Engine, JoinEvent, MemberInfo, MessageEvent
from guildward.guard.reports import Reports
from guildward.guard.simulate import GID, simulate
from guildward.guard.store import Store, clean_settings
from guildward.guard.web import COOKIE, Dashboard, sign, verify
from guildward.intel.audit import AM_PRESET, GuildFacts, audit_guild
from guildward.intel.behavior import (
    ContactFacts,
    MemberSnapshot,
    age_disclosure,
    context_signals,
    predict,
    role_age,
    score_member,
)
from guildward.intel.person import UserFacts

G = 111


def sf(days_ago: float, n: int = 0) -> int:
    return ((int((time.time() - days_ago * 86_400) * 1000) - DISCORD_EPOCH_MS) << 22) + n


@pytest.mark.parametrize(("text", "age"), [
    ("im 13", 13), ("I'm 13 years old", 13), ("I am 25", 25), ("jag är 12", 12), ("age: 14", 14),
    ("13 yo here", 13), ("how old r u? im 15 lol", 15), ("are u 13? im 12", 12), ("im almost 14 btw", 14),
    ("im 5 minutes away", None), ("i'm 2 lazy", None), ("I'm 100% sure", None), ("are you 13?", None),
    ("im 1v1 ing", None), ("im 20 kills ahead", None), ("im 12th in the queue", None), ("gg", None),
])
def test_age_disclosure(text, age):
    assert age_disclosure(text) == age


def test_role_age_and_context_signals():
    assert role_age(["13-15"]) == "minor"
    assert role_age(["Under 18"]) == "minor"
    assert role_age(["18+"]) == "adult"
    assert role_age(["Member", "Builders"]) is None
    assert [s.code for s in context_signals("check ur dms")] == ["behave.dm_request"]
    assert [s.code for s in context_signals("join discord.gg/abc123")] == ["behave.invite_link"]
    assert context_signals("nice castle") == []


class World:
    def __init__(self, **settings):
        self.store = Store()
        self.engine = Engine(self.store)
        self.reports = Reports(self.engine)
        self.store.upsert_guild(G, name="Kids", icon=None, owner_id=1, member_count=50)
        self.store.update_settings(G, {"alert_channel_id": "5", **settings})
        self.t = int(time.time()) - 600
        self.mid = 1000

    def join(self, m: MemberInfo, **kw):
        return self.engine.on_join(JoinEvent(G, m, self.t, **kw))

    def say(self, m: MemberInfo, text: str, reply: int | None = None, *, backfill: bool = False, ch: int = 7):
        self.t += 5
        self.mid += 1
        return self.engine.on_message(MessageEvent(G, ch, self.mid, m, text, self.t, reply_to=reply,
                                                   channel_name="general", backfill=backfill))


KID = MemberInfo(sf(400, 1), "kiddo", "Kiddo", has_avatar=True)
KID2 = MemberInfo(sf(300, 2), "pal", "Pal", has_avatar=True)
NEW = MemberInfo(sf(2, 3), "nice_guy")


def _grooming(w: World, *, backfill: bool = False):
    w.join(KID)
    w.join(NEW)
    w.say(KID, "hi im 12 lol")
    outs = []
    for line in ("how old are you?", "dont tell your parents ok, our secret", "add me on snapchat",
                 "send me a pic of you"):
        outs += w.say(NEW, line, reply=KID.id, backfill=backfill)
    return outs


def test_grooming_sequence_one_growing_alert_and_protect_actions():
    w = World(mode="protect")
    outs = _grooming(w)
    kinds = [o.kind for o in outs]
    assert kinds.count("alert") == 1, kinds  # one alert, then updates: no stream of pings
    assert "alert_update" in kinds
    assert "delete" in kinds and "timeout" in kinds and "warn_dm" in kinds
    a = w.reports.alerts(G, "en")[0]
    assert a["level"] == "red" and a["target"]["minor"]
    assert a["title"].startswith("Possible grooming")

    r = w.reports.person(G, NEW.id, "en")
    assert r["verdict"]["level"] == "red"
    codes = {s["code"] for s in r["verdict"]["signals"]}
    assert {"member.escalation", "member.sexual", "member.secrecy"} <= codes
    assert r["prediction"]["escalation"] == "likely"
    assert r["contacts"][0]["user"]["minor"] and len(r["contacts"][0]["stages"]) >= 3
    assert "escalating" in r["member"]["flags"]


def test_observe_mode_alerts_but_never_acts():
    outs = _grooming(World(mode="observe"))
    assert {o.kind for o in outs} <= {"alert", "alert_update", "warn_dm"}


def test_backfill_records_but_never_alerts():
    w = World(mode="protect")
    assert _grooming(w, backfill=True) == []
    assert w.store.member(G, NEW.id)["level"] == "red"


def test_peer_kids_are_damped():
    w = World()
    w.join(KID)
    w.join(KID2)
    w.say(KID, "im 12")
    w.say(KID2, "im 13")
    outs = w.say(KID2, "how old are you? add me on snapchat", reply=KID.id)
    assert outs == []
    assert w.store.member(G, KID2.id)["level"] == "green"


def test_message_text_is_never_stored():
    w = World(mode="protect")
    _grooming(w)
    w.say(NEW, "dont tell your parents about zebracastle, our secret", reply=KID.id)
    w.engine.on_report(G, KID, NEW, channel_id=7, message_id=w.mid, content="send me a pic of you zebracastle")
    dump = "\n".join(str(tuple(r)) for t in ("members", "observations", "events", "alerts", "contacts", "reports")
                     for r in w.store.q(f"SELECT * FROM {t}"))
    for phrase in ("pic of you", "zebracastle", "our secret", "how old are you"):  # app names may be params
        assert phrase not in dump.lower()


def test_raid_detection_and_quarantine():
    w = World(mode="protect", quarantine_role_id="9")
    outs, ids = [], [sf(0.2, 100 + n) for n in range(12)]
    for n, uid in enumerate(ids):
        outs += w.join(MemberInfo(uid, f"raider{n}"))
    assert sum(o.kind == "alert" for o in outs) == 1
    assert any(o.kind == "quarantine" for o in outs)
    assert all(w.store.member(G, uid)["raid_join"] == 1 for uid in ids)


def test_reports_count_once_per_reporter():
    w = World()
    w.join(NEW)
    assert w.engine.on_report(G, KID, NEW, channel_id=7, message_id=5, content=None)
    assert w.engine.on_report(G, KID, NEW, channel_id=7, message_id=5, content=None) == []
    w.engine.on_report(G, KID2, NEW, channel_id=7, message_id=5, content=None)
    assert w.store.reporters(G, NEW.id) == 2


def test_network_ban_flags_and_alerts_elsewhere():
    w = World()
    _grooming(w)
    w.engine.on_mod_action(G, NEW.id, "ban", by=1, by_name="Mod")
    other = 222
    w.store.upsert_guild(other, name="Other", icon=None, owner_id=2, member_count=10)
    outs = w.engine.on_join(JoinEvent(other, NEW, int(time.time())))
    alert = w.store.alert(next(o.alert_id for o in outs if o.kind == "alert"))
    assert alert["kind"] == "network" and alert["level"] == "red"
    w.store.update_settings(G, {"network_share": False})  # opting out withdraws the flag
    assert w.store.network_flags(NEW.id, exclude_guild=other) == []


def test_false_positive_feeds_signal_quality():
    w = World()
    _grooming(w)
    aid = w.reports.alerts(G, "en")[0]["id"]
    w.store.resolve_alert(aid, status="false_positive", by=1, by_name="Mod", action="false_positive")
    q = {x["code"]: x for x in w.reports.owner("en", {})["signal_quality"]}
    assert any(x["false_positive"] for x in q.values())


def test_trusted_and_longtime_members_score_low():
    user = UserFacts(id=sf(1000), username="regular", has_avatar=True)
    now = int(time.time())
    base = score_member(MemberSnapshot(user=user, now=now, joined_at=now - 400 * 86_400, msg_count=500))
    assert base.level.value == "green" and any(s.code == "member.longtime_clean" for s in base.signals)
    trusted = score_member(MemberSnapshot(user=user, now=now, status="trusted", reporters=1))
    assert any(s.code == "member.trusted" for s in trusted.signals)


def test_prediction_from_stage_order():
    user = UserFacts(id=sf(10), username="x")
    now = int(time.time())
    c = ContactFacts(1, True, 10, {"trust": now - 5 * 86_400, "risk_check": now - 4 * 86_400}, now)
    snap = MemberSnapshot(user=user, now=now, contacts=[c])
    assert predict(snap, score_member(snap), None).escalation == "possible"


def test_structural_audit():
    weak = GuildFacts(member_count=500, verification_level=0, content_filter=0, mfa_level=0, nsfw_level=0,
                      nsfw_channels=2, everyone_mentions=True, admin_humans=9, mods=1, minors_est=40,
                      guard_missing=("Ban Members",))
    failed = {c.id for c in audit_guild(weak) if not c.ok}
    assert {"verification", "content_filter", "automod_presets", "nsfw_channels", "mod_coverage", "admin_sprawl",
            "guard_permissions", "everyone_mentions"} <= failed
    strong = GuildFacts(member_count=100, verification_level=2, content_filter=2, mfa_level=1, nsfw_level=0,
                        automod_triggers=frozenset({AM_PRESET, 3, 5}), mods=3, has_rules_channel=True)
    assert all(c.ok for c in audit_guild(strong))


def test_settings_validation():
    assert clean_settings({"mode": "protect", "alert_channel_id": "123"}) == {"mode": "protect",
                                                                             "alert_channel_id": 123}
    for bad in ({"mode": "nuke"}, {"retention_days": 9999}, {"warn_targets": "yes"}, {"evil": 1},
                {"minor_role_ids": ["x"]}):
        with pytest.raises(ValueError):
            clean_settings(bad)


def test_simulation_produces_a_complete_overview():
    store = Store()
    simulate(store)
    o = Reports(Engine(store)).overview(GID, "en")
    assert set(o) >= {"guild", "health", "summary", "recommendations", "kpis", "series", "top_risks",
                      "recent_alerts", "audit", "permissions_missing"}
    assert len(o["series"]["days"]) == 30 and len(o["series"]["messages"]) == 30
    assert o["top_risks"][0]["level"] == "red"
    assert all("{" not in s for s in o["summary"])  # every placeholder filled


# --- dashboard API ------------------------------------------------------------------------------

def test_signed_links_reject_tampering():
    secret = b"k" * 32
    tok = sign(secret, {"u": "1", "e": time.time() + 60})
    assert verify(secret, tok)["u"] == "1"
    body, _, mac = tok.partition(".")
    assert verify(secret, body[:-2] + "xx." + mac) is None
    assert verify(b"other", tok) is None
    assert verify(secret, sign(secret, {"u": "1", "e": time.time() - 1})) is None


def test_dashboard_api_flow():
    asyncio.run(_api_flow())


async def _api_flow():
    store = Store()
    simulate(store)
    reports = Reports(Engine(store))
    dash = Dashboard(store, reports, base_url="http://localhost", host="", port=0, owner_ids=frozenset({42}))
    async with TestClient(TestServer(dash.app())) as client:
        assert (await client.get("/api/me")).status == 401
        link = dash.link(user_id=7, name="Admin", avatar=None, guild_id=GID, owner=False, lang="en")
        token = link.split("t=", 1)[1]
        r = await client.get(f"/auth?t={token}", allow_redirects=False)
        assert r.status == 302 and r.headers["Location"] == f"/#/g/{GID}"
        assert (await client.get(f"/auth?t={token}", allow_redirects=False)).status == 403  # one-time
        cookie = r.cookies[COOKIE].value
        client.session.cookie_jar.update_cookies({COOKIE: cookie})

        me = await (await client.get("/api/me")).json()
        assert me["owner"] is False and [g["id"] for g in me["guilds"]] == [str(GID)]
        assert (await client.get("/api/guilds/900000000000000002/overview")).status == 403  # not this admin's
        assert (await client.get("/api/owner/overview")).status == 403

        o = await (await client.get(f"/api/guilds/{GID}/overview")).json()
        assert o["guild"]["id"] == str(GID)
        members = await (await client.get(f"/api/guilds/{GID}/members?filter=at_risk")).json()
        top = members["members"][0]
        person = await (await client.get(f"/api/guilds/{GID}/members/{top['id']}")).json()
        assert person["verdict"]["level"] == "red" and person["timeline"]

        assert (await client.post(f"/api/guilds/{GID}/members/{top['id']}", json={"action": "watch"})).status == 403
        r = await client.post(f"/api/guilds/{GID}/members/{top['id']}", json={"action": "watch"},
                              headers={"X-Guildward": "1"})
        assert (await r.json())["member"]["status"] == "watch"

        alerts = await (await client.get(f"/api/guilds/{GID}/alerts")).json()
        aid = alerts["alerts"][0]["id"]
        r = await client.post(f"/api/guilds/{GID}/alerts/{aid}", json={"action": "resolve"},
                              headers={"X-Guildward": "1"})
        assert (await r.json())["alert"]["status"] == "resolved"

        r = await client.put(f"/api/guilds/{GID}/settings", json={"mode": "nuke"}, headers={"X-Guildward": "1"})
        assert r.status == 400
        r = await client.put(f"/api/guilds/{GID}/settings", json={"mode": "observe", "retention_days": 30},
                             headers={"X-Guildward": "1"})
        assert (await r.json())["settings"]["retention_days"] == 30
        assert "Content-Security-Policy" in r.headers

        owner = dash.link(user_id=42, name="Owner", avatar=None, guild_id=None, owner=True, lang="sv")
        r = await client.get(f"/auth?t={owner.split('t=', 1)[1]}", allow_redirects=False)
        client.session.cookie_jar.update_cookies({COOKIE: r.cookies[COOKIE].value})
        ov = await (await client.get("/api/owner/overview")).json()
        assert ov["totals"]["guilds"] == 3 and ov["pocket"]["server"]["green"] > 0
        assert json.dumps(ov)  # serialisable end to end


def test_guard_command_tree():
    asyncio.run(_guard_tree())


async def _guard_tree():
    from guildward.guard import commands
    from guildward.guard.bot import GuardBot, needed_permissions

    bot = GuardBot(Store(), dashboard_url=None)
    commands.setup(bot)
    names = {c.name for c in bot.tree.get_commands(type=None)}
    assert names == {"guard", "Report to mods", "Guard report"}
    guard = bot.tree.get_command("guard")
    assert {c.name for c in guard.commands} == {"setup", "audit", "report", "dashboard", "scan", "watch", "trust",
                                               "clear", "erase"}
    assert guard.default_permissions.manage_guild
    perms = needed_permissions()
    assert perms.moderate_members and perms.ban_members and not perms.administrator
    await bot.close()


def test_scam_broadcast_is_one_untargeted_alert():
    w = World()
    w.join(KID)
    scammer = MemberInfo(sf(1, 9), "nitro_support")
    w.join(scammer)
    outs = []
    for ch in (1, 2, 3):
        w.say(KID, "anyone online", ch=ch)
        outs += w.say(scammer, "free nitro gift for everyone claim here", ch=ch)
    assert [o.kind for o in outs].count("alert") == 1
    a = w.reports.alerts(G, "en")[0]
    assert a["target"] is None and "behave.spam" in {s["code"] for s in a["signals"]}
