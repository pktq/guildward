"""Dashboard server: the JSON API from docs/GUARD_API.md plus the static SPA in web/dashboard.

Runs on aiohttp (already a discord.py dependency) in the same event loop as the bots, so API calls
can act through the live Guard client. Two ways in: "Sign in with Discord" (OAuth2, scopes `identify guilds`,
needs DISCORD_CLIENT_SECRET; works while the bot is offline), or a one-time link the bot hands a member
inside Discord (`/guard dashboard`).
The bot owner can also get a link from `uv run guildward owner-link`.

A session only proves who someone is. What they may do in a server (view / act / admin) is worked out on
every request from their roles right now, so taking a role away takes the access away at once.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import logging
import os
import re
import secrets
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

import aiohttp
from aiohttp import web

import guildward.guard.render  # noqa: F401  (registers the g.* strings the API answers with)
from guildward import __version__
from guildward.core.i18n import t
from guildward.guard.store import ACCESS, NOTE_MAX, Store, clean_settings
from guildward.intel import semantic
from guildward.intel.rules import is_private

if TYPE_CHECKING:
    from guildward.guard.bot import GuardBot
    from guildward.guard.reports import Reports

log = logging.getLogger(__name__)

STATIC = Path(__file__).resolve().parents[3] / "web" / "dashboard"
COOKIE = "gw_session"
LINK_TTL = 600
SESSION_TTL = 12 * 3600
PUBLIC_TTL = 300  # seconds the public stats are cached
SESSION = web.RequestKey("session", object)
LANG = web.RequestKey("lang", str)
GUILDS = web.RequestKey("guilds", set)
OWNER = web.RequestKey("owner", bool)
GID = web.RequestKey("gid", int)
LEVEL = web.RequestKey("level", str)
OAUTH_COOKIE = "gw_oauth"  # binds a Discord sign-in to the browser that started it (login CSRF)
OAUTH_TTL = 600
DISCORD_API = "https://discord.com/api/v10"
MANAGE = 0x8 | 0x20  # Administrator, Manage Server
# Non-GET guild routes need "admin" unless listed here.
NEED_ACT = {("POST", "/api/guilds/{gid}/alerts/{aid}"), ("POST", "/api/guilds/{gid}/members/{uid}")}
_NEXT = re.compile(r"/dashboard(?:[/?#][A-Za-z0-9/_?=&#%.-]*)?")
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


def safe_next(path: object) -> str | None:
    """A dashboard path to land on after sign-in, or None. Same-origin `/dashboard...` only: no open redirect."""
    if not isinstance(path, str) or len(path) > 200 or "//" in path or ".." in path:
        return None
    return path if _NEXT.fullmatch(path) else None


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
                 owner_ids: frozenset[int], guard: GuardBot | None = None, pocket: Any = None,
                 crowd: Any = None, client_secret: str = "", client_id: int | None = None) -> None:
        self.store, self.reports = store, reports
        self.crowd = crowd  # pocket.Pocket: shared flags from every Guildward user
        self.base_url = base_url.rstrip("/")
        self.host, self.port = host, port
        self.owner_ids = owner_ids
        self.guard, self.pocket = guard, pocket
        self.secret = secret_for(store)
        self.client_secret = client_secret
        self._client_id = client_id  # from the token, for when the bot is offline
        self.started = time.time()
        self._runner: web.AppRunner | None = None
        self._public: tuple[float, dict[str, Any]] | None = None
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
        r.add_get("/auth/discord", self.discord_start)
        r.add_get("/auth/discord/callback", self.discord_callback)
        r.add_get("/api/public/auth", self.public_auth)
        r.add_post("/api/logout", self.logout)
        r.add_get("/api/me", self.me)
        r.add_get("/api/public/stats", self.public_stats)
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
        r.add_get("/api/owner/accounts", self.owner_accounts)
        r.add_post("/api/owner/accounts/{uid}", self.owner_account)
        r.add_get("/pocket/callback", self.pocket_callback)
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
        if not request.path.startswith("/api/") or request.path.startswith("/api/public/"):
            return await handler(request)
        if request.method in ("POST", "PUT", "DELETE") and request.headers.get("X-Guildward") != "1":
            return self._err(403, "Missing X-Guildward header.")
        token = request.cookies.get(COOKIE)
        sess = self.store.session(_hash(token)) if token else None
        if sess is None:
            return self._err(401, "Sign in again: run /guard dashboard in your server.")
        request[SESSION] = sess
        # shortcut: the dashboard is English-only for now; use sess["lang"] again when Swedish comes back.
        request[LANG] = "en"
        request[GUILDS] = {int(g) for g in json.loads(sess["guilds"] or "[]")}
        request[OWNER] = bool(sess["owner"])
        if "gid" in request.match_info and request.path.startswith("/api/guilds/"):
            gid = self._int(request.match_info["gid"])
            level = self._level(request, gid) if gid is not None else None
            if level is None:
                return self._err(403, "No access to this server.")
            route = (request.method, request.match_info.route.resource.canonical)
            need = "view" if request.method == "GET" else "act" if route in NEED_ACT else "admin"
            if ACCESS.index(level) < ACCESS.index(need):
                return self._err(403, t(f"g.dash_need_{need}", request[LANG]))
            request[GID], request[LEVEL] = gid, level
        if request.path.startswith("/api/owner/") and not request[OWNER]:
            return self._err(403, "Owner only.")
        return await handler(request)

    def _level(self, request: web.Request, gid: int) -> str | None:
        """view | act | admin in this server, or None. Live from Guard's member cache on every request."""
        if request[OWNER]:
            return "admin" if self.store.guild(gid) is not None else None
        if self.guard is not None and self.guard.get_guild(gid) is not None:
            return self.guard.access(gid, request[SESSION]["user_id"])
        # No live bot for this server (dashboard-only mode): trust the server a signed link named, as before.
        return "admin" if gid in request[GUILDS] else None

    def _actor(self, request: web.Request, gid: int) -> Any:
        """The signed-in member, so Guard checks their own Discord permission for timeout/kick/ban/delete."""
        if request[OWNER] or self.guard is None or (g := self.guard.get_guild(gid)) is None:
            return None
        return g.get_member(request[SESSION]["user_id"])

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

    @staticmethod
    def _page(status: int, title: str, body: str) -> web.Response:
        return web.Response(status=status, content_type="text/html", text=(
            "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>Guildward</title><body style='font:16px system-ui;padding:3rem 16px;max-width:36rem;margin:auto;"
            f"background:#0d1117;color:#e6edf3'><h1>{html.escape(title)}</h1><p>{body}</p>"
            "<p><a style='color:#58a6ff' href='/dashboard'>Back to the dashboard</a>"))

    def _session_response(self, dest: str, *, user_id: int, name: str, avatar: str | None, guilds: list[str],
                          owner: bool, lang: str) -> web.HTTPFound:
        token = secrets.token_urlsafe(32)
        self.store.add_session(_hash(token), user_id=user_id, name=name, avatar=avatar, guilds=guilds, owner=owner,
                               lang=lang, ttl=SESSION_TTL)
        resp = web.HTTPFound(dest)
        resp.set_cookie(COOKIE, token, max_age=SESSION_TTL, httponly=True, samesite="Strict",
                        secure=self.base_url.startswith("https://"), path="/")
        return resp

    async def auth(self, request: web.Request) -> web.StreamResponse:
        payload = verify(self.secret, request.query.get("t", ""))
        # "t" marks the other signed tokens (Discord sign-in state, server-scan state), never a sign-in link.
        if payload is None or "t" in payload or not self.store.use_nonce(payload["x"], payload["e"]):
            return self._page(403, "This sign-in link has expired",
                              "Links work once, for 10 minutes. Run <code>/guard dashboard</code> in your server for a "
                              "new one, or sign in with Discord.")
        uid = int(payload["u"])
        guilds = {payload["g"]} if payload.get("g") else set()
        old = request.cookies.get(COOKIE)
        prev = self.store.session(_hash(old)) if old else None
        if prev is not None and prev["user_id"] == uid:
            guilds |= set(json.loads(prev["guilds"] or "[]"))
            self.store.drop_session(_hash(old))
        dest = payload.get("p") or (f"/g/{payload['g']}" if payload.get("g") else "/owner")
        raise self._session_response(f"/#{dest}", user_id=uid, name=payload["n"], avatar=payload.get("a"),
                                     guilds=sorted(guilds), owner=bool(payload.get("o")),
                                     lang=payload.get("l") or "en")

    # --- Sign in with Discord (OAuth2, scopes identify + guilds) -----------------------------
    @property
    def client_id(self) -> int | None:
        return (self.guard.application_id if self.guard is not None else None) or self._client_id

    @property
    def oauth_enabled(self) -> bool:
        return bool(self.client_secret and self.client_id)

    @property
    def redirect_uri(self) -> str:
        return f"{self.base_url}/auth/discord/callback"

    async def public_auth(self, request: web.Request) -> web.Response:
        """No sign-in: which sign-in methods the dashboard should offer."""
        return web.json_response({"discord": self.oauth_enabled, "link": True})

    def _oauth_off(self) -> web.Response:
        return self._page(503, "Discord sign-in is off here",
                          "This Guard instance has no <code>DISCORD_CLIENT_SECRET</code> (or bot token) set. Run "
                          "<code>/guard dashboard</code> in your server for a sign-in link instead.")

    async def discord_start(self, request: web.Request) -> web.StreamResponse:
        if not self.oauth_enabled:
            return self._oauth_off()
        bind = secrets.token_urlsafe(24)
        state = sign(self.secret, {"t": "login", "p": safe_next(request.query.get("next")), "b": _hash(bind),
                                   "e": int(time.time()) + OAUTH_TTL, "x": secrets.token_hex(8)})
        resp = web.HTTPFound("https://discord.com/oauth2/authorize?" + urlencode({
            "client_id": str(self.client_id), "response_type": "code", "redirect_uri": self.redirect_uri,
            "scope": "identify guilds", "state": state, "prompt": "none"}))
        # Lax, not Strict: the callback is a top-level navigation coming back from discord.com.
        resp.set_cookie(OAUTH_COOKIE, bind, max_age=OAUTH_TTL, httponly=True, samesite="Lax",
                        secure=self.base_url.startswith("https://"), path="/auth/discord")
        raise resp

    async def discord_callback(self, request: web.Request) -> web.StreamResponse:
        q = request.query
        bind = request.cookies.get(OAUTH_COOKIE, "")
        payload = verify(self.secret, q.get("state", ""))
        valid = (payload is not None and payload.get("t") == "login" and bool(bind)
                 and hmac.compare_digest(str(payload.get("b", "")), _hash(bind))
                 and self.store.use_nonce("login:" + str(payload.get("x")), int(payload.get("e", 0))))
        resp: web.StreamResponse
        if not valid:
            resp = self._page(403, "This sign-in has expired", "A sign-in has to finish within 10 minutes, in "
                              "the browser that started it. Start again from the dashboard.")
        elif q.get("error") or not q.get("code"):
            resp = web.HTTPFound("/dashboard")  # pressed Cancel on Discord's screen
        elif not self.oauth_enabled:
            resp = self._oauth_off()
        elif (user := await self._discord_user(q["code"])) is None or not str(user.get("id", "")).isdigit():
            resp = self._page(502, "Discord didn't confirm your account", "Please try again in a moment.")
        else:
            uid = int(user["id"])
            avatar = (f"https://cdn.discordapp.com/avatars/{uid}/{user['avatar']}.png?size=64"
                      if re.fullmatch(r"(a_)?[0-9a-f]{32}", str(user.get("avatar") or "")) else None)
            owner = uid in self.owner_ids
            managed = self._managed(user.get("guilds"))
            resp = self._session_response(
                safe_next(payload.get("p")) or self._home(uid, owner, managed), user_id=uid,
                name=str(user.get("global_name") or user.get("username") or uid)[:100], avatar=avatar, guilds=managed,
                owner=owner, lang="sv" if str(user.get("locale", "")).startswith("sv") else "en")
        resp.del_cookie(OAUTH_COOKIE, path="/auth/discord")
        if isinstance(resp, web.HTTPException):
            raise resp
        return resp

    def _managed(self, guilds: Any) -> list[str]:
        """Servers Discord says this user owns or can manage, that Guard knows. Used when the bot can't check
        live (offline, or no longer in that server); role-based mod access needs the bot."""
        out = []
        for g in guilds if isinstance(guilds, list) else []:
            try:
                gid, perms = int(g["id"]), int(g.get("permissions") or 0)
            except (TypeError, ValueError, KeyError, AttributeError):
                continue
            if (g.get("owner") is True or perms & MANAGE) and self.store.guild(gid) is not None:
                out.append(str(gid))
        return out

    def _home(self, uid: int, owner: bool, managed: list[str]) -> str:
        if owner:
            return "/dashboard/owner"
        for g in self.store.active_guilds():
            if self.guard is not None and self.guard.get_guild(g["id"]) is not None and self.guard.access(g["id"], uid):
                return f"/dashboard/g/{g['id']}"
        return f"/dashboard/g/{managed[0]}" if managed else "/dashboard"

    async def _discord_user(self, code: str) -> dict[str, Any] | None:
        """Code -> access token -> /users/@me (+ its server list as "guilds"), then revoke the token: only the
        identity and the managed server IDs are kept, never the token."""
        creds = {"client_id": str(self.client_id), "client_secret": self.client_secret}
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as http:
                async with http.post(f"{DISCORD_API}/oauth2/token", data={
                        **creds, "grant_type": "authorization_code", "code": code,
                        "redirect_uri": self.redirect_uri}) as r:
                    if r.status != 200:
                        log.warning("discord sign-in: token exchange failed (%s)", r.status)
                        return None
                    access = (await r.json()).get("access_token", "")
                auth = {"Authorization": f"Bearer {access}"}
                async with http.get(f"{DISCORD_API}/users/@me", headers=auth) as r:
                    me = await r.json() if r.status == 200 else None
                async with http.get(f"{DISCORD_API}/users/@me/guilds", headers=auth) as r:
                    guilds = await r.json() if r.status == 200 else []
                async with http.post(f"{DISCORD_API}/oauth2/token/revoke",
                                     data={**creds, "token": access, "token_type_hint": "access_token"}):
                    pass
        except (aiohttp.ClientError, TimeoutError, ValueError) as e:
            log.warning("discord sign-in failed: %s", type(e).__name__)
            return None
        return {**me, "guilds": guilds} if isinstance(me, dict) else None

    async def logout(self, request: web.Request) -> web.Response:
        token = request.cookies.get(COOKIE)
        if token:
            self.store.drop_session(_hash(token))
        resp = web.json_response({"ok": True})
        resp.del_cookie(COOKIE, path="/")
        return resp

    async def me(self, request: web.Request) -> web.Response:
        s = request[SESSION]
        ids = [g["id"] for g in self.store.active_guilds()]
        ids += [gid for gid in sorted(request[GUILDS]) if gid not in ids and not request[OWNER]]
        guilds = []
        for gid in ids:
            g = self.store.guild(gid)
            if g is not None and (level := self._level(request, gid)):
                guilds.append({"id": str(gid), "name": g["name"], "icon": g["icon"], "level": level})
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
        body = await self._body(request)
        action, note = str(body.get("action", "")), body.get("note")
        if note is not None and (not isinstance(note, str) or len(note.strip()) > NOTE_MAX):
            return self._err(400, t("g.note_long", lang))
        note = (note or "").strip() or None
        by_id, by_name = self._who(request)
        if action in ("claim", "unclaim"):
            force = request[LEVEL] == "admin"  # admins may release someone else's claim
            if self.guard is not None:
                ok, text = await self.guard.claim(aid, by_id=by_id, by_name=by_name, action=action, force=force)
            else:
                code = self.store.claim_alert(aid, by=by_id, by_name=by_name, action=action, force=force)
                ok = code in ("claimed", "unclaimed")
                text = t(f"g.claim_{code}", lang, name=self.store.alert(aid)["assigned_name"] or "?")
            if not ok:
                return self._err(409, text)
            return web.json_response({"ok": True, "text": text,
                                      "alert": self.reports.alert_dict(self.store.alert(aid), lang)})
        if action not in ALERT_ACTIONS:
            return self._err(400, t("g.fix_unknown", lang))
        if self.guard is not None:
            ok, text = await self.guard.act(gid, row["user_id"], action, by_id=by_id, by_name=by_name, alert_id=aid,
                                            actor=self._actor(request, gid), note=note)
        elif action in ("resolve", "false_positive"):
            self.store.resolve_alert(aid, status="false_positive" if action == "false_positive" else "resolved",
                                     by=by_id, by_name=by_name, action=action, note=note)
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
            ok, text = await self.guard.act(gid, uid, action, by_id=by_id, by_name=by_name,
                                            actor=self._actor(request, gid))
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
        out["dashboard_roles"] = dict(st["dashboard_roles"])
        return out

    async def get_settings(self, request: web.Request) -> web.Response:
        meta = self._meta(request[GID])
        return web.json_response({"settings": self._settings_out(request[GID]), "channels": meta["channels"],
                                  "roles": meta["roles"]})

    async def put_settings(self, request: web.Request) -> web.Response:
        body = await self._body(request)
        try:
            clean_settings(body)
            meta = self.guard.guild_meta(request[GID]) if self.guard is not None else None
            if meta is not None and "dashboard_roles" in body:
                known = {r["id"] for r in meta["roles"]}  # no @everyone, no bot-managed roles
                if not {str(k) for k in body["dashboard_roles"]} <= known:
                    raise ValueError("dashboard_roles: unknown role")
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
                "db_bytes": size, "events_per_min": guard["events_per_min"], "model": semantic.status()}

    async def owner_overview(self, request: web.Request) -> web.Response:
        out = self.reports.owner(request[LANG], self.system())
        if self.crowd is not None:
            out["crowd"] = self.crowd.stats()
        return web.json_response(out)

    async def public_stats(self, request: web.Request) -> web.Response:
        """No sign-in: aggregate counts for the public site's stats page, rebuilt at most every 5 minutes."""
        if self._public is None or time.time() - self._public[0] > PUBLIC_TTL:
            self._public = (time.time(), self.reports.public(self.crowd.stats() if self.crowd is not None else None))
        return web.json_response(self._public[1], headers={"Cache-Control": f"public, max-age={PUBLIC_TTL}",
                                                           "Access-Control-Allow-Origin": "*"})

    async def owner_accounts(self, request: web.Request) -> web.Response:
        if self.crowd is None:
            return web.json_response({"counts": {}, "accounts": []})
        return web.json_response(self.crowd.owner_accounts(request.query.get("status", "review")))

    async def owner_account(self, request: web.Request) -> web.Response:
        uid = self._int(request.match_info["uid"])
        action = (await self._body(request)).get("action")
        if self.crowd is None or uid is None or not self.crowd.owner_action(uid, str(action), self._who(request)[0]):
            return self._err(400, "Unknown account or action.")
        return web.json_response({"ok": True})

    async def pocket_callback(self, request: web.Request) -> web.Response:
        from guildward.bot import scan

        lang = "en"
        status = "failed"
        code, state = request.query.get("code"), request.query.get("state")
        if self.pocket is not None and code and state:
            payload = verify(self.secret, state)
            lang = payload.get("l", "en") if payload else "en"
            try:
                status = await scan.finish(self.pocket, code, state)
            except Exception:
                log.exception("server scan callback failed")
        elif request.query.get("error"):
            status = "expired"
        text = html.escape(t(f"scan.page.{status}", lang))
        return web.Response(content_type="text/html", text=(
            "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>Guildward</title><body style='font:18px system-ui;max-width:32rem;margin:15vh auto;padding:0 16px;"
            f"color:#1f2328;background:#fff'><h1>Guildward</h1><p>{text}</p>"))

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
