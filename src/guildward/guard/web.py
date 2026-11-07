"""Dashboard server: the JSON API from docs/GUARD_API.md plus the static SPA in web/dashboard.

Runs on aiohttp (already a discord.py dependency) in the same event loop as the bots, so API calls
can act through the live Guard client. Sign-in is a one-time link the bot hands an admin inside
Discord (`/guard dashboard`), so no OAuth secret is needed and Discord itself vouches for the admin.
The bot owner gets one from `uv run guildward owner-link`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aiohttp import web

from guildward import __version__
from guildward.core.i18n import t
from guildward.guard.store import Store, clean_settings
from guildward.intel.rules import is_private

if TYPE_CHECKING:
    from guildward.guard.bot import GuardBot
    from guildward.guard.reports import Reports

log = logging.getLogger(__name__)

STATIC = Path(__file__).resolve().parents[3] / "web" / "dashboard"
COOKIE = "gw_session"
LINK_TTL = 600
SESSION_TTL = 12 * 3600
SESSION = web.RequestKey("session", object)
LANG = web.RequestKey("lang", str)
GUILDS = web.RequestKey("guilds", set)
OWNER = web.RequestKey("owner", bool)
GID = web.RequestKey("gid", int)
MEMBER_ACTIONS = {"watch", "trust", "clear", "timeout", "kick", "ban"}
ALERT_ACTIONS = {"resolve", "false_positive", "timeout", "kick", "ban", "delete", "watch"}
CSP = ("default-src 'self'; img-src 'self' https://cdn.discordapp.com data:; style-src 'self' 'unsafe-inline'; "
       "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def secret_for(store: Store) -> bytes:
    env = os.environ.get("DASHBOARD_SECRET", "").strip()
    if env:
        return env.encode()
    stored = store.meta("dashboard_secret")
    if stored is None:
        stored = secrets.token_hex(32)
        store.set_meta("dashboard_secret", stored)
    return stored.encode()


def sign(secret: bytes, payload: dict[str, Any]) -> str:
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return body + "." + _b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())


def verify(secret: bytes, token: str) -> dict[str, Any] | None:
    body, _, mac = token.partition(".")
    if not body or not mac:
        return None
    good = _b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(good, mac):
        return None
    try:
        payload = json.loads(_unb64(body))
    except ValueError:
        return None
    return payload if payload.get("e", 0) > time.time() else None


class Dashboard:
    def __init__(self, store: Store, reports: Reports, *, base_url: str, host: str, port: int,
                 owner_ids: frozenset[int], guard: GuardBot | None = None, pocket: Any = None) -> None:
        self.store, self.reports = store, reports
        self.base_url = base_url.rstrip("/")
        self.host, self.port = host, port
        self.owner_ids = owner_ids
        self.guard, self.pocket = guard, pocket
        self.secret = secret_for(store)
        self.started = time.time()
        self._runner: web.AppRunner | None = None
        if guard is not None:
            guard.sign_link = self.sign_link

    # --- links ------------------------------------------------------------------------------
    def link(self, *, user_id: int, name: str, avatar: str | None, guild_id: int | None, owner: bool, lang: str,
             path: str | None = None) -> str:
        payload = {"u": str(user_id), "n": name[:100], "a": avatar, "g": str(guild_id) if guild_id else None,
                   "o": owner, "l": lang, "p": path, "e": int(time.time()) + LINK_TTL, "x": secrets.token_hex(8)}
        return f"{self.base_url}/auth?t={sign(self.secret, payload)}"

    def sign_link(self, user: Any, guild_id: int, lang: str, path: str | None = None) -> str:
        avatar = user.display_avatar.url if getattr(user, "avatar", None) else None
        return self.link(user_id=user.id, name=getattr(user, "display_name", user.name), avatar=avatar,
                         guild_id=guild_id, owner=user.id in self.owner_ids, lang=lang, path=path)

    # --- app --------------------------------------------------------------------------------
    def app(self) -> web.Application:
        app = web.Application(middlewares=[self._headers, self._auth], client_max_size=64 * 1024)
        r = app.router
        r.add_get("/auth", self.auth)
        r.add_post("/api/logout", self.logout)
        r.add_get("/api/me", self.me)
        r.add_get("/api/guilds/{gid}/overview", self.overview)
        r.add_post("/api/guilds/{gid}/fix", self.fix)
        r.add_get("/api/guilds/{gid}/alerts", self.alerts)
        r.add_post("/api/guilds/{gid}/alerts/{aid}", self.alert_action)
        r.add_get("/api/guilds/{gid}/members", self.members)
        r.add_get("/api/guilds/{gid}/members/{uid}", self.member)
        r.add_post("/api/guilds/{gid}/members/{uid}", self.member_action)
        r.add_get("/api/guilds/{gid}/settings", self.get_settings)
        r.add_put("/api/guilds/{gid}/settings", self.put_settings)
        r.add_get("/api/owner/overview", self.owner_overview)
        r.add_post("/api/owner/network/{uid}", self.owner_network)
        r.add_post("/api/owner/guilds/{gid}", self.owner_guild)
        r.add_get("/", self.index)
        if STATIC.is_dir():
            r.add_static("/", STATIC, show_index=False, follow_symlinks=False)
        return app

    async def start(self) -> None:
        self._runner = web.AppRunner(self.app(), access_log=None)
        await self._runner.setup()
        await web.TCPSite(self._runner, self.host, self.port).start()
        log.info("dashboard on %s (listening %s:%d)", self.base_url, self.host, self.port)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()

    # --- middleware -------------------------------------------------------------------------
    @web.middleware
    async def _headers(self, request: web.Request, handler: Any) -> web.StreamResponse:
        try:
            resp = await handler(request)
        except web.HTTPException as e:
            resp = e
        resp.headers.setdefault("Content-Security-Policy", CSP)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        if request.path.startswith("/api/"):
            resp.headers.setdefault("Cache-Control", "no-store")
        if isinstance(resp, web.HTTPException):
            raise resp
        return resp

    @web.middleware
    async def _auth(self, request: web.Request, handler: Any) -> web.StreamResponse:
        if not request.path.startswith("/api/"):
            return await handler(request)
        if request.method in ("POST", "PUT", "DELETE") and request.headers.get("X-Guildward") != "1":
            return self._err(403, "Missing X-Guildward header.")
        token = request.cookies.get(COOKIE)
        sess = self.store.session(_hash(token)) if token else None
        if sess is None:
            return self._err(401, "Sign in again: run /guard dashboard in your server.")
        request[SESSION] = sess
        request[LANG] = sess["lang"] if sess["lang"] in ("en", "sv") else "en"
        request[GUILDS] = {int(g) for g in json.loads(sess["guilds"] or "[]")}
        request[OWNER] = bool(sess["owner"])
        if "gid" in request.match_info and request.path.startswith("/api/guilds/"):
            gid = self._int(request.match_info["gid"])
            if gid is None or not self._may_see(request, gid):
                return self._err(403, "No access to this server.")
            request[GID] = gid
        if request.path.startswith("/api/owner/") and not request[OWNER]:
            return self._err(403, "Owner only.")
        return await handler(request)

    def _may_see(self, request: web.Request, gid: int) -> bool:
        if request[OWNER]:
            return self.store.guild(gid) is not None
        if gid not in request[GUILDS]:
            return False
        # Lost Manage Server since signing in? Then the session no longer covers this server.
        if self.guard is not None and self.guard.get_guild(gid) is not None:
            return self.guard.is_admin(gid, request[SESSION]["user_id"])
        return True

    @staticmethod
    def _int(v: str) -> int | None:
        return int(v) if v.isdigit() and len(v) < 21 else None

    @staticmethod
    def _err(status: int, text: str) -> web.Response:
        return web.json_response({"ok": False, "error": text}, status=status)

    @staticmethod
    async def _body(request: web.Request) -> dict[str, Any]:
        try:
            body = await request.json()
        except ValueError:
            raise web.HTTPBadRequest(text='{"ok":false,"error":"Bad JSON."}', content_type="application/json") from None
        if not isinstance(body, dict):
            raise web.HTTPBadRequest(text='{"ok":false,"error":"Bad JSON."}', content_type="application/json")
        return body

    def _who(self, request: web.Request) -> tuple[int, str]:
        s = request[SESSION]
        return s["user_id"], s["name"]

    # --- auth -------------------------------------------------------------------------------
    async def index(self, request: web.Request) -> web.StreamResponse:
        index = STATIC / "index.html"
        if not index.is_file():
            return web.Response(text="Dashboard files not found (web/dashboard).", status=404)
        return web.FileResponse(index)

    async def auth(self, request: web.Request) -> web.StreamResponse:
        payload = verify(self.secret, request.query.get("t", ""))
        if payload is None or not self.store.use_nonce(payload["x"], payload["e"]):
            return web.Response(status=403, content_type="text/html", text=(
                "<!doctype html><meta charset=utf-8><title>Guildward</title><body style='font:16px system-ui;"
                "padding:3rem;background:#0d1117;color:#e6edf3'><h1>This sign-in link has expired</h1>"
                "<p>Links work once, for 10 minutes. Run <code>/guard dashboard</code> in your server for a new one."))
        uid = int(payload["u"])
        guilds = {payload["g"]} if payload.get("g") else set()
        old = request.cookies.get(COOKIE)
        prev = self.store.session(_hash(old)) if old else None
        if prev is not None and prev["user_id"] == uid:
            guilds |= set(json.loads(prev["guilds"] or "[]"))
            self.store.drop_session(_hash(old))
        token = secrets.token_urlsafe(32)
        self.store.add_session(_hash(token), user_id=uid, name=payload["n"], avatar=payload.get("a"),
                               guilds=sorted(guilds), owner=bool(payload.get("o")), lang=payload.get("l") or "en",
                               ttl=SESSION_TTL)
        dest = payload.get("p") or (f"/g/{payload['g']}" if payload.get("g") else "/owner")
        resp = web.HTTPFound(f"/#{dest}")
        resp.set_cookie(COOKIE, token, max_age=SESSION_TTL, httponly=True, samesite="Strict",
                        secure=self.base_url.startswith("https://"), path="/")
        raise resp

    async def logout(self, request: web.Request) -> web.Response:
        token = request.cookies.get(COOKIE)
        if token:
            self.store.drop_session(_hash(token))
        resp = web.json_response({"ok": True})
        resp.del_cookie(COOKIE, path="/")
        return resp

    async def me(self, request: web.Request) -> web.Response:
        s = request[SESSION]
        ids = [g["id"] for g in self.store.active_guilds()] if request[OWNER] else sorted(request[GUILDS])
        guilds = []
        for gid in ids:
            g = self.store.guild(gid)
            if g is not None and (request[OWNER] or self._may_see(request, gid)):
                guilds.append({"id": str(gid), "name": g["name"], "icon": g["icon"]})
        return web.json_response({"user": {"id": str(s["user_id"]), "name": s["name"], "avatar": s["avatar"]},
                                  "owner": request[OWNER], "lang": request[LANG], "guilds": guilds})

    # --- server admin -----------------------------------------------------------------------
    def _meta(self, gid: int) -> dict[str, Any]:
        meta = self.guard.guild_meta(gid) if self.guard else None
        return meta or {"missing": [], "alert_channel": None, "channels": [], "roles": []}

    async def overview(self, request: web.Request) -> web.Response:
        gid, lang = request[GID], request[LANG]
        meta = self._meta(gid)
        o = self.reports.overview(gid, lang, missing=meta["missing"], alert_channel=meta["alert_channel"])
        return web.json_response(o) if o else self._err(404, "Unknown server.")

    async def fix(self, request: web.Request) -> web.Response:
        body = await self._body(request)
        if self.guard is None:
            return self._err(503, t("g.dash_off", request[LANG]))
        ok, text = await self.guard.apply_fix(request[GID], str(body.get("fix", "")))
        return web.json_response({"ok": ok, "text": text, **({} if ok else {"error": text})}, status=200 if ok else 400)

    async def alerts(self, request: web.Request) -> web.Response:
        status = "all" if request.query.get("status") == "all" else "open"
        limit = min(200, self._int(request.query.get("limit", "50")) or 50)
        return web.json_response({"alerts": self.reports.alerts(request[GID], request[LANG], status=status,
                                                                limit=limit)})

    async def alert_action(self, request: web.Request) -> web.Response:
        gid, lang = request[GID], request[LANG]
        aid = self._int(request.match_info["aid"])
        row = self.store.alert(aid) if aid else None
        if row is None or row["guild_id"] != gid:
            return self._err(404, t("g.unknown_alert", lang))
        action = str((await self._body(request)).get("action", ""))
        if action not in ALERT_ACTIONS:
            return self._err(400, t("g.fix_unknown", lang))
        by_id, by_name = self._who(request)
        if self.guard is not None:
            ok, text = await self.guard.act(gid, row["user_id"], action, by_id=by_id, by_name=by_name, alert_id=aid)
        elif action in ("resolve", "false_positive"):
            self.store.resolve_alert(aid, status="false_positive" if action == "false_positive" else "resolved",
                                     by=by_id, by_name=by_name, action=action)
            ok, text = True, t("g.done", lang, action=t(f"g.act_{action}", lang))
        else:
            return self._err(503, t("g.dash_off", lang))
        if not ok:
            return self._err(400, text)
        alert = self.reports.alert_dict(self.store.alert(aid), lang)
        return web.json_response({"ok": True, "text": text, "alert": alert})

    async def members(self, request: web.Request) -> web.Response:
        q = request.query
        filt = q.get("filter", "all") if q.get("filter") in ("all", "at_risk", "minors", "watch", "new") else "all"
        sort = q.get("sort", "risk") if q.get("sort") in ("risk", "recent", "name") else "risk"
        limit = min(500, self._int(q.get("limit", "100")) or 100)
        return web.json_response(self.reports.members(request[GID], request[LANG], filter=filt, sort=sort,
                                                      q=q.get("q", "")[:64], limit=limit))

    async def member(self, request: web.Request) -> web.Response:
        uid = self._int(request.match_info["uid"])
        r = self.reports.person(request[GID], uid, request[LANG]) if uid else None
        return web.json_response(r) if r else self._err(404, t("g.gone", request[LANG]))

    async def member_action(self, request: web.Request) -> web.Response:
        gid, lang = request[GID], request[LANG]
        uid = self._int(request.match_info["uid"])
        if uid is None or self.store.member(gid, uid) is None:
            return self._err(404, t("g.gone", lang))
        action = str((await self._body(request)).get("action", ""))
        if action not in MEMBER_ACTIONS:
            return self._err(400, t("g.fix_unknown", lang))
        by_id, by_name = self._who(request)
        if self.guard is not None:
            ok, text = await self.guard.act(gid, uid, action, by_id=by_id, by_name=by_name)
        elif action in ("watch", "trust", "clear"):
            status = {"watch": "watch", "trust": "trusted", "clear": "none"}[action]
            self.store.set_member(gid, uid, status=status, status_by=by_id)
            self.store.event(gid, uid, "status", {"status": status, "by": by_name})
            self.reports.engine.rescore(gid, uid)
            ok, text = True, t("g.done", lang, action=t(f"g.act_{action}", lang))
        else:
            return self._err(503, t("g.dash_off", lang))
        if not ok:
            return self._err(400, text)
        return web.json_response({"ok": True, "text": text,
                                  "member": self.reports.member_row(self.store.member(gid, uid), lang)})

    def _settings_out(self, gid: int) -> dict[str, Any]:
        st = self.store.settings(gid)
        out = {k: (str(v) if k.endswith("_id") and v else v) for k, v in st.items()}
        out["minor_role_ids"] = [str(r) for r in st["minor_role_ids"]]
        return out

    async def get_settings(self, request: web.Request) -> web.Response:
        meta = self._meta(request[GID])
        return web.json_response({"settings": self._settings_out(request[GID]), "channels": meta["channels"],
                                  "roles": meta["roles"]})

    async def put_settings(self, request: web.Request) -> web.Response:
        body = await self._body(request)
        try:
            clean_settings(body)
            self.store.update_settings(request[GID], body)
        except ValueError as e:
            return self._err(400, str(e))
        return web.json_response({"ok": True, "settings": self._settings_out(request[GID])})

    # --- owner ------------------------------------------------------------------------------
    def system(self) -> dict[str, Any]:
        db = self.store.path
        size = sum(os.path.getsize(p) for p in (db, db + "-wal") if db != ":memory:" and os.path.exists(p))
        guard = self.guard.system() if self.guard else {"guard_online": False, "latency_ms": None,
                                                        "events_per_min": self.reports.engine.events_per_min()}
        pocket_ok = bool(self.pocket and self.pocket.is_ready())
        return {"uptime_s": int(time.time() - self.started), "version": __version__,
                "rules": "private" if is_private() else "public", "pocket_online": pocket_ok,
                "guard_online": guard["guard_online"],
                "latency_ms": {"pocket": round(self.pocket.latency * 1000) if pocket_ok else None,
                               "guard": guard["latency_ms"]},
                "db_bytes": size, "events_per_min": guard["events_per_min"]}

    async def owner_overview(self, request: web.Request) -> web.Response:
        return web.json_response(self.reports.owner(request[LANG], self.system()))

    async def owner_network(self, request: web.Request) -> web.Response:
        uid = self._int(request.match_info["uid"])
        if (await self._body(request)).get("action") != "clear" or uid is None:
            return self._err(400, "Unknown action.")
        self.store.x("DELETE FROM network WHERE user_id=?", uid)
        return web.json_response({"ok": True})

    async def owner_guild(self, request: web.Request) -> web.Response:
        gid = self._int(request.match_info["gid"])
        if (await self._body(request)).get("action") != "leave" or gid is None:
            return self._err(400, "Unknown action.")
        g = self.guard.get_guild(gid) if self.guard else None
        if g is not None:
            await g.leave()
        self.store.guild_left(gid)
        return web.json_response({"ok": True})
