"""Pocket app data: what Guildward users check and report, pooled per account across all users.

Who checked or reported is stored only as a keyed hash (`who`), so the table can't be read as "kid X
reported Y". Watches are the exception: they hold the kid's ID because we must DM them. Message text is
never stored; off-platform handles and scripts are stored only as keyed hashes (intel/linking.py).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
from typing import Any

from guildward.core.i18n import Lang, register, t
from guildward.core.models import Confidence, Kind, Signal, build_verdict
from guildward.core.snowflake import age_days
from guildward.guard.store import Store, day_of, now
from guildward.intel import crowd, linking
from guildward.intel.behavior import STAGE_OF, STAGE_ORDER, Stage

DAY = 86_400
MEMORY_DAYS = 14
MAX_REPORTS_PER_DAY = 10
COMMON_BAND_USERS = 5
RANK = {"none": 0, "cleared": 0, "watch": 1, "flagged": 2, "confirmed": 3}
DEFAULT_PREFS: dict[str, bool] = {"watch_alerts": True, "memory": True, "server_alerts": True, "weekly": False}
_LATE = {Stage.ISOLATION.value, Stage.SEXUAL.value, Stage.MEETING.value, Stage.COERCION.value}

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts(
  user_id INTEGER PRIMARY KEY, username TEXT NOT NULL DEFAULT '', display TEXT, avatar TEXT,
  first_seen INTEGER NOT NULL, last_seen INTEGER NOT NULL, profile_at INTEGER, deleted_at INTEGER,
  flag TEXT NOT NULL DEFAULT 'none', flag_by INTEGER, flag_at INTEGER, auto_flag TEXT NOT NULL DEFAULT 'none',
  score INTEGER NOT NULL DEFAULT 0, level TEXT NOT NULL DEFAULT 'green');
CREATE TABLE IF NOT EXISTS account_checks(
  user_id INTEGER NOT NULL, who TEXT NOT NULL, kind TEXT NOT NULL, level TEXT NOT NULL, at INTEGER NOT NULL,
  PRIMARY KEY(user_id, who, kind));
CREATE TABLE IF NOT EXISTS account_reports(
  user_id INTEGER NOT NULL, who TEXT NOT NULL, reason TEXT NOT NULL, weight REAL NOT NULL, at INTEGER NOT NULL,
  PRIMARY KEY(user_id, who));
CREATE TABLE IF NOT EXISTS name_history(user_id INTEGER NOT NULL, name TEXT NOT NULL, at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS marks(
  kind TEXT NOT NULL, key TEXT NOT NULL, user_id INTEGER NOT NULL, grp TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL, at INTEGER NOT NULL, PRIMARY KEY(kind, key, user_id, grp));
CREATE INDEX IF NOT EXISTS marks_user ON marks(user_id);
CREATE TABLE IF NOT EXISTS pair_signals(
  pair TEXT NOT NULL, ev TEXT NOT NULL, code TEXT NOT NULL, stage TEXT, at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS pair_at ON pair_signals(pair, at);
CREATE TABLE IF NOT EXISTS watches(
  kid_id INTEGER NOT NULL, user_id INTEGER NOT NULL, since INTEGER NOT NULL, last_at INTEGER NOT NULL,
  state TEXT NOT NULL DEFAULT 'none', deleted_seen INTEGER NOT NULL DEFAULT 0, notified_at INTEGER,
  PRIMARY KEY(kid_id, user_id));
CREATE TABLE IF NOT EXISTS pocket_users(
  user_id INTEGER PRIMARY KEY, lang TEXT NOT NULL DEFAULT 'en', joined_at INTEGER NOT NULL, last_at INTEGER NOT NULL,
  prefs TEXT NOT NULL DEFAULT '{}', adult_id INTEGER, dm TEXT NOT NULL DEFAULT 'unknown',
  oauth TEXT, servers TEXT NOT NULL DEFAULT '[]', scanned_at INTEGER, weekly_at INTEGER);
CREATE TABLE IF NOT EXISTS pair_codes(code TEXT PRIMARY KEY, kid_id INTEGER NOT NULL, expires INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS server_checks(
  guild_id INTEGER NOT NULL, who TEXT NOT NULL, level TEXT NOT NULL, at INTEGER NOT NULL, PRIMARY KEY(guild_id, who));
"""


def _rank_level(level: str) -> int:
    return {"green": 0, "yellow": 1, "red": 2}.get(level, 0)


class Pocket:
    def __init__(self, store: Store) -> None:
        self.store = store
        store.db.executescript(SCHEMA)
        key = store.meta("pocket_secret")
        if not key:
            key = secrets.token_hex(32)
            store.set_meta("pocket_secret", key)
        self.secret = bytes.fromhex(key)

    def _h(self, raw: str) -> str:
        return hmac.new(self.secret, raw.encode(), hashlib.sha256).hexdigest()[:32]

    def who(self, uid: int) -> str:
        return self._h(f"u:{uid}")

    def pair(self, kid: int, other: str | int) -> str:
        # Prefixed by the kid's hash so one kid's memory can be erased without knowing who they talked to.
        return self.who(kid)[:16] + self._h(f"p:{kid}:{other}")[:16]

    # --- users ------------------------------------------------------------------------------
    def user(self, uid: int) -> sqlite3.Row | None:
        return self.store.one("SELECT * FROM pocket_users WHERE user_id=?", uid)

    def touch_user(self, uid: int, lang: str) -> None:
        self.store.x("""INSERT INTO pocket_users(user_id,lang,joined_at,last_at) VALUES(?,?,?,?)
                        ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang, last_at=excluded.last_at""",
                     uid, lang, now(), now())

    def prefs(self, uid: int) -> dict[str, bool]:
        row = self.user(uid)
        return {**DEFAULT_PREFS, **(json.loads(row["prefs"]) if row else {})}

    def set_pref(self, uid: int, key: str, value: bool) -> dict[str, bool]:
        if key not in DEFAULT_PREFS:
            raise ValueError(key)
        p = {**self.prefs(uid), key: bool(value)}
        self.store.x("UPDATE pocket_users SET prefs=? WHERE user_id=?", json.dumps(p), uid)
        if key == "watch_alerts" and not value:
            self.store.x("DELETE FROM watches WHERE kid_id=?", uid)
        if key == "memory" and not value:
            self.store.x("DELETE FROM pair_signals WHERE pair LIKE ?", self.who(uid)[:16] + "%")
        return p

    def set_dm(self, uid: int, state: str) -> None:
        self.store.x("UPDATE pocket_users SET dm=? WHERE user_id=?", state, uid)

    def forget(self, uid: int) -> None:
        """A kid asked us to erase what we hold about them (their checks and reports stay out of counts)."""
        who = self.who(uid)
        touched = {r["user_id"] for r in self.store.q(
            "SELECT user_id FROM account_reports WHERE who=? UNION SELECT user_id FROM account_checks WHERE who=?",
            who, who)}
        with self.store.tx():
            # Only this kid's own rows: watches other kids hold on them must survive, or an abuser could
            # silence the alerts about himself by running forget.
            self.store.x("DELETE FROM watches WHERE kid_id=?", uid)
            self.store.x("DELETE FROM account_checks WHERE who=?", who)
            self.store.x("DELETE FROM account_reports WHERE who=?", who)
            self.store.x("DELETE FROM server_checks WHERE who=?", who)
            self.store.x("DELETE FROM pair_codes WHERE kid_id=?", uid)
            self.store.x("DELETE FROM pair_signals WHERE pair LIKE ?", who[:16] + "%")
            self.store.x("UPDATE pocket_users SET adult_id=NULL WHERE adult_id=?", uid)
            self.store.x("DELETE FROM pocket_users WHERE user_id=?", uid)
        for account in touched:
            self.refresh(account)

    # --- accounts ---------------------------------------------------------------------------
    def see_account(self, uid: int, username: str, display: str | None, avatar: str | None) -> None:
        row = self.store.one("SELECT username, display FROM accounts WHERE user_id=?", uid)
        t0 = now()
        deleted = username.startswith("deleted_user_")
        if deleted and row:  # keep the last real name so the kid's alert says who it was
            self.store.x("UPDATE accounts SET profile_at=?, deleted_at=COALESCE(deleted_at, ?) WHERE user_id=?",
                         t0, t0, uid)
            return
        self.store.x("""INSERT INTO accounts(user_id,username,display,avatar,first_seen,last_seen,profile_at,deleted_at)
                        VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,
                        display=excluded.display, avatar=excluded.avatar, last_seen=excluded.last_seen,
                        profile_at=excluded.profile_at,
                        deleted_at=COALESCE(accounts.deleted_at, excluded.deleted_at)""",
                     uid, username, display, avatar, t0, t0, t0, t0 if deleted else None)
        if row and not deleted and (row["username"], row["display"]) != (username, display):
            self.store.x("INSERT INTO name_history(user_id,name,at) VALUES(?,?,?)", uid,
                         f"{row['display'] or ''}@{row['username']}", t0)
        if not deleted:
            for m in linking.profile_marks(username, display, avatar):
                self._mark(uid, m, "profile")

    def record_check(self, kid: int, account: int, kind: str, level: str) -> None:
        """kind: person | message. Keeps the worst level each checker ever got for this account."""
        if kid == account:
            return
        who = self.who(kid)
        row = self.store.one("SELECT level FROM account_checks WHERE user_id=? AND who=? AND kind=?", account, who, kind)
        if row is None or _rank_level(level) > _rank_level(row["level"]):
            self.store.x("""INSERT INTO account_checks(user_id,who,kind,level,at) VALUES(?,?,?,?,?)
                            ON CONFLICT(user_id,who,kind) DO UPDATE SET level=excluded.level, at=excluded.at""",
                         account, who, kind, level, now())
        if self.prefs(kid)["watch_alerts"]:
            state = self.level_of(account)
            self.store.x("""INSERT INTO watches(kid_id,user_id,since,last_at,state) VALUES(?,?,?,?,?)
                            ON CONFLICT(kid_id,user_id) DO UPDATE SET last_at=excluded.last_at""",
                         kid, account, now(), now(), state)
        self.store.bump(0, "pocket.checked_account")

    def reporter_weight(self, kid: int) -> float:
        return crowd.reporter_weight(age_days(kid), self.level_of(kid))

    def report(self, kid: int, account: int, reason: str) -> bool:
        if kid == account or reason not in crowd.REPORT_REASONS:
            return False
        if self.store.val("SELECT COUNT(*) FROM account_reports WHERE who=? AND at>=?", self.who(kid),
                          now() - DAY) >= MAX_REPORTS_PER_DAY:
            return False  # one person can't mass-report their way into flags
        weight = self.reporter_weight(kid)
        self.store.x("""INSERT INTO account_reports(user_id,who,reason,weight,at) VALUES(?,?,?,?,?)
                        ON CONFLICT(user_id,who) DO UPDATE SET reason=excluded.reason, at=excluded.at""",
                     account, self.who(kid), reason, weight, now())
        self.store.bump(0, "pocket.report")
        self.refresh(account)
        return True

    def _mark(self, uid: int, m: linking.Mark, source: str, grp: str = "") -> None:
        self.store.x("""INSERT INTO marks(kind,key,user_id,grp,source,at) VALUES(?,?,?,?,?,?)
                        ON CONFLICT(kind,key,user_id,grp) DO UPDATE SET at=excluded.at""",
                     m.kind, linking.mark_key(self.secret, m), uid, grp if m.kind == "script" else "", source, now())

    def record_marks(self, uid: int, text: str, source: str) -> int:
        """Remember handles/scripts a risky message pushed, hashed, so alts pushing the same ones link up."""
        marks = linking.extract_marks(text)
        grp = secrets.token_hex(6)  # script bands only match within one message pair, never pooled per account
        for m in marks:
            self._mark(uid, m, source, grp)
        return len(marks)

    def _matches(self, marks: list[tuple[str, str, str]], exclude: int | None) -> list[tuple[int, str]]:
        """marks: (kind, key, own group). Returns (other account, kind) for every link found."""
        found: set[tuple[int, str]] = set()
        bands: dict[tuple[str, int, str], int] = {}  # (own group, other user, other group) -> equal bands
        for kind, key, grp in marks:
            rows = self.store.q("SELECT user_id, grp FROM marks WHERE kind=? AND key=? AND user_id IS NOT ? "
                                "LIMIT 200", kind, key, exclude)
            if kind == "script" and len({r["user_id"] for r in rows}) > COMMON_BAND_USERS:
                continue  # a band many accounts share is a common phrase, not a fingerprint
            for r in rows:
                if kind != "script":
                    found.add((r["user_id"], kind))
                    continue
                k = (grp, r["user_id"], r["grp"])
                bands[k] = bands.get(k, 0) + 1
                if bands[k] >= linking.SCRIPT_MATCH_BANDS:
                    found.add((r["user_id"], "script"))
        return sorted(found)

    def links_of(self, uid: int) -> list[crowd.Link]:
        marks = [(r["kind"], r["key"], r["grp"]) for r in
                 self.store.q("SELECT kind, key, grp FROM marks WHERE user_id=?", uid)]
        return [crowd.Link(kind, other, self.level_of(other)) for other, kind in self._matches(marks, uid)]

    def match_text(self, text: str) -> list[tuple[str, int, str]]:
        """Handles/scripts in a message that flagged accounts pushed before: (kind, account, level)."""
        marks = [(m.kind, linking.mark_key(self.secret, m), "new") for m in linking.extract_marks(text)]
        out = []
        for uid, kind in self._matches(marks, None):
            level = self.level_of(uid)
            if level == "confirmed":  # auto-flags never propagate by themselves (framing via planted handles)
                out.append((kind, uid, level))
        return out

    def facts(self, uid: int) -> crowd.CrowdFacts:
        s, t0 = self.store, now()
        row = s.one("SELECT flag, deleted_at FROM accounts WHERE user_id=?", uid)
        reports = tuple(crowd.Report(r["weight"], r["at"], r["reason"])
                        for r in s.q("SELECT weight, at, reason FROM account_reports WHERE user_id=?", uid))
        return crowd.CrowdFacts(
            user_id=uid, now=t0,
            checkers=s.val("SELECT COUNT(DISTINCT who) FROM account_checks WHERE user_id=?", uid),
            red_checkers=s.val("SELECT COUNT(DISTINCT who) FROM account_checks WHERE user_id=? AND kind='message' "
                               "AND level='red'", uid),
            reports=reports,
            flag=row["flag"] if row else "none",
            network_guilds=len(s.network_flags(uid)),
            links=tuple(self.links_of(uid)),
            deleted=bool(row and row["deleted_at"]),
            name_changes_30d=s.val("SELECT COUNT(*) FROM name_history WHERE user_id=? AND at>=?", uid, t0 - 30 * DAY),
        )

    def refresh(self, uid: int) -> crowd.CrowdFacts:
        f = self.facts(uid)
        auto = crowd.auto_flag(f)
        v = build_verdict(Kind.PERSON, crowd.crowd_signals(f), base=0, confidence=Confidence.MEDIUM)
        self.store.x("""INSERT INTO accounts(user_id,first_seen,last_seen,auto_flag,score,level) VALUES(?,?,?,?,?,?)
                        ON CONFLICT(user_id) DO UPDATE SET auto_flag=excluded.auto_flag, score=excluded.score,
                        level=excluded.level""", uid, now(), now(), auto if auto in RANK else "none", v.score,
                     v.level.value)
        return f

    def level_of(self, uid: int) -> str:
        """Effective flag: the owner's decision wins over the automatic one; Guard child-safety bans floor it."""
        row = self.store.one("SELECT flag, auto_flag FROM accounts WHERE user_id=?", uid)
        level = (row["flag"] if row["flag"] != "none" else row["auto_flag"]) if row else "none"
        if level == "cleared":
            return level  # the owner reviewed it; one admin's bans can't override that
        network = len(self.store.network_flags(uid))
        if network >= 2:
            return "confirmed"
        if network == 1 and RANK[level] < RANK["flagged"]:
            return "flagged"
        return level

    def account_signals(self, uid: int) -> list[Signal]:
        return crowd.crowd_signals(self.refresh(uid))

    # --- pattern memory (per kid + sender, or kid + conversation) ----------------------------
    def remember(self, kid: int, other: str | int, codes: list[str], event: str | int) -> None:
        """event: the checked message (id or content hash), so checking it twice isn't two warning signs."""
        if not codes or not self.prefs(kid)["memory"]:
            return
        pair, ev, t0 = self.pair(kid, other), self._h(f"e:{event}")[:16], now()
        if self.store.val("SELECT 1 FROM pair_signals WHERE pair=? AND ev=?", pair, ev, default=0):
            return
        with self.store.tx():
            for c in codes:
                st = STAGE_OF.get(c)
                self.store.x("INSERT INTO pair_signals(pair,ev,code,stage,at) VALUES(?,?,?,?,?)", pair, ev, c,
                             st.value if st else None, t0)

    def pattern_signal(self, kid: int, other: str | int, lang: Lang) -> Signal | None:
        rows = self.store.q("SELECT code, stage, ev FROM pair_signals WHERE pair=? AND at>=?",
                            self.pair(kid, other), now() - MEMORY_DAYS * DAY)
        times = {r["ev"] for r in rows}
        if len(times) < 2:
            return None
        stages = sorted({r["stage"] for r in rows if r["stage"]}, key=lambda s: STAGE_ORDER.index(Stage(s)))
        k = len(stages)
        weight = min(40, 10 + 10 * max(0, k - 1))
        names = ", ".join(t(f"stage.{s}", lang) for s in stages) or t("pocket.no_stage", lang)
        return Signal("pocket.pattern", weight, {"n": len(times), "stages": names},
                      severe=k >= 3 and bool(set(stages) & _LATE))

    # --- watches ----------------------------------------------------------------------------
    def watches_to_check(self, limit: int = 500) -> list[sqlite3.Row]:
        return self.store.q("""SELECT w.*, a.deleted_at, a.username, a.display FROM watches w
                               LEFT JOIN accounts a ON a.user_id=w.user_id
                               LEFT JOIN pocket_users u ON u.user_id=w.kid_id
                               WHERE COALESCE(u.dm, 'unknown')<>'blocked'
                               ORDER BY w.notified_at IS NOT NULL, w.last_at DESC LIMIT ?""", limit)

    def watch_news(self, w: sqlite3.Row) -> str | None:
        """'flagged' | 'confirmed' | 'deleted' when this watch has news for the kid, else None."""
        level = self.level_of(w["user_id"])
        if RANK[level] > RANK[w["state"]] and RANK[level] >= RANK["flagged"]:
            return level
        if w["deleted_at"] and not w["deleted_seen"]:
            risky = self.store.val("SELECT 1 FROM account_checks WHERE user_id=? AND who=? AND level<>'green'",
                                   w["user_id"], self.who(w["kid_id"]), default=0)
            if not risky:
                self.store.x("UPDATE watches SET deleted_seen=1 WHERE kid_id=? AND user_id=?", w["kid_id"],
                             w["user_id"])
            return "deleted" if risky else None
        return None

    def watch_done(self, kid: int, uid: int, news: str) -> None:
        state = news if news in RANK else self.level_of(uid)
        self.store.x("UPDATE watches SET state=?, notified_at=?, deleted_seen=MAX(deleted_seen, ?) WHERE kid_id=? "
                     "AND user_id=?", state, now(), int(news == "deleted"), kid, uid)
        self.store.bump(0, "pocket.watch_alert")

    def stale_profiles(self, limit: int = 40) -> list[int]:
        """Watched accounts whose public profile we haven't re-read in a day (name changes, deletions)."""
        return [r["user_id"] for r in self.store.q(
            """SELECT DISTINCT w.user_id FROM watches w LEFT JOIN accounts a ON a.user_id=w.user_id
               WHERE a.deleted_at IS NULL AND (a.profile_at IS NULL OR a.profile_at<?) LIMIT ?""",
            now() - DAY, limit)]

    # --- trusted adult ----------------------------------------------------------------------
    def new_pair_code(self, kid: int) -> str:
        code = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
        self.store.x("DELETE FROM pair_codes WHERE kid_id=? OR expires<?", kid, now())
        self.store.x("INSERT INTO pair_codes(code,kid_id,expires) VALUES(?,?,?)", code, kid, now() + 1800)
        return code

    def claim_code(self, code: str, adult: int) -> int | None:
        row = self.store.one("SELECT kid_id FROM pair_codes WHERE code=? AND expires>=?", code.strip().upper(), now())
        if row is None or row["kid_id"] == adult:
            return None
        self.store.x("DELETE FROM pair_codes WHERE code=?", code.strip().upper())
        self.store.x("UPDATE pocket_users SET adult_id=? WHERE user_id=?", adult, row["kid_id"])
        return row["kid_id"]

    def adult_of(self, kid: int) -> int | None:
        row = self.user(kid)
        return row["adult_id"] if row else None

    def remove_adult(self, kid: int) -> None:
        self.store.x("UPDATE pocket_users SET adult_id=NULL WHERE user_id=?", kid)

    # --- servers ----------------------------------------------------------------------------
    def record_server_check(self, kid: int, gid: int, level: str) -> None:
        self.store.x("""INSERT INTO server_checks(guild_id,who,level,at) VALUES(?,?,?,?)
                        ON CONFLICT(guild_id,who) DO UPDATE SET level=excluded.level, at=excluded.at""",
                     gid, self.who(kid), level, now())

    def server_red_checkers(self, gid: int) -> int:
        return self.store.val("SELECT COUNT(*) FROM server_checks WHERE guild_id=? AND level='red'", gid)

    def set_oauth(self, kid: int, refresh_token: str | None) -> None:
        self.store.x("UPDATE pocket_users SET oauth=? WHERE user_id=?", refresh_token, kid)

    def save_scan(self, kid: int, servers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Store the latest scan; returns servers that are new since the previous scan."""
        row = self.user(kid)
        before = {s["id"] for s in json.loads(row["servers"])} if row and row["scanned_at"] else None
        self.store.x("UPDATE pocket_users SET servers=?, scanned_at=? WHERE user_id=?", json.dumps(servers), now(), kid)
        return [] if before is None else [s for s in servers if s["id"] not in before]

    def scans_due(self, limit: int = 50) -> list[sqlite3.Row]:
        return self.store.q("SELECT * FROM pocket_users WHERE oauth IS NOT NULL AND (scanned_at IS NULL OR "
                            "scanned_at<?) LIMIT ?", now() - DAY, limit)

    def weekly_due(self, limit: int = 100) -> list[sqlite3.Row]:
        rows = self.store.q("SELECT * FROM pocket_users WHERE dm<>'blocked' AND (weekly_at IS NULL OR weekly_at<?) "
                            "LIMIT ?", now() - 7 * DAY, limit * 4)
        return [r for r in rows if {**DEFAULT_PREFS, **json.loads(r["prefs"])}["weekly"]][:limit]

    def weekly_done(self, kid: int) -> None:
        self.store.x("UPDATE pocket_users SET weekly_at=? WHERE user_id=?", now(), kid)

    def weekly_facts(self, kid: int) -> dict[str, int]:
        since = now() - 7 * DAY
        return {
            "checks": self.store.val("SELECT COUNT(*) FROM account_checks WHERE who=? AND at>=?", self.who(kid), since),
            "flagged": self.store.val("SELECT COUNT(*) FROM watches WHERE kid_id=? AND state IN ('flagged','confirmed')",
                                      kid),
            "servers": len(json.loads((self.user(kid) or {"servers": "[]"})["servers"])),
            "risky_servers": sum(1 for s in json.loads((self.user(kid) or {"servers": "[]"})["servers"])
                                 if s.get("level") != "green"),
        }

    # --- owner ------------------------------------------------------------------------------
    def owner_accounts(self, status: str = "review", limit: int = 200) -> dict[str, Any]:
        where = {
            "review": "a.flag='none' AND a.auto_flag IN ('watch','flagged')",
            "flagged": "((a.flag='none' AND a.auto_flag='flagged') OR a.flag='flagged')",
            "confirmed": "a.flag='confirmed'",
            "cleared": "a.flag='cleared'",
            "all": "1=1",
        }
        if status not in where:
            status = "review"
        counts = {k: self.store.val(f"SELECT COUNT(*) FROM accounts a WHERE {w}") for k, w in where.items()
                  if k != "all"}
        rows = self.store.q(f"""SELECT a.* FROM accounts a WHERE {where[status]}
                                AND (EXISTS(SELECT 1 FROM account_reports r WHERE r.user_id=a.user_id)
                                     OR EXISTS(SELECT 1 FROM account_checks c WHERE c.user_id=a.user_id)
                                     OR a.flag<>'none')
                                ORDER BY a.score DESC, a.last_seen DESC LIMIT ?""", limit)
        return {"counts": counts, "accounts": [self._owner_row(r) for r in rows]}

    def _owner_row(self, r: sqlite3.Row) -> dict[str, Any]:
        f = self.facts(r["user_id"])
        reasons: dict[str, int] = {}
        for rep in f.reports:
            reasons[rep.reason] = reasons.get(rep.reason, 0) + 1
        names = {x["user_id"]: x["username"] for x in self.store.q(
            f"SELECT user_id, username FROM accounts WHERE user_id IN ({','.join('?' * len(f.links)) or 'NULL'})",
            *[ln.other_id for ln in f.links])}
        avatar = (f"https://cdn.discordapp.com/avatars/{r['user_id']}/{r['avatar']}.png?size=64"
                  if r["avatar"] else None)
        return {
            "id": str(r["user_id"]), "name": r["username"] or str(r["user_id"]), "avatar": avatar,
            "created_at": int((r["user_id"] >> 22) / 1000 + 1_420_070_400), "flag": r["flag"],
            "auto_flag": r["auto_flag"], "score": r["score"], "level": r["level"], "checkers": f.checkers,
            "red_checkers": f.red_checkers, "reports": len(f.reports),
            "report_score": round(crowd.report_score(f.reports, f.now), 2), "reasons": reasons,
            "network": f.network_guilds,
            "links": [{"kind": ln.kind, "other_id": str(ln.other_id), "other_name": names.get(ln.other_id),
                       "other_flag": ln.other_level} for ln in f.links],
            "last_seen": r["last_seen"], "deleted": bool(r["deleted_at"]),
        }

    def owner_action(self, uid: int, action: str, by: int) -> bool:
        flag = {"confirm": "confirmed", "clear": "cleared", "watch": "watch", "reset": "none"}.get(action)
        if flag is None or self.store.one("SELECT 1 FROM accounts WHERE user_id=?", uid) is None:
            return False
        self.store.x("UPDATE accounts SET flag=?, flag_by=?, flag_at=? WHERE user_id=?", flag, by, now(), uid)
        self.refresh(uid)
        return True

    def stats(self) -> dict[str, int]:
        s, since = self.store, day_of(now() - 7 * DAY)
        week = lambda m: s.val("SELECT SUM(n) FROM daily WHERE guild_id=0 AND metric=? AND day>=?", m, since)  # noqa: E731
        c = self.owner_accounts("review", limit=0)["counts"]
        return {"users": s.val("SELECT COUNT(*) FROM pocket_users"), "accounts": s.val("SELECT COUNT(*) FROM accounts"),
                "reports_7d": week("pocket.report"), "review": c["review"], "flagged": c["flagged"],
                "confirmed": c["confirmed"], "watch_alerts_7d": week("pocket.watch_alert")}

    # --- retention --------------------------------------------------------------------------
    def purge(self) -> None:
        s, t0 = self.store, now()
        with s.tx():
            s.x("DELETE FROM pair_signals WHERE at<?", t0 - MEMORY_DAYS * DAY)
            s.x("DELETE FROM pair_codes WHERE expires<?", t0)
            s.x("DELETE FROM watches WHERE last_at<?", t0 - 60 * DAY)
            s.x("DELETE FROM account_checks WHERE at<?", t0 - 180 * DAY)
            s.x("DELETE FROM server_checks WHERE at<?", t0 - 180 * DAY)
            s.x("DELETE FROM account_reports WHERE at<?", t0 - 365 * DAY)
            s.x("DELETE FROM marks WHERE at<?", t0 - 365 * DAY)
            s.x("DELETE FROM name_history WHERE at<?", t0 - 90 * DAY)
            s.x("""DELETE FROM accounts WHERE flag IN ('none','cleared') AND last_seen<? AND user_id NOT IN
                   (SELECT user_id FROM account_reports) AND user_id NOT IN (SELECT user_id FROM watches)""",
                t0 - 365 * DAY)


register({
    "pocket.pattern": {
        "en": "This is warning sign #{n} from this person in the last two weeks. So far: {stages}.",
        "sv": "Det här är varningstecken nummer {n} från den här personen de senaste två veckorna. Hittills: {stages}.",
    },
    "pocket.no_stage": {"en": "several warning signs", "sv": "flera varningstecken"},
    "pocket.handle_known": {
        "en": "This message pushes a {kind} that an account flagged by Guildward users pushed before.",
        "sv": "Meddelandet skickar vidare till ett {kind} som ett konto som Guildward-användare flaggat har använt förut.",
    },
    "pocket.kind.handle": {"en": "account on another app", "sv": "konto i en annan app"},
    "pocket.kind.payment": {"en": "payment account", "sv": "betalkonto"},
    "pocket.kind.script": {"en": "copy-paste text", "sv": "kopierad text"},
    "pocket.kind.avatar": {"en": "profile picture", "sv": "profilbild"},
    "pocket.kind.name": {"en": "name", "sv": "namn"},
})
