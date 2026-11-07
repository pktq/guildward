"""A simulated kids' server, run through the real engine, so the dashboard can be tried (and tested)
without a Discord token. `uv run guildward simulate` then `uv run guildward dashboard`.

Every member, message and alert here is synthetic. Nothing is stored about message text, just like live.
"""

from __future__ import annotations

import random
import time

from guildward.core.snowflake import DISCORD_EPOCH_MS
from guildward.guard.engine import Engine, JoinEvent, MemberInfo, MessageEvent
from guildward.guard.store import Store, now

GID = 900_000_000_000_000_001
GUILDS = ((GID, "Pixel Pals MC (demo)", 64), (900_000_000_000_000_002, "Study Hall SE (demo)", 30),
          (900_000_000_000_000_003, "Speedrun Squad (demo)", 22))
CHANNELS = {1: "general", 2: "minecraft", 3: "memes", 4: "voice-chat-text"}
DAY = 86_400

_KID_LINES = ["anyone on the server rn", "gg that was so fun", "im building a castle", "who wants to play bedwars",
              "lol", "my mom says i have to do homework first", "can someone help me with redstone",
              "that creeper blew up my house", "brb dinner", "check out my new skin"]
_ADULT_LINES = ["Server restart in 10 minutes", "Please keep #general on topic", "nice build!",
                "reminder: no sharing personal info here", "welcome to the server"]


def _sf(days_ago: float, n: int) -> int:
    return ((int((time.time() - days_ago * DAY) * 1000) - DISCORD_EPOCH_MS) << 22) + n


def simulate(store: Store, seed: int = 7) -> str:
    rnd = random.Random(seed)
    engine = Engine(store)
    for gid, name, members in GUILDS:
        store.upsert_guild(gid, name=name, icon=None, owner_id=_sf(900, 1), member_count=members)
    store.update_settings(GID, {"mode": "protect", "alert_channel_id": "4", "minor_role_ids": []})
    store.update_settings(GUILDS[1][0], {"mode": "observe"})
    store.save_audit(GID, {"facts": {
        "member_count": 64, "verification_level": 1, "content_filter": 1, "mfa_level": 0, "nsfw_level": 0,
        "automod_triggers": [3], "nsfw_channels": 0, "everyone_mentions": True, "admin_humans": 2, "admin_bots": 1,
        "mods": 2, "has_rules_channel": True, "guard_missing": ["Manage Roles"], "minors_est": 0}})
    for gid, _, _ in GUILDS[1:]:
        store.save_audit(gid, {"facts": {
            "member_count": 30, "verification_level": 2, "content_filter": 2, "mfa_level": 1, "nsfw_level": 0,
            "automod_triggers": [3, 4, 5], "nsfw_channels": 0, "everyone_mentions": False, "admin_humans": 1,
            "admin_bots": 0, "mods": 3, "has_rules_channel": True, "guard_missing": [], "minors_est": 0}})

    t0 = now() - 29 * DAY
    kids = [MemberInfo(_sf(rnd.randint(200, 1500), i), f"kid_{i}", rnd.choice(["Mia", "Leo", "Ella", "Noah", "Alva",
                                                                              "Liam", "Saga", "Hugo"]) + str(i),
                       has_avatar=rnd.random() > 0.3, role_age="minor" if i % 3 == 0 else None)
            for i in range(1, 41)]
    adults = [MemberInfo(_sf(rnd.randint(800, 3000), 100 + i), f"mod_{i}", f"Mod {name}", has_avatar=True,
                         role_age="adult") for i, name in enumerate(["Sam", "Kim", "Alex"])]
    groomer = MemberInfo(_sf(3, 200), "chill_gamer_19", "ChillGamer", has_avatar=False)
    reported = MemberInfo(_sf(60, 201), "robux_rich", "RobuxRich", has_avatar=True)
    scammer = MemberInfo(_sf(1, 202), "discord_nitro_support", "Nitro Support", has_avatar=False)
    teen_peer = kids[4]

    for i, m in enumerate(kids + adults):
        engine.on_join(JoinEvent(GID, m, t0 - rnd.randint(1, 400) * DAY if i % 4 else t0 + i * 3600))
    store.x("UPDATE members SET joined_at=? WHERE guild_id=? AND joined_at>?", t0 - 30 * DAY, GID, now())

    mid = [10_000]

    def say(m: MemberInfo, text: str, at: int, *, ch: int = 1, reply: int | None = None, backfill: bool = True) -> None:
        mid[0] += 1
        out = engine.on_message(MessageEvent(GID, ch, mid[0], m, text, at, reply_to=reply,
                                             channel_name=CHANNELS[ch], backfill=backfill))
        for o in out:  # resolve auto actions as the live bot would record them
            if o.kind in ("timeout", "quarantine"):
                engine.on_mod_action(GID, o.user_id, o.kind, by=None, by_name="Guard", source="guard")

    # Four weeks of ordinary chat; a few kids say their age.
    for day in range(29):
        for _ in range(rnd.randint(60, 140)):
            who = rnd.choice(kids + adults[:1])
            line = rnd.choice(_ADULT_LINES if who in adults else _KID_LINES)
            say(who, line, t0 + day * DAY + rnd.randint(0, DAY - 1), ch=rnd.choice([1, 2, 3]))
    for k in kids[:12]:
        say(k, f"im {rnd.randint(10, 15)} lol", t0 + rnd.randint(0, 20) * DAY)
    say(adults[0], "I'm 34, I run the server", t0 + 2 * DAY)

    # Two kids being normal kids with each other: age questions between minors stay low.
    base = now() - 6 * DAY
    say(kids[1], "how old are you?", base, reply=kids[2].id)
    say(kids[2], "im 12 wbu", base + 30)
    say(kids[1], "add me on snapchat", base + 60, reply=kids[2].id)

    # The groomer: joins 3 days ago, works through several kids, escalates with one.
    j = now() - 3 * DAY
    engine.on_join(JoinEvent(GID, groomer, j, invite_code="mc-kids", inviter_id=None))
    say(groomer, "hey whats up everyone", j + 600)
    say(groomer, "I'm 19 btw", j + 900)
    for k in kids[:4]:
        say(groomer, "how old are you?", j + 3600 + kids.index(k) * 400, reply=k.id)
    say(groomer, "you're really mature for your age", j + DAY, reply=teen_peer.id)
    say(groomer, "how old are you?", j + DAY + 300, reply=teen_peer.id, backfill=False)
    say(groomer, "dont tell your parents we talk ok, our secret", j + 2 * DAY, reply=teen_peer.id, backfill=False)
    say(groomer, "add me on snapchat its easier", j + 2 * DAY + 200, reply=teen_peer.id, backfill=False)
    say(groomer, "check ur dms", j + 2 * DAY + 400, reply=kids[3].id, backfill=False)
    say(groomer, "send me a pic of you", now() - 3600, reply=teen_peer.id, backfill=False)

    # Someone offering Robux, reported by two kids.
    r = now() - 5 * DAY
    engine.on_join(JoinEvent(GID, reported, now() - 40 * DAY))
    say(reported, "i can give you free robux if you add me", r, reply=kids[6].id, backfill=False)
    for k in kids[6:8]:
        engine.on_report(GID, k, reported, channel_id=1, message_id=mid[0], content=None, channel_name="general")

    # A scam burst + a raid.
    raid_at = now() - 2 * DAY
    for n in range(12):
        engine.on_join(JoinEvent(GID, MemberInfo(_sf(0.5, 300 + n), f"x{n}raider", None), raid_at + n * 4))
    engine.on_join(JoinEvent(GID, scammer, raid_at + 60))
    for ch in (1, 2, 3):
        say(scammer, "free nitro gift for everyone claim here", raid_at + 70 + ch, ch=ch, backfill=False)

    # Moderators handled some alerts (response times), marked one false alarm.
    rows = store.q("SELECT id, created_at FROM alerts WHERE guild_id=? ORDER BY id", GID)
    for i, row in enumerate(rows):
        store.x("UPDATE alerts SET created_at=? WHERE id=?", min(row["created_at"], now() - (len(rows) - i) * 5400),
                row["id"])
    for row in rows[:len(rows) // 2]:
        store.resolve_alert(row["id"], status="resolved", by=adults[0].id, by_name="Mod Sam", action="timeout")
        store.x("UPDATE alerts SET resolved_at=created_at+? WHERE id=?", rnd.randint(4, 40) * 60, row["id"])
    if rows:
        store.resolve_alert(rows[0]["id"], status="false_positive", by=adults[1].id, by_name="Mod Kim",
                            action="false_positive")

    # A network flag from another Guard server, and pocket-app usage counts.
    store.flag_network(reported.id, GUILDS[1][0], "child_safety")
    for d in range(30):
        for kind in ("server", "person", "message"):
            for level, n in (("green", rnd.randint(2, 9)), ("yellow", rnd.randint(0, 3)), ("red", rnd.randint(0, 1))):
                store.bump(0, f"pocket.{kind}.{level}", n, at=now() - d * DAY)
    for gid, _, _ in GUILDS[1:]:
        for d in range(30):
            store.bump(gid, "messages", rnd.randint(40, 200), at=now() - d * DAY)
            store.bump(gid, "joins", rnd.randint(0, 2), at=now() - d * DAY)
    for uid in {r["user_id"] for r in store.q("SELECT user_id FROM members WHERE guild_id=?", GID)}:
        engine.rescore(GID, uid)
    alerts = store.val("SELECT COUNT(*) FROM alerts WHERE guild_id=?", GID)
    members = store.val("SELECT COUNT(*) FROM members WHERE guild_id=?", GID)
    return f"simulated {len(GUILDS)} servers; demo server has {members} members and {alerts} alerts (db: {store.path})"
