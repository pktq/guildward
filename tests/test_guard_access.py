"""Dashboard team access, offline: Sign in with Discord, role-based levels, alert claims and notes, DB migration.

Live role checks run against a fake Guard (the real one needs a Discord connection)."""

import asyncio
import sqlite3
import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import aiohttp
import pytest
from aiohttp.test_utils import TestClient, TestServer

from guildward.guard.engine import Engine
from guildward.guard.reports import Reports
from guildward.guard.simulate import GID, simulate
from guildward.guard.store import Store, clean_settings, role_access
from guildward.guard.web import COOKIE, OAUTH_COOKIE, Dashboard, safe_next, sign

OWNER, VIEW, ACT, ADMIN, NOBODY = 42, 7, 8, 9, 10
X = {"X-Guildward": "1"}


class FakeGuard:
    """Just what the dashboard asks of GuardBot; `levels` plays the members' current roles."""

    application_id = 555

    def __init__(self, store: Store, levels: dict[int, str | None]) -> None:
        self.store, self.levels, self.acted = store, levels, []

    def get_guild(self, gid):
        if gid != GID:
            return None
        return SimpleNamespace(get_member=lambda uid: SimpleNamespace(id=uid) if uid in self.levels else None)

    def access(self, gid, uid):
        return self.levels.get(uid)

    def guild_meta(self, gid):
        return {"missing": [], "alert_channel": None, "channels": [], "roles": [{"id": "601", "name": "Mods"}]}

    async def act(self, gid, uid, action, *, by_id, by_name, alert_id=None, actor=None, note=None, **_):
        self.acted.append((action, actor.id if actor else None, note))
        if alert_id and action in ("resolve", "false_positive"):
            self.store.resolve_alert(alert_id, status="false_positive" if action == "false_positive" else "resolved",
                                     by=by_id, by_name=by_name, action=action, note=note)
        return True, "ok"

    async def claim(self, aid, *, by_id, by_name, action, force=False):
        code = self.store.claim_alert(aid, by=by_id, by_name=by_name, action=action, force=force)
        return code in ("claimed", "unclaimed"), code

    async def apply_fix(self, gid, fix):
        return True, "fixed"


def _world(secret: str = "s3cret"):
    store = Store()
    simulate(store)
    guard = FakeGuard(store, {VIEW: "view", ACT: "act", ADMIN: "admin"})
    dash = Dashboard(store, Reports(Engine(store)), base_url="http://localhost", host="", port=0,
                     owner_ids=frozenset({OWNER}), guard=guard, client_secret=secret)
    return store, guard, dash


def _client(dash: Dashboard) -> TestClient:
    return TestClient(TestServer(dash.app()), cookie_jar=aiohttp.DummyCookieJar())


async def _signin(client: TestClient, dash: Dashboard, uid: int, guild: int | None = GID) -> dict[str, str]:
    link = dash.link(user_id=uid, name=f"user{uid}", avatar=None, guild_id=guild, owner=uid == OWNER, lang="en")
    r = await client.get(f"/auth?t={link.split('t=', 1)[1]}", allow_redirects=False)
    return {"Cookie": f"{COOKIE}={r.cookies[COOKIE].value}"}


# --- levels ---------------------------------------------------------------------------------------

def test_role_access_and_settings_validation():
    roles = {"601": "act", "602": "view"}
    assert role_access(admin=True, role_ids=[], dashboard_roles={}) == "admin"
    assert role_access(admin=False, role_ids=[602, 601], dashboard_roles=roles) == "act"  # highest role wins
    assert role_access(admin=False, role_ids=[602], dashboard_roles=roles) == "view"
    assert role_access(admin=False, role_ids=[700], dashboard_roles=roles) is None
    assert clean_settings({"dashboard_roles": {601: "act"}}) == {"dashboard_roles": {"601": "act"}}
    for bad in ({"dashboard_roles": {"601": "admin"}}, {"dashboard_roles": {"x": "view"}},
                {"dashboard_roles": ["601"]}, {"dashboard_roles": {str(i): "view" for i in range(51)}}):
        with pytest.raises(ValueError):
            clean_settings(bad)


def test_guardbot_access_follows_current_roles():
    asyncio.run(_guardbot_access())


async def _guardbot_access():
    from guildward.guard.bot import GuardBot

    store = Store()
    store.upsert_guild(1, name="g", icon=None, owner_id=99, member_count=3)
    store.update_settings(1, {"dashboard_roles": {"601": "view"}})
    bot = GuardBot(store, dashboard_url=None)
    mod = SimpleNamespace(id=5, roles=[SimpleNamespace(id=601)], guild_permissions=SimpleNamespace(manage_guild=False))
    owner = SimpleNamespace(id=99, roles=[], guild_permissions=SimpleNamespace(manage_guild=False))
    members = {5: mod, 99: owner}
    bot.get_guild = lambda gid: SimpleNamespace(owner_id=99, get_member=members.get) if gid == 1 else None
    assert bot.access(1, 5) == "view" and bot.access(1, 99) == "admin" and bot.access(1, 6) is None
    mod.roles = []  # role taken away: access gone on the next request
    assert bot.access(1, 5) is None
    mod.guild_permissions.manage_guild = True
    assert bot.access(1, 5) == "admin"
    await bot.close()


def test_dashboard_enforces_levels_server_side():
    asyncio.run(_levels())


async def _levels():
    store, guard, dash = _world()
    aid = store.q("SELECT id FROM alerts WHERE guild_id=? AND status='open' ORDER BY id LIMIT 1", GID)[0]["id"]
    uid = store.q("SELECT user_id FROM members WHERE guild_id=? LIMIT 1", GID)[0]["user_id"]
    async with _client(dash) as c:
        view, act, admin = [await _signin(c, dash, u) for u in (VIEW, ACT, ADMIN)]
        nobody = await _signin(c, dash, NOBODY)
        me = await (await c.get("/api/me", headers=view)).json()
        assert [(g["id"], g["level"]) for g in me["guilds"]] == [(str(GID), "view")]
        assert (await (await c.get("/api/me", headers=nobody)).json())["guilds"] == []
        assert (await c.get(f"/api/guilds/{GID}/overview", headers=nobody)).status == 403

        # view: read everything, change nothing
        assert (await c.get(f"/api/guilds/{GID}/overview", headers=view)).status == 200
        assert (await c.get(f"/api/guilds/{GID}/settings", headers=view)).status == 200
        for method, path, body in (("POST", f"alerts/{aid}", {"action": "resolve"}),
                                   ("POST", f"alerts/{aid}", {"action": "claim"}),
                                   ("POST", f"members/{uid}", {"action": "watch"}),
                                   ("PUT", "settings", {"mode": "protect"}), ("POST", "fix", {"fix": "verification"})):
            r = await c.request(method, f"/api/guilds/{GID}/{path}", json=body, headers={**view, **X})
            assert r.status == 403, (method, path)

        # act: alert and member actions (as the signed-in member, so Guard checks their Discord permissions)
        r = await c.post(f"/api/guilds/{GID}/alerts/{aid}", json={"action": "claim"}, headers={**act, **X})
        assert (await r.json())["alert"]["assigned"] == {"id": str(ACT), "name": f"user{ACT}", "avatar": None}
        r = await c.post(f"/api/guilds/{GID}/members/{uid}", json={"action": "watch"}, headers={**act, **X})
        assert r.status == 200 and guard.acted[-1] == ("watch", ACT, None)
        for method, path, body in (("PUT", "settings", {"dashboard_roles": {"601": "act"}}),
                                   ("POST", "fix", {"fix": "verification"})):
            assert (await c.request(method, f"/api/guilds/{GID}/{path}", json=body, headers={**act, **X})).status == 403

        # admin: settings, fixes and who gets access; roles must exist in the server
        r = await c.put(f"/api/guilds/{GID}/settings", json={"dashboard_roles": {"601": "act"}}, headers={**admin, **X})
        assert (await r.json())["settings"]["dashboard_roles"] == {"601": "act"}
        r = await c.put(f"/api/guilds/{GID}/settings", json={"dashboard_roles": {"999": "view"}},
                        headers={**admin, **X})
        assert r.status == 400
        r = await c.post(f"/api/guilds/{GID}/fix", json={"fix": "verification"}, headers={**admin, **X})
        assert r.status == 200
        # admins can release someone else's claim
        r = await c.post(f"/api/guilds/{GID}/alerts/{aid}", json={"action": "unclaim"}, headers={**admin, **X})
        assert r.status == 200 and (await r.json())["alert"]["assigned"] is None

        # the role is taken away: the same session loses access on its next request
        guard.levels[VIEW] = None
        assert (await c.get(f"/api/guilds/{GID}/overview", headers=view)).status == 403
        assert (await (await c.get("/api/me", headers=view)).json())["guilds"] == []

        # owner keeps the owner dashboard and every server
        owner = await _signin(c, dash, OWNER, None)
        me = await (await c.get("/api/me", headers=owner)).json()
        assert me["owner"] and len(me["guilds"]) == 3 and {g["level"] for g in me["guilds"]} == {"admin"}


# --- claims and notes -----------------------------------------------------------------------------

def test_claims_and_notes():
    asyncio.run(_claims())


async def _claims():
    store = Store()
    simulate(store)
    aid = store.q("SELECT id FROM alerts WHERE guild_id=? AND status='open' ORDER BY id LIMIT 1", GID)[0]["id"]
    assert store.claim_alert(aid, by=1, by_name="Ana", action="claim") == "claimed"
    assert store.claim_alert(aid, by=2, by_name="Bo", action="claim") == "taken"
    assert store.claim_alert(aid, by=2, by_name="Bo", action="unclaim") == "not_yours"
    assert store.claim_alert(aid, by=1, by_name="Ana", action="toggle") == "unclaimed"  # same mod again: let go
    assert store.claim_alert(aid, by=2, by_name="Bo", action="toggle") == "claimed"

    # dashboard-only mode (no live bot): a signed link's server counts as admin, as before
    dash = Dashboard(store, Reports(Engine(store)), base_url="http://localhost", host="", port=0,
                     owner_ids=frozenset())
    async with _client(dash) as c:
        h = {**(await _signin(c, dash, 3)), **X}
        r = await c.post(f"/api/guilds/{GID}/alerts/{aid}", json={"action": "resolve", "note": "x" * 501}, headers=h)
        assert r.status == 400
        r = await c.post(f"/api/guilds/{GID}/alerts/{aid}", json={"action": "resolve", "note": "  Talked to them.  "},
                         headers=h)
        a = (await r.json())["alert"]
        assert a["status"] == "resolved" and a["note"] == "Talked to them." and a["assigned"]["name"] == "Bo"
        r = await c.post(f"/api/guilds/{GID}/alerts/{aid}", json={"action": "claim"}, headers=h)
        assert r.status == 409  # closed
        uid = store.alert(aid)["user_id"]
        person = await (await c.get(f"/api/guilds/{GID}/members/{uid}", headers=h)).json()
        notes = [e for e in person["timeline"] if e["kind"] == "note"]
        assert notes and "Talked to them." in notes[0]["text"] and f"#{aid}" in notes[0]["text"]


def test_old_database_gets_alert_columns(tmp_path):
    db = tmp_path / "old.db"
    old = sqlite3.connect(db)
    old.execute("""CREATE TABLE alerts(
      id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, kind TEXT NOT NULL, level TEXT NOT NULL,
      score INTEGER NOT NULL,
      user_id INTEGER, target_id INTEGER, title TEXT NOT NULL, params TEXT NOT NULL DEFAULT '{}',
      signals TEXT NOT NULL DEFAULT '[]', channel_id INTEGER, message_id INTEGER, post_channel_id INTEGER,
      post_id INTEGER, status TEXT NOT NULL DEFAULT 'open', created_at INTEGER NOT NULL,
      resolved_by INTEGER, resolved_by_name TEXT, resolved_at INTEGER, action TEXT)""")
    old.execute("INSERT INTO alerts(guild_id,kind,level,score,title,created_at) VALUES(1,'message','red',80,'t',0)")
    old.commit()
    old.close()
    for _ in range(2):  # opening twice must not try to add the columns again
        store = Store(db)
        cols = {r["name"] for r in store.q("PRAGMA table_info(alerts)")}
        assert {"assigned_to", "assigned_name", "note"} <= cols
        assert store.alert(1)["note"] is None
        store.close()
    store = Store(db)
    assert store.claim_alert(1, by=5, by_name="Mod", action="claim") == "claimed"
    store.close()


def test_alert_card_shows_claim_and_note():
    asyncio.run(_card())


async def _card():
    from guildward.guard import render
    from guildward.guard.commands import alert_view

    store = Store()
    simulate(store)
    reports = Reports(Engine(store))
    aid = store.q("SELECT id FROM alerts WHERE guild_id=? AND status='open' AND user_id IS NOT NULL LIMIT 1",
                  GID)[0]["id"]
    labels = lambda a: {c.item.custom_id.rsplit(":", 1)[1]: c.item.label for c in alert_view(a, "en").children}  # noqa: E731
    a = reports.alert_dict(store.alert(aid), "en")
    assert labels(a)["claim"] == "I'm on it"
    store.claim_alert(aid, by=5, by_name="Mod Ana", action="claim")
    a = reports.alert_dict(store.alert(aid), "en")
    assert labels(a)["claim"] == "Mod Ana is on it"
    fields = {f.name: f.value for f in render.alert_embed(a, "en", dashboard_url=None, quote=False).fields}
    assert fields["Handled by"] == "<@5>"
    store.resolve_alert(aid, status="resolved", by=5, by_name="Mod Ana", action="resolve", note="Spoke to the parent.")
    a = reports.alert_dict(store.alert(aid), "en")
    fields = {f.name: f.value for f in render.alert_embed(a, "en", dashboard_url=None, quote=False).fields}
    assert fields["Note"] == "Spoke to the parent." and "Handled by" not in fields


# --- Sign in with Discord -------------------------------------------------------------------------

def test_safe_next_blocks_open_redirects():
    assert safe_next("/dashboard") == "/dashboard"
    assert safe_next(f"/dashboard/g/{GID}/alerts?status=all") == f"/dashboard/g/{GID}/alerts?status=all"
    for bad in ("//evil.com", "https://evil.com", "/dashboard//evil.com", "/dashboardx", "/api/me",
                "/dashboard/../api", "/dashboard\\@evil.com", "/dashboard/<script>", None, 5,
                "/dashboard/" + "a" * 300):
        assert safe_next(bad) is None, bad


def test_discord_sign_in_flow():
    asyncio.run(_oauth())


async def _oauth():
    _, _, dash = _world()
    seen: list[str] = []

    async def fake_user(code):
        seen.append(code)
        return {"id": str(fake_user.uid), "username": "mod", "global_name": "Mod Ana", "avatar": "a" * 32,
                "locale": "sv-SE"}

    fake_user.uid = ACT
    dash._discord_user = fake_user

    async def start(next_path: str | None = None):
        r = await c.get("/auth/discord", params={"next": next_path} if next_path else None, allow_redirects=False)
        assert r.status == 302
        loc = urlparse(r.headers["Location"])
        q = {k: v[0] for k, v in parse_qs(loc.query).items()}
        assert loc.netloc == "discord.com" and q["scope"] == "identify" and q["client_id"] == "555"
        assert q["redirect_uri"] == "http://localhost/auth/discord/callback"
        cookie = r.cookies[OAUTH_COOKIE]
        assert cookie["httponly"] and cookie["samesite"] == "Lax" and cookie["path"] == "/auth/discord"
        return q["state"], {"Cookie": f"{OAUTH_COOKIE}={cookie.value}"}

    async with _client(dash) as c:
        assert (await (await c.get("/api/public/auth")).json())["discord"] is True

        state, bound = await start(f"/dashboard/g/{GID}/alerts")
        cb = f"/auth/discord/callback?code=abc&state={state}"
        assert (await c.get(cb, allow_redirects=False)).status == 403  # not the browser that started it
        assert (await c.get(cb, headers={"Cookie": f"{OAUTH_COOKIE}=forged"}, allow_redirects=False)).status == 403
        r = await c.get(cb, headers=bound, allow_redirects=False)
        assert r.status == 302 and r.headers["Location"] == f"/dashboard/g/{GID}/alerts" and seen == ["abc"]
        sess = r.cookies[COOKIE]
        assert sess["httponly"] and sess["samesite"] == "Strict" and "abc" not in r.headers["Location"]
        assert (await c.get(cb, headers=bound, allow_redirects=False)).status == 403  # single use
        me = await (await c.get("/api/me", headers={"Cookie": f"{COOKIE}={sess.value}"})).json()
        assert me["user"]["name"] == "Mod Ana" and me["lang"] == "sv" and me["owner"] is False
        assert me["user"]["avatar"].startswith(f"https://cdn.discordapp.com/avatars/{ACT}/")
        assert [(g["id"], g["level"]) for g in me["guilds"]] == [(str(GID), "act")]

        # no (or a bad) next: the first server they can see; owners land on the owner dashboard
        for uid, nxt, dest in ((ACT, "https://evil.com", f"/dashboard/g/{GID}"), (NOBODY, None, "/dashboard"),
                               (OWNER, None, "/dashboard/owner")):
            fake_user.uid = uid
            state, bound = await start(nxt)
            r = await c.get(f"/auth/discord/callback?code=c&state={state}", headers=bound, allow_redirects=False)
            assert r.headers["Location"] == dest, uid

        state, bound = await start()  # Cancel on Discord's screen
        r = await c.get(f"/auth/discord/callback?error=access_denied&state={state}", headers=bound,
                        allow_redirects=False)
        assert r.status == 302 and r.headers["Location"] == "/dashboard" and COOKIE not in r.cookies

        # the two kinds of signed token are not interchangeable
        state, bound = await start()
        assert (await c.get(f"/auth?t={state}", allow_redirects=False)).status == 403
        link = dash.link(user_id=ACT, name="x", avatar=None, guild_id=GID, owner=False, lang="en").split("t=", 1)[1]
        r = await c.get(f"/auth/discord/callback?code=c&state={link}", headers=bound, allow_redirects=False)
        assert r.status == 403
        forged = sign(b"wrong", {"t": "login", "p": None, "b": "x", "e": int(time.time()) + 60, "x": "1"})
        r = await c.get(f"/auth/discord/callback?code=c&state={forged}", headers=bound, allow_redirects=False)
        assert r.status == 403

    # no client secret: the button is hidden and the endpoints say why
    _, _, off = _world(secret="")
    async with _client(off) as c:
        assert (await (await c.get("/api/public/auth")).json())["discord"] is False
        assert (await c.get("/auth/discord", allow_redirects=False)).status == 503
