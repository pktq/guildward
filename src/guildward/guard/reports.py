"""Synthesised reports: one person, one server, the whole deployment. Plain dicts in the shapes of
docs/GUARD_API.md, used by the dashboard API and (condensed) by the /guard commands' embeds.

Many data vectors go in: profile, what they said about their age, every observation with who it was
aimed at, grooming stages per contact, reports, moderation, network flags, raids, the structural
audit and how fast moderators react. What comes out is a score, the reasons, plain sentences an
admin can act on, a prediction, and a timeline.
"""

from __future__ import annotations

import json
import math
import statistics
from datetime import UTC, datetime
from typing import Any

import guildward.bot.render  # noqa: F401  (registers the shared confidence.* strings)
from guildward.core.i18n import Lang, register, t
from guildward.core.models import Confidence, Kind, Signal, build_verdict, level_for
from guildward.core.snowflake import age_days, created_at
from guildward.guard.engine import Engine
from guildward.guard.store import is_minor_row, last_days, now
from guildward.intel.audit import Check, GuildFacts, audit_guild, audit_signals
from guildward.intel.behavior import STAGE_ORDER, Stage

SERVER_LIVE_BASE = 20
GRADES = ((15, "A"), (30, "B"), (45, "C"), (65, "D"))


def _saturate(raw: int, cap: int) -> int:
    return round(cap * (1 - math.exp(-raw / 40)))


def server_score(sigs: list[Signal]) -> int:
    """Settings problems and live incidents each saturate (max 35 and 45 points), so one bad week reads as
    D/F without every extra issue pushing a server to a meaningless 100, and fixing things visibly helps."""
    audit = sum(x.weight for x in sigs if x.weight > 0 and x.code.startswith("audit."))
    live = sum(x.weight for x in sigs if x.weight > 0 and not x.code.startswith("audit."))
    bonus = sum(x.weight for x in sigs if x.weight < 0)
    return max(0, min(100, SERVER_LIVE_BASE + _saturate(audit, 35) + _saturate(live, 45) + bonus))


def iso(ts: int | None) -> str | None:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None


def jump(gid: int, cid: int | None, mid: int | None) -> str | None:
    return f"https://discord.com/channels/{gid}/{cid}/{mid}" if cid and mid else None


def grade(score: int) -> str:
    return next((g for limit, g in GRADES if score < limit), "F")


def name_of(row: Any, uid: int | None = None) -> str:
    if row is None:
        return f"#{uid}" if uid else "?"
    disp, user = row["display"], row["username"]
    return f"{disp} (@{user})" if disp and disp != user else f"@{user}"


def sig_text(code: str, params: dict[str, Any], lang: Lang) -> str:
    try:
        return t(code, lang, **params)
    except (KeyError, IndexError):
        return t(code, lang)


def signal_dict(s: Signal | dict[str, Any], lang: Lang, at: int | None = None) -> dict[str, Any]:
    if isinstance(s, Signal):
        code, weight, params, severe = s.code, s.weight, dict(s.params), s.severe
    else:
        code, weight, params, severe = s["code"], s["weight"], s.get("params", {}), s.get("severe", False)
    return {"code": code, "weight": weight, "severe": severe, "text": sig_text(code, params, lang), "at": iso(at)}


class Reports:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.store = engine.store

    # --- small shapes -----------------------------------------------------------------------
    def user_ref(self, gid: int, uid: int | None) -> dict[str, Any] | None:
        if not uid:
            return None
        row = self.store.member(gid, uid)
        return {"id": str(uid), "name": name_of(row, uid), "avatar": row["avatar"] if row else None,
                "minor": bool(row) and is_minor_row(row)}

    def member_row(self, row: Any, lang: Lang) -> dict[str, Any]:
        gid, uid = row["guild_id"], row["user_id"]
        flags = []
        days = age_days(uid)
        if days < 30:
            flags.append("new_account")
        if not row["has_avatar"]:
            flags.append("no_avatar")
        minor = is_minor_row(row)
        if minor:
            flags.append("minor")
        if row["raid_join"]:
            flags.append("raid")
        if row["status"] in ("watch", "trusted"):
            flags.append(row["status"])
        if self.store.reporters(gid, uid):
            flags.append("reported")
        if self.store.network_flags(uid, exclude_guild=gid):
            flags.append("network")
        top = row["top_code"]
        codes = set(json.loads(row["codes"] or "[]"))
        if codes & {"member.adult_minor", "member.many_minors"}:
            flags.append("adult_contacting_minors")
        if "member.escalation" in codes:
            flags.append("escalating")
        before = self.store.score_days_ago(gid, uid, 7)
        status = "left" if row["left_at"] else row["status"]
        return {
            "id": str(uid), "name": name_of(row), "avatar": row["avatar"], "score": row["score"],
            "level": row["level"], "status": status, "joined_at": iso(row["joined_at"]),
            "account_age_days": int(days), "self_age": row["self_age"], "minor": minor, "flags": flags,
            "trend": row["score"] - before if before is not None else 0, "last_seen": iso(row["last_msg_at"]),
            "top_signal": sig_text(top, json.loads(row["top_params"] or "{}"), lang) if top else None,
        }

    def alert_dict(self, row: Any, lang: Lang) -> dict[str, Any]:
        gid = row["guild_id"]
        params = json.loads(row["params"])
        signals = json.loads(row["signals"])
        title = t(row["title"], lang, **{k: v for k, v in params.items() if k != "to_minor"})
        if params.get("to_minor") and row["title"] not in ("alert.t.scam", "alert.t.spam"):
            title += t("alert.to_minor_suffix", lang)
        user, target = self.user_ref(gid, row["user_id"]), self.user_ref(gid, row["target_id"])
        top = [sig_text(s["code"], s.get("params", {}), lang) for s in signals if s["weight"] > 0][:2]
        summary = t(f"alert.s.{row['kind']}", lang, user=user["name"] if user else "?",
                    target=target["name"] if target else t("alert.someone", lang),
                    channel=params.get("channel") or "?", n=params.get("n", 0))
        if top:
            summary += " " + " ".join(top)
        return {
            "id": row["id"], "kind": row["kind"], "level": row["level"], "score": row["score"], "title": title,
            "summary": summary, "quote": self.engine.quotes.get(row["id"]), "user": user, "target": target,
            "signals": [signal_dict(s, lang) for s in signals],
            "jump_url": jump(gid, row["channel_id"], row["message_id"]), "status": row["status"],
            "created_at": iso(row["created_at"]), "resolved_by": row["resolved_by_name"], "action": row["action"],
            "assigned": {"id": str(row["assigned_to"]), "name": row["assigned_name"] or "?", "avatar": None}
            if row["assigned_to"] else None,
            "note": row["note"],
        }

    def alerts(self, gid: int, lang: Lang, *, status: str = "open", limit: int = 50) -> list[dict[str, Any]]:
        where = "AND status='open'" if status == "open" else ""
        rows = self.store.q(f"SELECT * FROM alerts WHERE guild_id=? {where} ORDER BY id DESC LIMIT ?", gid, limit)
        return [self.alert_dict(r, lang) for r in rows]

    # --- members ----------------------------------------------------------------------------
    def members(self, gid: int, lang: Lang, *, filter: str = "all", sort: str = "risk", q: str = "",
                limit: int = 100) -> dict[str, Any]:
        where, args = ["guild_id=?", "is_bot=0"], [gid]
        if filter == "at_risk":
            where.append("level<>'green'")
        elif filter == "minors":
            where.append("((self_age IS NOT NULL AND self_age<18) OR role_age='minor')")
        elif filter == "watch":
            where.append("status='watch'")
        elif filter == "new":
            where.append("joined_at>=?")
            args.append(now() - 7 * 86_400)
        if filter != "watch" and not q:
            where.append("left_at IS NULL")
        if q:
            where.append("(username LIKE ? OR display LIKE ? OR CAST(user_id AS TEXT)=?)")
            args += [f"%{q}%", f"%{q}%", q]
        order = {"risk": "score DESC, last_msg_at DESC", "recent": "COALESCE(joined_at,0) DESC",
                 "name": "COALESCE(display, username) COLLATE NOCASE"}.get(sort, "score DESC")
        sql_where = " AND ".join(where)
        total = self.store.val(f"SELECT COUNT(*) FROM members WHERE {sql_where}", *args)
        rows = self.store.q(f"SELECT * FROM members WHERE {sql_where} ORDER BY {order} LIMIT ?", *args, limit)
        return {"members": [self.member_row(r, lang) for r in rows], "total": total}

    def person(self, gid: int, uid: int, lang: Lang) -> dict[str, Any] | None:
        s = self.store
        scored = self.engine.rescore(gid, uid)
        row = s.member(gid, uid)
        if scored is None or row is None:
            return None
        v, _, pred = scored
        snap = self.engine.snapshot(gid, uid)
        assert snap is not None
        member = self.member_row(row, lang) | {
            "username": row["username"], "account_created": iso(int(created_at(uid).timestamp())),
            "left_at": iso(row["left_at"]), "invite_code": row["invite_code"], "roles": json.loads(row["roles"]),
        }
        obs = s.observations(gid, uid, now() - 90 * 86_400)
        risky = [o for o in obs if o.weight > 0]
        targets = {o.target_id for o in risky if o.target_id}
        minor_targets = {o.target_id for o in risky if o.target_id and o.target_minor}
        all_contacts = s.contacts_of(gid, uid, 200)
        events = s.events_of(gid, uid, 200)
        mod_actions = sum(1 for e in events if e["kind"] == "action")
        network = s.network_flags(uid, exclude_guild=gid)
        flagged_msgs = len({o.message_id for o in risky if o.message_id})

        summary = [t("rep.p.account", lang, days=int(age_days(uid)))]
        if row["joined_at"]:
            joined_days = max(0, (now() - row["joined_at"]) // 86_400)
            key = "rep.p.joined_today" if joined_days == 0 else "rep.p.joined"
            summary.append(t(key, lang, days=joined_days))
            if row["invite_code"]:
                summary.append(t("rep.p.invite", lang, invite=row["invite_code"]))
        if row["self_age"] is not None:
            summary.append(t("rep.p.age_said", lang, age=row["self_age"]))
        elif row["role_age"]:
            summary.append(t(f"rep.p.role_{row['role_age']}", lang))
        summary.append(t("rep.p.activity", lang, msgs=row["msg_count"], targets=len(all_contacts)))
        if flagged_msgs:
            summary.append(t("rep.p.flagged", lang, n=flagged_msgs, targets=len(targets), minors=len(minor_targets)))
        if snap.reporters:
            summary.append(t("rep.p.reports", lang, n=snap.reporters))
        if network:
            summary.append(t("rep.p.network", lang, n=len(network)))
        if mod_actions:
            summary.append(t("rep.p.mod_actions", lang, n=mod_actions))
        if row["status"] in ("watch", "trusted", "actioned"):
            summary.append(t(f"rep.p.status_{row['status']}", lang))
        if not risky and not snap.reporters and not network:
            summary.append(t("rep.p.clean", lang))

        contacts = []
        for c in all_contacts[:15]:
            stages = sorted(json.loads(c["stages"]), key=lambda x: STAGE_ORDER.index(Stage(x)))
            k, minor = len(stages), is_minor_row(c)
            late = bool(set(stages) & {"isolation", "sexual", "meeting", "coercion"})
            level = "red" if k >= 3 or (minor and late and k >= 2) else "yellow" if k else "green"
            contacts.append({"user": self.user_ref(gid, c["target_id"]), "messages": c["msgs"],
                             "stages": [t(f"stage.{x}", lang) for x in stages], "level": level,
                             "last_at": iso(c["last_at"])})

        timeline: list[dict[str, Any]] = []
        for o in risky[-80:]:
            text = t(f"label.{o.code}", lang, **o.params) if o.code != "msg.isolation" else \
                t("label.msg.isolation", lang, app=o.params.get("app", "?"))
            if o.target_id:
                text += t("tl.to_minor" if o.target_minor else "tl.to_member", lang,
                          name=name_of(s.member(gid, o.target_id), o.target_id))
            if o.deleted:
                text += t("tl.deleted", lang)
            timeline.append({"at": iso(o.at), "kind": "signal", "text": text,
                             "level": level_for(o.weight + 10).value, "jump_url": jump(gid, o.channel_id, o.message_id)})
        for e in events:
            data = json.loads(e["data"])
            kind = e["kind"]
            text = t(f"tl.{kind}", lang, **{k: (v if v is not None else "?") for k, v in data.items()})
            api_kind = {"age_said": "signal", "deleted_flagged": "signal", "reported": "report", "warned": "action",
                        "action": "action", "status": "action"}.get(kind, kind)
            timeline.append({"at": iso(e["at"]), "kind": api_kind, "text": text,
                             "level": "yellow" if kind in ("reported", "deleted_flagged") else None, "jump_url": None})
        for a in s.q("SELECT * FROM alerts WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 30", gid, uid):
            timeline.append({"at": iso(a["created_at"]), "kind": "alert", "text": self.alert_dict(a, lang)["title"],
                             "level": a["level"], "jump_url": jump(gid, a["channel_id"], a["message_id"])})
            if a["note"]:
                timeline.append({"at": iso(a["resolved_at"] or a["created_at"]), "kind": "note",
                                 "text": t("tl.alert_note", lang, id=a["id"], by=a["resolved_by_name"] or "?",
                                           note=a["note"]), "level": None, "jump_url": None})
        timeline.sort(key=lambda x: x["at"] or "", reverse=True)

        days = last_days(30)
        msgs_by_day = {d: 0 for d in days}
        flagged_by_day = {d: 0 for d in days}
        for o in risky:
            d = datetime.fromtimestamp(o.at, UTC).strftime("%Y-%m-%d")
            if d in flagged_by_day:
                flagged_by_day[d] += 1
        score_by_day: dict[str, int] = {}
        for r in s.q("SELECT day, score, msgs FROM score_days WHERE guild_id=? AND user_id=? AND day>=?",
                     gid, uid, days[0]):
            msgs_by_day[r["day"]] = r["msgs"]
            score_by_day[r["day"]] = r["score"]
        scores, last = [], 0
        for d in days:
            last = score_by_day.get(d, last)
            scores.append(last)

        return {
            "member": member,
            "verdict": {"score": v.score, "level": v.level.value,
                        "confidence": t(f"confidence.{v.confidence.name.lower()}", lang),
                        "signals": [signal_dict(x, lang) for x in v.signals]},
            "summary": summary,
            "prediction": {"trajectory": pred.trajectory, "escalation": pred.escalation,
                           "text": t(pred.code, lang, **pred.params)},
            "stats": {"messages": row["msg_count"], "flagged": flagged_msgs, "distinct_targets": len(targets),
                      "minor_targets": len(minor_targets), "reports": snap.reporters, "mod_actions": mod_actions,
                      "network_flags": len(network)},
            "contacts": contacts,
            "timeline": timeline[:120],
            "series": {"days": days, "messages": [msgs_by_day[d] for d in days],
                       "flagged": [flagged_by_day[d] for d in days], "score": scores},
        }

    # --- server -----------------------------------------------------------------------------
    def facts(self, gid: int) -> GuildFacts | None:
        raw = json.loads(self.store.val("SELECT audit FROM guilds WHERE id=?", gid, default="{}"))
        if not raw.get("facts"):
            return None
        f = dict(raw["facts"])
        f["automod_triggers"] = frozenset(f.get("automod_triggers", ()))
        f["guard_missing"] = tuple(f.get("guard_missing", ()))
        f["minors_est"] = self.minors(gid)
        return GuildFacts(**f)

    def minors(self, gid: int) -> int:
        return self.store.val("SELECT COUNT(*) FROM members WHERE guild_id=? AND left_at IS NULL AND is_bot=0 "
                              "AND ((self_age IS NOT NULL AND self_age<18) OR role_age='minor')", gid)

    def median_response_min(self, gid: int, since: int) -> int | None:
        rows = self.store.q("SELECT resolved_at-created_at d FROM alerts WHERE guild_id=? AND resolved_at IS NOT NULL "
                            "AND created_at>=? AND resolved_by IS NOT NULL", gid, since)
        return round(statistics.median(r["d"] for r in rows) / 60) if rows else None

    def health(self, gid: int, lang: Lang) -> tuple[dict[str, Any], list[Check], dict[str, Any]]:
        s, t0 = self.store, now()
        facts = self.facts(gid)
        checks = audit_guild(facts) if facts else []
        sigs = audit_signals(checks) if facts else []
        open_red = s.val("SELECT COUNT(*) FROM alerts WHERE guild_id=? AND status='open' AND level='red'", gid)
        stale = s.val("SELECT COUNT(*) FROM alerts WHERE guild_id=? AND status='open' AND created_at<?", gid,
                      t0 - 86_400)
        red = s.val("SELECT COUNT(*) FROM members WHERE guild_id=? AND level='red' AND left_at IS NULL "
                    "AND status NOT IN ('actioned','trusted')", gid)
        yellow = s.val("SELECT COUNT(*) FROM members WHERE guild_id=? AND level='yellow' AND left_at IS NULL "
                       "AND status NOT IN ('actioned','trusted')", gid)
        raids = sum(s.series(gid, "raids", 7))
        msgs7, flagged7 = sum(s.series(gid, "messages", 7)), sum(s.series(gid, "flagged", 7))
        alerts7 = sum(s.series(gid, "alerts", 7))
        resp = self.median_response_min(gid, t0 - 30 * 86_400)
        if open_red:
            sigs.append(Signal("live.open_red", min(30, 10 * open_red), {"n": open_red}))
        if red:
            sigs.append(Signal("live.red_members", min(24, 8 * red), {"n": red}))
        if raids:
            sigs.append(Signal("live.raid", 10))
        if stale:
            sigs.append(Signal("live.stale_alerts", min(15, 5 * stale), {"n": stale}))
        if resp is not None:
            sigs.append(Signal("live.slow_response", 8, {"min": resp}) if resp > 180
                        else Signal("live.fast_response", -5, {"min": resp}) if resp <= 30 else None)
        rate = round(1000 * flagged7 / msgs7, 1) if msgs7 >= 200 else 0
        if rate > 5:
            sigs.append(Signal("live.flag_rate", 10, {"rate": rate}))
        if not alerts7 and msgs7:
            sigs.append(Signal("live.quiet", -5))
        sigs = [x for x in sigs if x is not None]
        conf = Confidence.HIGHEST if msgs7 else Confidence.HIGH
        v = build_verdict(Kind.SERVER, sigs, base=SERVER_LIVE_BASE, confidence=conf)  # for ordering
        score = server_score(sigs)
        health = {"score": score, "level": level_for(score).value, "grade": grade(score),
                  "confidence": t(f"confidence.{conf.name.lower()}", lang),
                  "signals": [signal_dict(x, lang) for x in v.signals]}
        live = {"open_red": open_red, "red": red, "yellow": yellow, "raids": raids, "msgs7": msgs7,
                "flagged7": flagged7, "alerts7": alerts7, "resp": resp, "rate": rate}
        return health, checks, live

    def overview(self, gid: int, lang: Lang, *, missing: list[str] | None = None,
                 alert_channel: str | None = None) -> dict[str, Any] | None:
        s = self.store
        g = s.guild(gid)
        if g is None:
            return None
        settings = s.settings(gid)
        health, checks, live = self.health(gid, lang)
        members = s.val("SELECT COUNT(*) FROM members WHERE guild_id=? AND left_at IS NULL AND is_bot=0", gid)
        member_count = g["member_count"] or members
        minors = self.minors(gid)
        open_alerts = s.val("SELECT COUNT(*) FROM alerts WHERE guild_id=? AND status='open'", gid)
        days = last_days(30)

        summary = [t("rep.g.members", lang, n=member_count, m=minors)]
        if live["msgs7"] >= 200:
            summary.append(t("rep.g.activity", lang, msgs=live["msgs7"], flagged=live["flagged7"],
                             rate=round(1000 * live["flagged7"] / live["msgs7"], 1)))
        elif live["msgs7"]:
            summary.append(t("rep.g.activity_small", lang, msgs=live["msgs7"], flagged=live["flagged7"]))
        summary.append(t("rep.g.alerts", lang, open=open_alerts, week=live["alerts7"]))
        if live["red"] or live["yellow"]:
            summary.append(t("rep.g.risk", lang, red=live["red"], yellow=live["yellow"]))
        if live["resp"] is not None:
            summary.append(t("rep.g.response", lang, min=live["resp"]))
        if live["raids"]:
            summary.append(t("rep.g.raids", lang, n=live["raids"]))
        if checks:
            fails = sum(not c.ok for c in checks)
            summary.append(t("rep.g.audit", lang, fails=fails, total=len(checks)))
        summary.append(t(f"rep.g.mode_{settings['mode']}", lang))

        sev_rank = {"high": 0, "medium": 1, "low": 2}
        recs = [{"severity": c.severity, "text": t(f"audit.{c.id}.todo", lang), "fix": c.fix}
                for c in sorted(checks, key=lambda c: sev_rank[c.severity]) if not c.ok]
        if not settings["alert_channel_id"]:
            recs.insert(0, {"severity": "high", "text": t("rec.alert_channel", lang), "fix": None})
        if live["open_red"]:
            recs.insert(0, {"severity": "high", "text": t("rec.review_red", lang, n=live["open_red"]), "fix": None})
        if settings["mode"] == "observe" and (live["red"] or live["raids"]):
            recs.append({"severity": "medium", "text": t("rec.protect_mode", lang), "fix": None})
        if minors and not settings["minor_role_ids"]:
            recs.append({"severity": "low", "text": t("rec.minor_roles", lang), "fix": None})

        top = s.q("SELECT * FROM members WHERE guild_id=? AND left_at IS NULL AND is_bot=0 AND level<>'green' "
                  "AND status NOT IN ('trusted') ORDER BY score DESC LIMIT 8", gid)
        recent = s.q("SELECT * FROM alerts WHERE guild_id=? ORDER BY id DESC LIMIT 8", gid)
        audit = [{"id": c.id, "ok": c.ok, "severity": c.severity, "label": t(f"audit.{c.id}.label", lang),
                  "detail": t(f"audit.{c.id}.ok" if c.ok else f"audit.{c.id}", lang, **c.params), "fix": c.fix}
                 for c in checks]
        return {
            "guild": {"id": str(gid), "name": g["name"], "icon": g["icon"], "member_count": member_count,
                      "guard_since": iso(g["joined_at"]), "mode": settings["mode"], "alert_channel": alert_channel},
            "health": health,
            "summary": summary,
            "recommendations": recs,
            "kpis": {"members": member_count, "minors_est": minors, "at_risk": live["red"] + live["yellow"],
                     "red": live["red"], "open_alerts": open_alerts, "flagged_7d": live["flagged7"],
                     "messages_7d": live["msgs7"], "joins_7d": sum(s.series(gid, "joins", 7)),
                     "actions_7d": sum(s.series(gid, "actions", 7)), "median_response_min": live["resp"]},
            "series": {"days": days, **{m: s.series(gid, m) for m in ("messages", "flagged", "joins", "alerts")}},
            "top_risks": [self.member_row(r, lang) for r in top],
            "recent_alerts": [self.alert_dict(r, lang) for r in recent],
            "audit": audit,
            "permissions_missing": missing or [],
        }

    # --- owner ------------------------------------------------------------------------------
    def owner(self, lang: Lang, system: dict[str, Any]) -> dict[str, Any]:
        s, t0 = self.store, now()
        week, month = t0 - 7 * 86_400, t0 - 30 * 86_400
        guilds = []
        for g in s.active_guilds():
            health, _, _ = self.health(g["id"], lang)
            guilds.append({
                "id": str(g["id"]), "name": g["name"], "icon": g["icon"], "members": g["member_count"],
                "mode": s.settings(g["id"])["mode"], "score": health["score"], "level": health["level"],
                "open_alerts": s.val("SELECT COUNT(*) FROM alerts WHERE guild_id=? AND status='open'", g["id"]),
                "alerts_7d": sum(s.series(g["id"], "alerts", 7)), "joined_at": iso(g["joined_at"]),
            })
        pocket: dict[str, dict[str, int]] = {k: {"green": 0, "yellow": 0, "red": 0} for k in ("server", "person",
                                                                                            "message")}
        for r in s.q("SELECT metric, SUM(n) n FROM daily WHERE guild_id=0 AND metric LIKE 'pocket.%' AND day>=? "
                     "GROUP BY metric", last_days(30)[0]):
            parts = r["metric"].split(".")  # also pocket.report, pocket.ai.red, ...: only kind.level counts here
            kind, level = (parts[1], parts[2]) if len(parts) == 3 else ("", "")
            if kind in pocket and level in pocket[kind]:
                pocket[kind][level] = r["n"]
        pocket_series = [0] * 30
        for metric in (f"pocket.{k}.{lv}" for k in pocket for lv in ("green", "yellow", "red")):
            pocket_series = [a + b for a, b in zip(pocket_series, s.series(0, metric), strict=True)]
        quality = []
        fps = {r["code"]: r["n"] for r in s.q("SELECT code, COUNT(*) n FROM feedback WHERE at>=? GROUP BY code", month)}
        for r in s.q("SELECT code, COUNT(*) n FROM observations WHERE at>=? GROUP BY code ORDER BY n DESC", month):
            fp = fps.get(r["code"], 0)
            quality.append({"code": r["code"], "label": t(f"label.{r['code']}", lang, app="…"),
                            "fired_30d": r["n"], "false_positive": fp, "fp_rate": round(fp / r["n"], 3)})
        network = []
        for r in s.q("SELECT user_id, COUNT(*) n, MIN(at) first_at, GROUP_CONCAT(reason) reasons FROM network "
                     "GROUP BY user_id ORDER BY n DESC LIMIT 200"):
            m = s.one("SELECT * FROM members WHERE user_id=? ORDER BY score_at DESC LIMIT 1", r["user_id"])
            network.append({"user": {"id": str(r["user_id"]), "name": name_of(m, r["user_id"]),
                                     "avatar": m["avatar"] if m else None, "minor": False},
                            "guilds": r["n"], "reasons": sorted({t(f"net.{x}", lang) for x in r["reasons"].split(",")}),
                            "first_at": iso(r["first_at"])})
        return {
            "system": system,
            "totals": {"guilds": len(guilds), "members": sum(g["members"] or 0 for g in guilds),
                       "alerts_open": s.val("SELECT COUNT(*) FROM alerts WHERE status='open'"),
                       "alerts_7d": s.val("SELECT COUNT(*) FROM alerts WHERE created_at>=?", week),
                       "flagged_7d": sum(s.series(None, "flagged", 7)),
                       "network_flags": s.val("SELECT COUNT(DISTINCT user_id) FROM network"),
                       "pocket_checks_7d": sum(pocket_series[-7:])},
            "series": {"days": last_days(30), "pocket_checks": pocket_series, "alerts": s.series(None, "alerts"),
                       "flagged": s.series(None, "flagged"), "messages": s.series(None, "messages")},
            "pocket": pocket,
            "guilds": guilds,
            "signal_quality": sorted(quality, key=lambda q: (-q["fp_rate"], -q["fired_30d"])),
            "network": network,
        }

    # --- public -----------------------------------------------------------------------------
    def public(self, crowd: dict[str, int] | None = None) -> dict[str, Any]:
        """Deployment-wide totals for the public stats page: counts only, no names, IDs or text.
        Totals cover what `daily` keeps (400 days)."""
        s = self.store
        total = lambda m: s.val("SELECT SUM(n) FROM daily WHERE guild_id<>0 AND metric=?", m)  # noqa: E731
        guilds = s.active_guilds()
        checks = {k: {"green": 0, "yellow": 0, "red": 0} for k in ("server", "person", "message")}
        for r in s.q("SELECT metric, SUM(n) n FROM daily WHERE guild_id=0 AND metric LIKE 'pocket.%' GROUP BY metric"):
            parts = r["metric"].split(".")
            if len(parts) == 3 and parts[1] in checks and parts[2] in checks[parts[1]]:
                checks[parts[1]][parts[2]] = r["n"]
        pocket_series = [0] * 90
        for metric in (f"pocket.{k}.{lv}" for k in checks for lv in ("green", "yellow", "red")):
            pocket_series = [a + b for a, b in zip(pocket_series, s.series(0, metric, 90), strict=True)]
        g0 = lambda m: s.val("SELECT SUM(n) FROM daily WHERE guild_id=0 AND metric=?", m)  # noqa: E731
        first = s.val("SELECT MIN(day) FROM daily", default=None)
        signals = [{"code": r["code"], "label": t(f"label.{r['code']}", "en", app="another app"), "n": r["n"]}
                   for r in s.q("SELECT code, COUNT(*) n FROM observations GROUP BY code ORDER BY n DESC LIMIT 8")]
        return {
            "generated_at": iso(now()),
            "since": f"{first}T00:00:00Z" if first else None,
            "servers": len(guilds),
            "members": sum(g["member_count"] or 0 for g in guilds),
            "guard": {
                "messages": total("messages"), "flagged": total("flagged"), "alerts": total("alerts"),
                "red_alerts": s.val("SELECT COUNT(*) FROM alerts WHERE level='red'"),
                "resolved": s.val("SELECT COUNT(*) FROM alerts WHERE status='resolved'"),
                "actions": total("actions"), "raids": total("raids"), "reports": total("reports"),
                "kids_warned": total("warned"),
                "network_flags": s.val("SELECT COUNT(DISTINCT user_id) FROM network"),
            },
            "pocket": {
                "users": (crowd or {}).get("users", 0),
                "checks": sum(sum(v.values()) for v in checks.values()), "by_kind": checks,
                "scans": g0("pocket.scan"), "watch_alerts": g0("pocket.watch_alert"), "reports": g0("pocket.report"),
                "flagged_accounts": (crowd or {}).get("flagged", 0) + (crowd or {}).get("confirmed", 0),
            },
            "signals": signals,
            "series": {"days": last_days(90), "messages": s.series(None, "messages", 90),
                       "flagged": s.series(None, "flagged", 90), "alerts": s.series(None, "alerts", 90),
                       "pocket_checks": pocket_series},
        }


_L = {  # short labels for timelines and the owner's signal-quality table
    "msg.age_probe": ("Asked someone's age", "Frågade någon om ålder"),
    "msg.age_gap": ("Pointed out an adult/child age gap", "Lyfte fram åldersskillnad vuxen/barn"),
    "msg.isolation": ("Tried to move the chat to {app}", "Försökte flytta chatten till {app}"),
    "msg.isolation_private": ("Asked for a private call or chat", "Bad om ett privat samtal eller chatt"),
    "msg.secrecy": ("Asked to keep a secret", "Bad någon hålla en hemlighet"),
    "msg.photo_request": ("Asked for photos", "Bad om bilder"),
    "msg.sexual": ("Sexual message", "Sexuellt meddelande"),
    "msg.gifts": ("Offered gifts or money", "Erbjöd presenter eller pengar"),
    "msg.meeting": ("Tried to meet in real life", "Försökte träffas på riktigt"),
    "msg.personal_info": ("Asked for personal details", "Frågade efter personliga uppgifter"),
    "msg.flattery": ("Heavy flattery", "Mycket smicker"),
    "msg.scam_link": ("Scam link", "Bluff-länk"),
    "msg.pressure": ("Pressure or threats", "Press eller hot"),
    "msg.multi_stage": ("Several warning signs in one message", "Flera varningstecken i ett meddelande"),
    "behave.dm_request": ("Asked to move to DMs", "Ville flytta till DM"),
    "behave.invite_link": ("Posted a server invite", "Lade upp en serverinbjudan"),
    "behave.spam": ("Spam across channels", "Spam i flera kanaler"),
    "behave.mass_mention": ("Mass mention", "Massomnämnande"),
    "behave.automod": ("Blocked by AutoMod", "Blockerat av AutoMod"),
}

register({
    **{f"label.{k}": {"en": en, "sv": sv} for k, (en, sv) in _L.items()},
    "alert.to_minor_suffix": {"en": " (to a member under 18)", "sv": " (till en medlem under 18)"},
    "alert.someone": {"en": "someone", "sv": "någon"},
    "alert.t.sexual": {"en": "Possible grooming: sexual message or photo request", "sv": "Möjlig grooming: sexuellt meddelande eller bildförfrågan"},
    "alert.t.pressure": {"en": "Pressure or threats", "sv": "Press eller hot"},
    "alert.t.meeting": {"en": "Trying to meet a member in real life", "sv": "Försöker träffa en medlem på riktigt"},
    "alert.t.secrecy": {"en": "Asking a member to keep secrets", "sv": "Ber en medlem hålla hemligheter"},
    "alert.t.isolation": {"en": "Pulling a member into DMs or another app", "sv": "Drar en medlem till DM eller en annan app"},
    "alert.t.probing": {"en": "Probing a member's age or personal details", "sv": "Frågar ut en medlem om ålder eller personliga uppgifter"},
    "alert.t.gifts": {"en": "Gifts or flattery aimed at a member", "sv": "Presenter eller smicker riktat mot en medlem"},
    "alert.t.scam": {"en": "Scam link", "sv": "Bluff-länk"},
    "alert.t.spam": {"en": "Spam", "sv": "Spam"},
    "alert.t.message": {"en": "Message with warning signs", "sv": "Meddelande med varningstecken"},
    "alert.t.member_yellow": {"en": "Member's behaviour pattern is concerning", "sv": "Medlemmens beteendemönster är oroande"},
    "alert.t.member_red": {"en": "Member is now high risk", "sv": "Medlemmen har nu hög risk"},
    "alert.t.raid": {"en": "Join raid: {n} accounts in a burst", "sv": "Raid: {n} konton på kort tid"},
    "alert.t.network": {"en": "Joined: banned for child safety in {n} other server(s)", "sv": "Gick med: bannad för barnsäkerhet i {n} andra server(rar)"},
    "alert.t.join": {"en": "High-risk account joined", "sv": "Högriskkonto gick med"},
    "alert.t.report": {"en": "Member report", "sv": "Anmälan från medlem"},
    "alert.s.message": {"en": "{user} → {target} in #{channel}.", "sv": "{user} → {target} i #{channel}."},
    "alert.s.member": {"en": "{user}: pattern across their messages.", "sv": "{user}: mönster i hens meddelanden."},
    "alert.s.raid": {"en": "{n} joins in under two minutes.", "sv": "{n} anslutningar på under två minuter."},
    "alert.s.network": {"en": "{user} just joined.", "sv": "{user} gick precis med."},
    "alert.s.join": {"en": "{user} just joined.", "sv": "{user} gick precis med."},
    "alert.s.report": {"en": "{target} reported {user} in #{channel}.", "sv": "{target} anmälde {user} i #{channel}."},
    # person report sentences
    "rep.p.account": {"en": "Discord account created {days} days ago.", "sv": "Discord-kontot skapades för {days} dagar sedan."},
    "rep.p.joined": {"en": "Joined the server {days} days ago.", "sv": "Gick med i servern för {days} dagar sedan."},
    "rep.p.joined_today": {"en": "Joined the server today.", "sv": "Gick med i servern i dag."},
    "rep.p.invite": {"en": "Came in through invite {invite}.", "sv": "Kom in via inbjudan {invite}."},
    "rep.p.age_said": {"en": "Said they are {age}.", "sv": "Har sagt att hen är {age}."},
    "rep.p.role_minor": {"en": "Their roles say they are under 18.", "sv": "Hens roller säger att hen är under 18."},
    "rep.p.role_adult": {"en": "Their roles say they are an adult.", "sv": "Hens roller säger att hen är vuxen."},
    "rep.p.activity": {"en": "Sent {msgs} messages and talked directly with {targets} member(s).", "sv": "Har skickat {msgs} meddelanden och pratat direkt med {targets} medlem(mar)."},
    "rep.p.flagged": {"en": "{n} flagged message(s) aimed at {targets} member(s), {minors} of them under 18.", "sv": "{n} flaggade meddelanden riktade till {targets} medlem(mar), varav {minors} under 18."},
    "rep.p.reports": {"en": "Reported by {n} member(s).", "sv": "Anmäld av {n} medlem(mar)."},
    "rep.p.network": {"en": "Banned for child safety in {n} other Guard server(s).", "sv": "Bannad för barnsäkerhet i {n} andra Guard-server(rar)."},
    "rep.p.mod_actions": {"en": "{n} moderation action(s) on record.", "sv": "{n} moderationsåtgärd(er) registrerade."},
    "rep.p.status_watch": {"en": "On the watch list.", "sv": "Står på bevakningslistan."},
    "rep.p.status_trusted": {"en": "Marked trusted by a moderator.", "sv": "Markerad som pålitlig av en moderator."},
    "rep.p.status_actioned": {"en": "Already kicked or banned.", "sv": "Redan sparkad eller bannad."},
    "rep.p.clean": {"en": "No warning signs in their history.", "sv": "Inga varningstecken i hens historik."},
    # timeline
    "tl.to_minor": {"en": " → {name} (under 18)", "sv": " → {name} (under 18)"},
    "tl.to_member": {"en": " → {name}", "sv": " → {name}"},
    "tl.alert_note": {"en": "{by} on alert #{id}: {note}", "sv": "{by} om larm #{id}: {note}"},
    "tl.deleted": {"en": " · deleted afterwards", "sv": " · raderat efteråt"},
    "tl.join": {"en": "Joined (invite {invite})", "sv": "Gick med (inbjudan {invite})"},
    "tl.leave": {"en": "Left the server", "sv": "Lämnade servern"},
    "tl.name_change": {"en": "Changed name from {from} to {to}", "sv": "Bytte namn från {from} till {to}"},
    "tl.age_said": {"en": "Said they are {age}", "sv": "Sa att hen är {age}"},
    "tl.reported": {"en": "Reported by {by}", "sv": "Anmäld av {by}"},
    "tl.action": {"en": "Moderation: {kind} (by {by})", "sv": "Moderering: {kind} (av {by})"},
    "tl.deleted_flagged": {"en": "Deleted a flagged message", "sv": "Raderade ett flaggat meddelande"},
    "tl.warned": {"en": "Guard sent them a safety tip", "sv": "Guard skickade ett säkerhetstips"},
    "tl.status": {"en": "Status set to {status} by {by}", "sv": "Status satt till {status} av {by}"},
    # server report sentences
    "rep.g.members": {"en": "{n} members; {m} of them said or show they are under 18.", "sv": "{n} medlemmar; {m} av dem har sagt eller visar att de är under 18."},
    "rep.g.activity": {"en": "{msgs} messages this week, {flagged} flagged ({rate} per 1,000).", "sv": "{msgs} meddelanden den här veckan, {flagged} flaggade ({rate} per 1 000)."},
    "rep.g.activity_small": {"en": "{msgs} messages this week, {flagged} flagged.", "sv": "{msgs} meddelanden den här veckan, {flagged} flaggade."},
    "rep.g.alerts": {"en": "{open} open alert(s); {week} raised this week.", "sv": "{open} öppna larm; {week} nya den här veckan."},
    "rep.g.risk": {"en": "{red} member(s) rated red and {yellow} yellow.", "sv": "{red} medlem(mar) med rött betyg och {yellow} med gult."},
    "rep.g.response": {"en": "Moderators handle alerts in about {min} minutes (median).", "sv": "Moderatorerna hanterar larm på ungefär {min} minuter (median)."},
    "rep.g.raids": {"en": "{n} join raid(s) this week.", "sv": "{n} raid(er) den här veckan."},
    "rep.g.audit": {"en": "{fails} of {total} safety checks need attention.", "sv": "{fails} av {total} säkerhetskontroller behöver åtgärdas."},
    "rep.g.mode_observe": {"en": "Guard is in observe mode: it alerts moderators but takes no action itself.", "sv": "Guard är i observationsläge: den larmar moderatorer men agerar inte själv."},
    "rep.g.mode_protect": {"en": "Guard is in protect mode: it deletes the worst messages and times out red members until a moderator reviews.", "sv": "Guard är i skyddsläge: den raderar de värsta meddelandena och stänger av röda medlemmar tills en moderator granskat."},
    "rec.alert_channel": {"en": "Choose a private moderator channel for Guard's alerts.", "sv": "Välj en privat moderatorkanal för Guards larm."},
    "rec.review_red": {"en": "Review the {n} open red alert(s) now.", "sv": "Granska de {n} öppna röda larmen nu."},
    "rec.protect_mode": {"en": "Switch to protect mode so Guard can act while no moderator is online.", "sv": "Byt till skyddsläge så att Guard kan agera när ingen moderator är online."},
    "rec.minor_roles": {"en": "If you have age roles, mark which ones mean under 18 so Guard protects those members first.", "sv": "Om ni har åldersroller, markera vilka som betyder under 18 så skyddar Guard de medlemmarna först."},
    "net.child_safety": {"en": "Banned for child safety", "sv": "Bannad för barnsäkerhet"},
    "net.manual": {"en": "Flagged by a moderator", "sv": "Flaggad av en moderator"},
})
