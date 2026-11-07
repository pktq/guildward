"""Guard's local database (SQLite, stdlib). Holds who is in a server and what Guard observed about them.

Privacy invariant: message *text* is never written here. An observation is a signal code, a weight,
who sent it, who it was aimed at, and the message/channel IDs, so admins can jump to the evidence in
Discord while Discord keeps the content. Everything is per guild and purged after `retention_days`.

Times are unix seconds (int). Discord IDs are ints.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from guildward.intel.behavior import Obs

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS guilds(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL DEFAULT '', icon TEXT, owner_id INTEGER,
  member_count INTEGER NOT NULL DEFAULT 0, joined_at INTEGER, left_at INTEGER,
  settings TEXT NOT NULL DEFAULT '{}', audit TEXT NOT NULL DEFAULT '{}', audit_at INTEGER);
CREATE TABLE IF NOT EXISTS members(
  guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
  username TEXT NOT NULL DEFAULT '', display TEXT, avatar TEXT, has_avatar INTEGER NOT NULL DEFAULT 0,
  is_bot INTEGER NOT NULL DEFAULT 0, spammer INTEGER NOT NULL DEFAULT 0,
  joined_at INTEGER, left_at INTEGER, invite_code TEXT, inviter_id INTEGER,
  self_age INTEGER, self_age_at INTEGER, role_age TEXT, roles TEXT NOT NULL DEFAULT '[]',
  msg_count INTEGER NOT NULL DEFAULT 0, last_msg_at INTEGER,
  status TEXT NOT NULL DEFAULT 'none', status_by INTEGER, raid_join INTEGER NOT NULL DEFAULT 0,
  score INTEGER NOT NULL DEFAULT 0, level TEXT NOT NULL DEFAULT 'green', score_at INTEGER,
  top_code TEXT, top_params TEXT, codes TEXT NOT NULL DEFAULT '[]', timeout_at INTEGER,
  PRIMARY KEY(guild_id, user_id));
CREATE INDEX IF NOT EXISTS members_score ON members(guild_id, score DESC);
CREATE TABLE IF NOT EXISTS score_days(
  guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, day TEXT NOT NULL, score INTEGER NOT NULL DEFAULT 0,
  msgs INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(guild_id, user_id, day));
CREATE TABLE IF NOT EXISTS observations(
  id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, code TEXT NOT NULL,
  weight INTEGER NOT NULL, params TEXT NOT NULL DEFAULT '{}', target_id INTEGER,
  target_minor INTEGER NOT NULL DEFAULT 0, channel_id INTEGER, message_id INTEGER, at INTEGER NOT NULL,
  deleted INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS obs_user ON observations(guild_id, user_id, at);
CREATE INDEX IF NOT EXISTS obs_msg ON observations(guild_id, message_id);
CREATE INDEX IF NOT EXISTS obs_code ON observations(code, at);
CREATE TABLE IF NOT EXISTS contacts(
  guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, target_id INTEGER NOT NULL,
  msgs INTEGER NOT NULL DEFAULT 0, first_at INTEGER NOT NULL, last_at INTEGER NOT NULL,
  stages TEXT NOT NULL DEFAULT '{}', risk INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(guild_id, user_id, target_id));
CREATE INDEX IF NOT EXISTS contacts_target ON contacts(guild_id, target_id);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, user_id INTEGER, kind TEXT NOT NULL,
  data TEXT NOT NULL DEFAULT '{}', at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS events_user ON events(guild_id, user_id, at);
CREATE TABLE IF NOT EXISTS alerts(
  id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, kind TEXT NOT NULL, level TEXT NOT NULL, score INTEGER NOT NULL,
  user_id INTEGER, target_id INTEGER, title TEXT NOT NULL, params TEXT NOT NULL DEFAULT '{}',
  signals TEXT NOT NULL DEFAULT '[]', channel_id INTEGER, message_id INTEGER, post_channel_id INTEGER,
  post_id INTEGER, status TEXT NOT NULL DEFAULT 'open', created_at INTEGER NOT NULL,
  resolved_by INTEGER, resolved_by_name TEXT, resolved_at INTEGER, action TEXT);
CREATE INDEX IF NOT EXISTS alerts_guild ON alerts(guild_id, status, created_at);
CREATE TABLE IF NOT EXISTS reports(
  id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, reporter_id INTEGER NOT NULL, target_id INTEGER NOT NULL,
  channel_id INTEGER, message_id INTEGER, at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS network(
  user_id INTEGER NOT NULL, guild_id INTEGER NOT NULL, reason TEXT NOT NULL, at INTEGER NOT NULL,
  PRIMARY KEY(user_id, guild_id));
CREATE TABLE IF NOT EXISTS feedback(code TEXT NOT NULL, guild_id INTEGER NOT NULL, at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS daily(
  guild_id INTEGER NOT NULL, day TEXT NOT NULL, metric TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(guild_id, day, metric));
CREATE TABLE IF NOT EXISTS sessions(
  token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL, avatar TEXT, guilds TEXT NOT NULL DEFAULT '[]',
  owner INTEGER NOT NULL DEFAULT 0, lang TEXT NOT NULL DEFAULT 'en', expires INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS used_nonces(nonce TEXT PRIMARY KEY, expires INTEGER NOT NULL);
"""

DEFAULT_SETTINGS: dict[str, Any] = {
    "mode": "observe",
    "alert_channel_id": None,
    "alert_min_level": "yellow",
    "ping_role_id": None,
    "auto_delete": True,
    "auto_timeout": True,
    "quarantine_role_id": None,
    "quarantine_new_accounts": False,
    "raid_protection": True,
    "warn_targets": True,
    "network_share": True,
    "quote_in_alerts": True,
    "minor_role_ids": [],
    "retention_days": 90,
    "lang": "en",
}
_ID_SETTINGS = {"alert_channel_id", "ping_role_id", "quarantine_role_id"}
_CHOICES = {"mode": {"observe", "protect"}, "alert_min_level": {"yellow", "red"}, "lang": {"en", "sv"}}


def clean_settings(patch: dict[str, Any]) -> dict[str, Any]:
    """Validate a partial settings update from the dashboard or a command. Raises ValueError."""
    out: dict[str, Any] = {}
    for key, value in patch.items():
        if key not in DEFAULT_SETTINGS:
            raise ValueError(f"unknown setting {key!r}")
        default = DEFAULT_SETTINGS[key]
        if key in _ID_SETTINGS:
            if value in (None, "", 0, "0"):
                out[key] = None
            elif str(value).isdigit():
                out[key] = int(value)
            else:
                raise ValueError(f"{key} must be an ID")
        elif key == "minor_role_ids":
            if not isinstance(value, list) or not all(str(v).isdigit() for v in value):
                raise ValueError("minor_role_ids must be a list of IDs")
            out[key] = [int(v) for v in value][:50]
        elif key == "retention_days":
            if not isinstance(value, int) or isinstance(value, bool) or not 7 <= value <= 365:
                raise ValueError("retention_days must be 7..365")
            out[key] = value
        elif isinstance(default, bool):
            if not isinstance(value, bool):
                raise ValueError(f"{key} must be true/false")
            out[key] = value
        else:
            if value not in _CHOICES[key]:
                raise ValueError(f"{key} must be one of {sorted(_CHOICES[key])}")
            out[key] = value
    return out


def now() -> int:
    return int(time.time())


def day_of(ts: int) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")


def last_days(n: int, end: int | None = None) -> list[str]:
    end_dt = datetime.fromtimestamp(end or now(), UTC)
    return [(end_dt - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n - 1, -1, -1)]


class Store:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self.db = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        self.db.execute("BEGIN")
        try:
            yield self.db
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        self.db.execute("COMMIT")

    def q(self, sql: str, *args: Any) -> list[sqlite3.Row]:
        return self.db.execute(sql, args).fetchall()

    def one(self, sql: str, *args: Any) -> sqlite3.Row | None:
        return self.db.execute(sql, args).fetchone()

    def val(self, sql: str, *args: Any, default: Any = 0) -> Any:
        row = self.db.execute(sql, args).fetchone()
        return default if row is None or row[0] is None else row[0]

    def x(self, sql: str, *args: Any) -> int:
        cur = self.db.execute(sql, args)
        return cur.lastrowid or cur.rowcount

    # --- meta -------------------------------------------------------------------------------
    def meta(self, key: str) -> str | None:
        return self.val("SELECT value FROM meta WHERE key=?", key, default=None)

    def set_meta(self, key: str, value: str) -> None:
        self.x("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               key, value)

    # --- guilds -----------------------------------------------------------------------------
    def upsert_guild(self, gid: int, *, name: str, icon: str | None, owner_id: int | None,
                     member_count: int) -> None:
        self.x("""INSERT INTO guilds(id,name,icon,owner_id,member_count,joined_at) VALUES(?,?,?,?,?,?)
                  ON CONFLICT(id) DO UPDATE SET name=excluded.name, icon=excluded.icon, owner_id=excluded.owner_id,
                  member_count=excluded.member_count, left_at=NULL""",
               gid, name, icon, owner_id, member_count, now())

    def guild(self, gid: int) -> sqlite3.Row | None:
        return self.one("SELECT * FROM guilds WHERE id=?", gid)

    def active_guilds(self) -> list[sqlite3.Row]:
        return self.q("SELECT * FROM guilds WHERE left_at IS NULL ORDER BY member_count DESC")

    def guild_left(self, gid: int) -> None:
        self.x("UPDATE guilds SET left_at=? WHERE id=?", now(), gid)

    def settings(self, gid: int) -> dict[str, Any]:
        raw = self.val("SELECT settings FROM guilds WHERE id=?", gid, default="{}")
        return {**DEFAULT_SETTINGS, **json.loads(raw)}

    def update_settings(self, gid: int, patch: dict[str, Any]) -> dict[str, Any]:
        merged = {**self.settings(gid), **clean_settings(patch)}
        stored = {k: v for k, v in merged.items() if DEFAULT_SETTINGS[k] != v}
        self.x("UPDATE guilds SET settings=? WHERE id=?", json.dumps(stored), gid)
        return merged

    def save_audit(self, gid: int, audit: dict[str, Any]) -> None:
        self.x("UPDATE guilds SET audit=?, audit_at=? WHERE id=?", json.dumps(audit), now(), gid)

    # --- members ----------------------------------------------------------------------------
    def member(self, gid: int, uid: int) -> sqlite3.Row | None:
        return self.one("SELECT * FROM members WHERE guild_id=? AND user_id=?", gid, uid)

    def upsert_member(self, gid: int, uid: int, **fields: Any) -> None:
        cols = ["guild_id", "user_id", *fields]
        placeholders = ",".join("?" * len(cols))
        updates = ",".join(f"{c}=excluded.{c}" for c in fields) or "user_id=user_id"
        self.x(f"INSERT INTO members({','.join(cols)}) VALUES({placeholders}) "
               f"ON CONFLICT(guild_id,user_id) DO UPDATE SET {updates}", gid, uid, *fields.values())

    def set_member(self, gid: int, uid: int, **fields: Any) -> None:
        sets = ",".join(f"{c}=?" for c in fields)
        self.x(f"UPDATE members SET {sets} WHERE guild_id=? AND user_id=?", *fields.values(), gid, uid)

    def is_minor(self, gid: int, uid: int) -> bool:
        row = self.one("SELECT self_age, role_age FROM members WHERE guild_id=? AND user_id=?", gid, uid)
        return bool(row) and is_minor_row(row)

    def record_score(self, gid: int, uid: int, score: int, level: str, top_code: str | None,
                     top_params: dict[str, Any] | None, at: int | None = None, codes: list[str] | None = None) -> None:
        at = at or now()
        self.set_member(gid, uid, score=score, level=level, score_at=at, top_code=top_code,
                        top_params=json.dumps(top_params or {}), codes=json.dumps(codes or []))
        self.x("""INSERT INTO score_days(guild_id,user_id,day,score) VALUES(?,?,?,?)
                  ON CONFLICT(guild_id,user_id,day) DO UPDATE SET score=excluded.score""",
               gid, uid, day_of(at), score)

    def count_message(self, gid: int, uid: int, at: int) -> None:
        self.x("""INSERT INTO score_days(guild_id,user_id,day,score,msgs) VALUES(?,?,?,
                  COALESCE((SELECT score FROM members WHERE guild_id=? AND user_id=?),0),1)
                  ON CONFLICT(guild_id,user_id,day) DO UPDATE SET msgs=msgs+1""", gid, uid, day_of(at), gid, uid)

    def score_days_ago(self, gid: int, uid: int, days: int) -> int | None:
        cutoff = day_of(now() - days * 86_400)
        return self.val("SELECT score FROM score_days WHERE guild_id=? AND user_id=? AND day<=? "
                        "ORDER BY day DESC LIMIT 1", gid, uid, cutoff, default=None)

    # --- observations / contacts ------------------------------------------------------------
    def observe(self, gid: int, uid: int, code: str, weight: int, params: dict[str, Any] | None = None, *,
                target_id: int | None = None, target_minor: bool = False, channel_id: int | None = None,
                message_id: int | None = None, at: int | None = None) -> None:
        self.x("""INSERT INTO observations(guild_id,user_id,code,weight,params,target_id,target_minor,
                  channel_id,message_id,at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
               gid, uid, code, weight, json.dumps(dict(params or {})), target_id, int(target_minor),
               channel_id, message_id, at or now())

    def observations(self, gid: int, uid: int, since: int) -> list[Obs]:
        rows = self.q("SELECT * FROM observations WHERE guild_id=? AND user_id=? AND at>=? ORDER BY at",
                      gid, uid, since)
        return [Obs(r["code"], r["weight"], json.loads(r["params"]), r["target_id"], bool(r["target_minor"]),
                    r["channel_id"], r["message_id"], r["at"], bool(r["deleted"])) for r in rows]

    def mark_deleted(self, gid: int, message_id: int) -> int | None:
        """Flag observations of a deleted message; returns the author if any were flagged."""
        row = self.one("SELECT user_id FROM observations WHERE guild_id=? AND message_id=? LIMIT 1", gid, message_id)
        if row:
            self.x("UPDATE observations SET deleted=1 WHERE guild_id=? AND message_id=?", gid, message_id)
        return row["user_id"] if row else None

    def touch_contact(self, gid: int, uid: int, target: int, at: int, stages: Iterable[str], risk: int) -> None:
        row = self.one("SELECT stages FROM contacts WHERE guild_id=? AND user_id=? AND target_id=?", gid, uid, target)
        merged: dict[str, int] = json.loads(row["stages"]) if row else {}
        for st in stages:
            merged.setdefault(st, at)
        self.x("""INSERT INTO contacts(guild_id,user_id,target_id,msgs,first_at,last_at,stages,risk)
                  VALUES(?,?,?,1,?,?,?,?) ON CONFLICT(guild_id,user_id,target_id) DO UPDATE SET
                  msgs=msgs+1, last_at=excluded.last_at, stages=excluded.stages, risk=risk+excluded.risk""",
               gid, uid, target, at, at, json.dumps(merged), risk)

    def contacts_of(self, gid: int, uid: int, limit: int = 50) -> list[sqlite3.Row]:
        return self.q("""SELECT c.*, m.self_age, m.role_age, m.username, m.display, m.avatar FROM contacts c
                         LEFT JOIN members m ON m.guild_id=c.guild_id AND m.user_id=c.target_id
                         WHERE c.guild_id=? AND c.user_id=? ORDER BY c.risk DESC, c.msgs DESC LIMIT ?""",
                      gid, uid, limit)

    # --- events / reports / network ---------------------------------------------------------
    def event(self, gid: int, uid: int | None, kind: str, data: dict[str, Any] | None = None,
              at: int | None = None) -> None:
        self.x("INSERT INTO events(guild_id,user_id,kind,data,at) VALUES(?,?,?,?,?)",
               gid, uid, kind, json.dumps(data or {}), at or now())

    def events_of(self, gid: int, uid: int, limit: int = 100) -> list[sqlite3.Row]:
        return self.q("SELECT * FROM events WHERE guild_id=? AND user_id=? ORDER BY at DESC LIMIT ?", gid, uid, limit)

    def add_report(self, gid: int, reporter: int, target: int, channel_id: int | None,
                   message_id: int | None) -> bool:
        """False if this reporter already reported this message/person (no double counting)."""
        dup = self.one("SELECT 1 FROM reports WHERE guild_id=? AND reporter_id=? AND target_id=? "
                       "AND COALESCE(message_id,0)=COALESCE(?,0)", gid, reporter, target, message_id)
        if dup:
            return False
        self.x("INSERT INTO reports(guild_id,reporter_id,target_id,channel_id,message_id,at) VALUES(?,?,?,?,?,?)",
               gid, reporter, target, channel_id, message_id, now())
        return True

    def reporters(self, gid: int, uid: int) -> int:
        return self.val("SELECT COUNT(DISTINCT reporter_id) FROM reports WHERE guild_id=? AND target_id=?", gid, uid)

    def flag_network(self, uid: int, gid: int, reason: str) -> None:
        self.x("INSERT INTO network(user_id,guild_id,reason,at) VALUES(?,?,?,?) "
               "ON CONFLICT(user_id,guild_id) DO UPDATE SET reason=excluded.reason", uid, gid, reason, now())

    def network_flags(self, uid: int, *, exclude_guild: int | None = None) -> list[sqlite3.Row]:
        """Flags from other guilds that share with the network."""
        rows = self.q("SELECT n.*, g.settings FROM network n JOIN guilds g ON g.id=n.guild_id "
                      "WHERE n.user_id=? AND n.guild_id IS NOT ?", uid, exclude_guild)
        return [r for r in rows if json.loads(r["settings"]).get("network_share", True)]

    # --- alerts -----------------------------------------------------------------------------
    def add_alert(self, gid: int, *, kind: str, level: str, score: int, title: str, params: dict[str, Any],
                  signals: list[dict[str, Any]], user_id: int | None = None, target_id: int | None = None,
                  channel_id: int | None = None, message_id: int | None = None) -> int:
        aid = self.x("""INSERT INTO alerts(guild_id,kind,level,score,user_id,target_id,title,params,signals,
                        channel_id,message_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                     gid, kind, level, score, user_id, target_id, title, json.dumps(params), json.dumps(signals),
                     channel_id, message_id, now())
        self.bump(gid, "alerts")
        return aid

    def alert(self, aid: int) -> sqlite3.Row | None:
        return self.one("SELECT * FROM alerts WHERE id=?", aid)

    def recent_alert(self, gid: int, *, kind: str, user_id: int | None, target_id: int | None,
                     within: int, any_target: bool = False) -> sqlite3.Row | None:
        if any_target:
            return self.one("SELECT * FROM alerts WHERE guild_id=? AND kind=? AND user_id IS ? AND created_at>=? "
                            "ORDER BY id DESC LIMIT 1", gid, kind, user_id, now() - within)
        return self.one("SELECT * FROM alerts WHERE guild_id=? AND kind=? AND user_id IS ? AND target_id IS ? "
                        "AND created_at>=? ORDER BY id DESC LIMIT 1", gid, kind, user_id, target_id, now() - within)

    def resolve_alert(self, aid: int, *, status: str, by: int | None, by_name: str | None,
                      action: str | None) -> None:
        self.x("UPDATE alerts SET status=?, resolved_by=?, resolved_by_name=?, resolved_at=?, action=? WHERE id=?",
               status, by, by_name, now(), action, aid)
        if status == "false_positive":
            row = self.alert(aid)
            if row:
                for s in json.loads(row["signals"]):
                    self.x("INSERT INTO feedback(code,guild_id,at) VALUES(?,?,?)", s["code"], row["guild_id"], now())

    # --- metrics ----------------------------------------------------------------------------
    def bump(self, gid: int, metric: str, n: int = 1, at: int | None = None) -> None:
        self.x("""INSERT INTO daily(guild_id,day,metric,n) VALUES(?,?,?,?)
                  ON CONFLICT(guild_id,day,metric) DO UPDATE SET n=n+excluded.n""",
               gid, day_of(at or now()), metric, n)

    def series(self, gid: int | None, metric: str, days: int = 30) -> list[int]:
        """Daily counts, oldest first. gid None = all guilds except the global row 0."""
        span = last_days(days)
        if gid is None:
            rows = self.q("SELECT day, SUM(n) n FROM daily WHERE guild_id<>0 AND metric=? AND day>=? GROUP BY day",
                          metric, span[0])
        else:
            rows = self.q("SELECT day, n FROM daily WHERE guild_id=? AND metric=? AND day>=?", gid, metric, span[0])
        by_day = {r["day"]: r["n"] for r in rows}
        return [by_day.get(d, 0) for d in span]

    # --- sessions ---------------------------------------------------------------------------
    def add_session(self, token_hash: str, *, user_id: int, name: str, avatar: str | None, guilds: list[str],
                    owner: bool, lang: str, ttl: int) -> None:
        self.x("INSERT INTO sessions(token,user_id,name,avatar,guilds,owner,lang,expires) VALUES(?,?,?,?,?,?,?,?)",
               token_hash, user_id, name, avatar, json.dumps(guilds), int(owner), lang, now() + ttl)

    def session(self, token_hash: str) -> sqlite3.Row | None:
        return self.one("SELECT * FROM sessions WHERE token=? AND expires>?", token_hash, now())

    def drop_session(self, token_hash: str) -> None:
        self.x("DELETE FROM sessions WHERE token=?", token_hash)

    def use_nonce(self, nonce: str, expires: int) -> bool:
        """True the first time a sign-in link is used, False on replay."""
        try:
            self.x("INSERT INTO used_nonces(nonce,expires) VALUES(?,?)", nonce, expires)
        except sqlite3.IntegrityError:
            return False
        return True

    # --- retention --------------------------------------------------------------------------
    def purge(self) -> None:
        t = now()
        self.x("DELETE FROM sessions WHERE expires<?", t)
        self.x("DELETE FROM used_nonces WHERE expires<?", t)
        for g in self.q("SELECT id FROM guilds"):
            cutoff = t - self.settings(g["id"])["retention_days"] * 86_400
            gid = g["id"]
            with self.tx():
                self.x("DELETE FROM observations WHERE guild_id=? AND at<?", gid, cutoff)
                self.x("DELETE FROM events WHERE guild_id=? AND at<?", gid, cutoff)
                self.x("DELETE FROM contacts WHERE guild_id=? AND last_at<?", gid, cutoff)
                self.x("DELETE FROM reports WHERE guild_id=? AND at<?", gid, cutoff)
                self.x("DELETE FROM alerts WHERE guild_id=? AND created_at<? AND status<>'open'", gid, cutoff)
                self.x("DELETE FROM score_days WHERE guild_id=? AND day<?", gid, day_of(cutoff))
                self.x("DELETE FROM members WHERE guild_id=? AND left_at IS NOT NULL AND left_at<? "
                       "AND status NOT IN ('watch','actioned')", gid, cutoff)
        self.x("DELETE FROM daily WHERE day<?", day_of(t - 400 * 86_400))
        self.x("DELETE FROM feedback WHERE at<?", t - 400 * 86_400)

    def forget_guild(self, gid: int) -> None:
        """Admin asked Guard to erase this server's data (also used when the bot is removed for good)."""
        with self.tx():
            for table, col in (("observations", "guild_id"), ("events", "guild_id"), ("contacts", "guild_id"),
                               ("reports", "guild_id"), ("alerts", "guild_id"), ("score_days", "guild_id"),
                               ("members", "guild_id"), ("daily", "guild_id"), ("network", "guild_id"),
                               ("feedback", "guild_id"), ("guilds", "id")):
                self.x(f"DELETE FROM {table} WHERE {col}=?", gid)


def is_minor_row(row: sqlite3.Row | dict[str, Any]) -> bool:
    age = row["self_age"]
    return (age is not None and age < 18) or row["role_age"] == "minor"


def is_adult_row(row: sqlite3.Row | dict[str, Any]) -> bool:
    age = row["self_age"]
    return (age is not None and age >= 18) or (age is None and row["role_age"] == "adult")
