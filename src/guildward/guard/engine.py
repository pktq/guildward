"""Guard's brain: Discord-free events in, observations + alerts + actions out.

guard/bot.py turns discord.py objects into the small event types below, calls the engine, and carries
out what comes back (post an alert, delete a message, time someone out, DM a safety tip). Keeping
Discord out of here means the whole pipeline is testable with plain data (tests/test_guard.py).

Message text lives only inside one `on_message` call. Only signal codes, weights and IDs are stored.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Any

from guildward.core.models import Confidence, Kind, Level, Signal, Verdict, build_verdict
from guildward.core.snowflake import age_days
from guildward.guard.store import Store, is_adult_row, is_minor_row, now
from guildward.intel.behavior import (
    STAGE_OF,
    ContactFacts,
    MemberSnapshot,
    Prediction,
    age_disclosure,
    context_signals,
    predict,
    score_member,
)
from guildward.intel.message import MESSAGE_BASE, analyze_message
from guildward.intel.person import UserFacts

RANK = {"green": 0, "yellow": 1, "red": 2}
TARGET_WINDOW = 120  # a message right after someone else's in the same channel is probably aimed at them
RAID_WINDOW, RAID_JOINS, RAID_NEW = 60, 10, 5
DEDUPE_SECONDS = 600
_PEER_NORMAL = {"msg.age_probe", "msg.personal_info", "msg.isolation", "msg.isolation_private",
                "behave.dm_request", "msg.flattery", "msg.gifts"}
_BROADCAST = {"msg.scam_link", "behave.spam", "behave.mass_mention", "behave.invite_link", "msg.multi_stage"}
_DELETE_WORTHY = {"msg.photo_request", "msg.sexual", "msg.pressure", "msg.scam_link"}
_MOD_KINDS = {"timeout", "kick", "ban", "warn"}
# Most serious first: a merged alert keeps the worst title it has seen.
_TITLES = [f"alert.t.{x}" for x in ("sexual", "pressure", "meeting", "secrecy", "isolation", "probing", "gifts",
                                       "scam", "spam", "message")]

_TITLE_OF = {
    "msg.photo_request": "sexual", "msg.sexual": "sexual", "msg.pressure": "pressure", "msg.meeting": "meeting",
    "msg.secrecy": "secrecy", "msg.isolation": "isolation", "msg.isolation_private": "isolation",
    "behave.dm_request": "isolation", "msg.age_probe": "probing", "msg.personal_info": "probing",
    "msg.age_gap": "probing", "msg.gifts": "gifts", "msg.flattery": "gifts", "msg.scam_link": "scam",
    "behave.spam": "spam", "behave.mass_mention": "spam", "behave.invite_link": "spam",
}


@dataclass(frozen=True, slots=True)
class MemberInfo:
    id: int
    username: str
    display: str | None = None
    avatar: str | None = None  # URL
    has_avatar: bool = False
    is_bot: bool = False
    spammer: bool = False
    role_age: str | None = None  # minor | adult | None, from role names / minor_role_ids
    roles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MessageEvent:
    guild_id: int
    channel_id: int
    message_id: int
    author: MemberInfo
    content: str
    at: int
    reply_to: int | None = None  # author of the message being replied to
    mentions: tuple[int, ...] = ()
    channel_name: str = ""
    backfill: bool = False  # history scan: record, never alert or act


@dataclass(frozen=True, slots=True)
class JoinEvent:
    guild_id: int
    member: MemberInfo
    at: int
    invite_code: str | None = None
    inviter_id: int | None = None


@dataclass(frozen=True, slots=True)
class Out:
    """Something the Discord layer must do. kind: alert | alert_update | delete | timeout | quarantine | warn_dm"""

    kind: str
    guild_id: int
    alert_id: int | None = None
    user_id: int | None = None
    channel_id: int | None = None
    message_id: int | None = None
    seconds: int = 0
    reason: str = ""


def sig_json(signals: tuple[Signal, ...] | list[Signal]) -> list[dict[str, Any]]:
    return [{"code": s.code, "weight": s.weight, "params": dict(s.params), "severe": s.severe} for s in signals]


@dataclass
class _GuildState:
    joins: deque[tuple[int, int, bool]] = field(default_factory=deque)
    raid_until: int = 0
    last_author: dict[int, tuple[int, int]] = field(default_factory=dict)


class Engine:
    def __init__(self, store: Store) -> None:
        self.store = store
        self._g: dict[int, _GuildState] = {}
        self._spam: dict[tuple[int, int], deque[tuple[int, str, int]]] = {}
        # Flagged text for the dashboard, memory only (gone on restart, never written to disk).
        self.quotes: OrderedDict[int, str] = OrderedDict()
        self.events_seen = deque(maxlen=5000)
        self._last_spam: list[Signal] = []

    def _gs(self, gid: int) -> _GuildState:
        return self._g.setdefault(gid, _GuildState())

    def _remember_quote(self, aid: int, text: str) -> None:
        self.quotes[aid] = text[:400]
        while len(self.quotes) > 1000:
            self.quotes.popitem(last=False)

    # --- members ----------------------------------------------------------------------------
    def _upsert(self, gid: int, m: MemberInfo, **extra: Any) -> None:
        self.store.upsert_member(gid, m.id, username=m.username, display=m.display, avatar=m.avatar,
                                 has_avatar=int(m.has_avatar), is_bot=int(m.is_bot), spammer=int(m.spammer),
                                 role_age=m.role_age, roles=json.dumps(list(m.roles)[:25]), **extra)

    def snapshot(self, gid: int, uid: int) -> MemberSnapshot | None:
        s = self.store
        row = s.member(gid, uid)
        if row is None:
            return None
        t = now()
        contacts = [ContactFacts(c["target_id"], is_minor_row(c), c["msgs"], json.loads(c["stages"]), c["last_at"])
                    for c in s.contacts_of(gid, uid) if c["stages"] != "{}"]
        mod_actions = sum(1 for e in s.events_of(gid, uid, 200)
                          if e["kind"] == "action" and json.loads(e["data"]).get("kind") in _MOD_KINDS)
        name_changes = s.val("SELECT COUNT(*) FROM events WHERE guild_id=? AND user_id=? AND kind='name_change' "
                             "AND at>=?", gid, uid, t - 7 * 86_400)
        user = UserFacts(id=uid, username=row["username"], global_name=row["display"],
                         has_avatar=bool(row["has_avatar"]), is_bot=bool(row["is_bot"]),
                         discord_spammer=bool(row["spammer"]))
        settings = s.settings(gid)
        return MemberSnapshot(
            user=user, now=t, joined_at=row["joined_at"], self_age=row["self_age"], minor=is_minor_row(row),
            adult=is_adult_row(row), status=row["status"], msg_count=row["msg_count"],
            obs=s.observations(gid, uid, t - 30 * 86_400), contacts=contacts, reporters=s.reporters(gid, uid),
            mod_actions=mod_actions,
            network_guilds=len(s.network_flags(uid, exclude_guild=gid)) if settings["network_share"] else 0,
            name_changes_7d=name_changes, raid_join=bool(row["raid_join"]),
        )

    def rescore(self, gid: int, uid: int) -> tuple[Verdict, str, Prediction] | None:
        """Recompute a member's score. Returns (verdict, previous level, prediction)."""
        snap = self.snapshot(gid, uid)
        if snap is None:
            return None
        row = self.store.member(gid, uid)
        prev = row["level"] if row else "green"
        v = score_member(snap)
        top = v.risks[0] if v.risks else None
        self.store.record_score(gid, uid, v.score, v.level.value, top.code if top else None,
                                dict(top.params) if top else None, codes=[x.code for x in v.risks])
        return v, prev, predict(snap, v, self.store.score_days_ago(gid, uid, 7))

    # --- messages ---------------------------------------------------------------------------
    def _target(self, ev: MessageEvent) -> int | None:
        gs = self._gs(ev.guild_id)
        target = None
        if ev.reply_to and ev.reply_to != ev.author.id:
            target = ev.reply_to
        else:
            others = [m for m in dict.fromkeys(ev.mentions) if m != ev.author.id]
            if len(others) == 1:
                target = others[0]
            elif not others and (last := gs.last_author.get(ev.channel_id)):
                uid, at = last
                if uid != ev.author.id and ev.at - at <= TARGET_WINDOW:
                    target = uid
        gs.last_author[ev.channel_id] = (ev.author.id, ev.at)
        return target

    def _spam_signal(self, ev: MessageEvent) -> Signal | None:
        self._last_spam = []
        if len(ev.content) < 12:
            return None
        key = (ev.guild_id, ev.author.id)
        q = self._spam.setdefault(key, deque(maxlen=20))
        h = hashlib.blake2b(ev.content.casefold().encode(), digest_size=8).hexdigest()  # hash only, never the text
        q.append((ev.at, h, ev.channel_id))
        channels = {c for at, hh, c in q if hh == h and ev.at - at <= 60}
        self._last_spam = [Signal("behave.spam", 15)] if len(channels) >= 3 else []
        return self._last_spam[0] if self._last_spam else None

    def message_verdict(self, ev: MessageEvent, target: int | None, *,
                        spam_checked: bool = False) -> tuple[Verdict, bool, list[Signal]]:
        """Message signals adjusted for who sent it to whom. Returns (verdict, target_minor, raw signals)."""
        s = self.store
        raw = list(analyze_message(ev.content)) + context_signals(ev.content)
        if spam_checked:
            raw += [x for x in self._last_spam if x]
        elif sp := self._spam_signal(ev):
            raw.append(sp)
        if len(set(ev.mentions)) >= 5:
            raw.append(Signal("behave.mass_mention", 15))
        if not raw:
            return build_verdict(Kind.MESSAGE, [], base=0, confidence=Confidence.HIGHEST), False, []

        sender = s.member(ev.guild_id, ev.author.id)
        sender_minor = bool(sender) and is_minor_row(sender)
        sender_adult = bool(sender) and is_adult_row(sender)
        trow = s.member(ev.guild_id, target) if target else None
        target_minor = bool(trow) and is_minor_row(trow)

        sigs = list(raw)
        if target_minor and sender_minor:
            # Kids ask each other's age and swap Snapchats constantly; only the non-peer-normal parts count fully.
            peer_only = all(x.code in _PEER_NORMAL or x.code == "msg.multi_stage" for x in sigs)
            sigs = [dataclasses.replace(x, weight=x.weight // 4)
                    if x.code in _PEER_NORMAL or (peer_only and x.code == "msg.multi_stage") else x for x in sigs]
            sigs.append(Signal("ctx.peer", 0))
        elif target_minor:
            sigs = [dataclasses.replace(x, weight=round(x.weight * 1.25)) for x in sigs]
            if sender_adult and sender["self_age"]:
                sigs.append(Signal("ctx.adult_to_minor", 15, {"age": sender["self_age"]}))
            else:
                sigs.append(Signal("ctx.to_minor", 8))
        days = age_days(ev.author.id)
        if days < 7:
            sigs.append(Signal("ctx.new_account", 8, {"days": int(days)}))
        if sender and sender["status"] == "watch":
            sigs.append(Signal("ctx.watched", 5))
        if sender and sender["status"] == "trusted":
            sigs = [dataclasses.replace(x, weight=x.weight // 2) for x in sigs]
        return (build_verdict(Kind.MESSAGE, sigs, base=MESSAGE_BASE, confidence=Confidence.HIGHEST),
                target_minor, raw)

    def on_message(self, ev: MessageEvent) -> list[Out]:
        if ev.author.is_bot:
            return []
        s, gid, uid = self.store, ev.guild_id, ev.author.id
        self.events_seen.append(ev.at)
        prev_row = s.member(gid, uid)
        self._upsert(gid, ev.author, msg_count=(prev_row["msg_count"] + 1) if prev_row else 1, last_msg_at=ev.at)
        s.bump(gid, "messages", at=ev.at)
        s.count_message(gid, uid, ev.at)

        said = age_disclosure(ev.content)
        if said is not None and (prev_row is None or prev_row["self_age"] != said):
            s.set_member(gid, uid, self_age=said, self_age_at=ev.at)
            s.event(gid, uid, "age_said", {"age": said}, at=ev.at)

        target = self._target(ev)
        v, target_minor, raw = self.message_verdict(ev, target)
        explicit = bool(ev.reply_to) or bool(set(ev.mentions) - {uid})
        if raw and not explicit and {x.code for x in raw} <= _BROADCAST:
            # Scam/spam is aimed at the room, not at whoever happened to speak just before.
            target = None
            v, target_minor, raw = self.message_verdict(ev, None, spam_checked=True)
        stages = sorted({STAGE_OF[x.code].value for x in raw if x.code in STAGE_OF})
        if target:
            s.touch_contact(gid, uid, target, ev.at, stages, v.score if v.level is not Level.GREEN else 0)
        if not raw:
            return []

        adjusted = {x.code: x for x in v.signals}
        with s.tx():
            for x in raw:
                w = adjusted[x.code].weight if x.code in adjusted else x.weight
                s.observe(gid, uid, x.code, w, dict(x.params), target_id=target, target_minor=target_minor,
                          channel_id=ev.channel_id, message_id=ev.message_id, at=ev.at)
        if v.level is not Level.GREEN:
            s.bump(gid, "flagged", at=ev.at)
        scored = self.rescore(gid, uid)
        if ev.backfill or scored is None:
            return []
        mv, prev_level, _ = scored

        settings = s.settings(gid)
        out: list[Out] = []
        min_rank = RANK[settings["alert_min_level"]]
        msg_alert = None
        if RANK[v.level.value] >= min_rank:
            top = v.risks[0].code if v.risks else ""
            title = f"alert.t.{_TITLE_OF.get(top, 'message')}"
            recent = s.recent_alert(gid, kind="message", user_id=uid, target_id=target, within=DEDUPE_SECONDS,
                                    any_target=title in ("alert.t.scam", "alert.t.spam"))
            if recent is not None and recent["status"] == "open":
                # Same person, same target, minutes apart: one growing alert instead of a stream of them.
                msg_alert = recent["id"]
                old = {x["code"]: x for x in json.loads(recent["signals"])}
                merged = {**old, **{x["code"]: x for x in sig_json(v.signals) if x["code"] not in old
                                    or x["weight"] > old[x["code"]]["weight"]}}
                if _TITLES.index(recent["title"]) < _TITLES.index(title):
                    title = recent["title"]
                level = max(recent["level"], v.level.value, key=RANK.__getitem__)
                s.x("UPDATE alerts SET level=?, score=?, title=?, signals=?, channel_id=?, message_id=? WHERE id=?",
                    level, max(recent["score"], v.score), title,
                    json.dumps(sorted(merged.values(), key=lambda x: -x["weight"])), ev.channel_id, ev.message_id,
                    msg_alert)
                out.append(Out("alert_update", gid, msg_alert, uid, ev.channel_id, ev.message_id))
            else:
                msg_alert = s.add_alert(
                    gid, kind="message", level=v.level.value, score=v.score, user_id=uid, target_id=target,
                    title=title, params={"to_minor": int(target_minor), "channel": ev.channel_name},
                    signals=sig_json(v.signals), channel_id=ev.channel_id, message_id=ev.message_id)
                out.append(Out("alert", gid, msg_alert, uid, ev.channel_id, ev.message_id))
            if settings["quote_in_alerts"]:
                self._remember_quote(msg_alert, ev.content)

        crossed = RANK[mv.level.value] > RANK[prev_level] and RANK[mv.level.value] >= min_rank
        if crossed and (msg_alert is None or (mv.level is Level.RED and v.level is not Level.RED)):
            aid = s.add_alert(gid, kind="member", level=mv.level.value, score=mv.score, user_id=uid,
                              title=f"alert.t.member_{mv.level.value}", params={}, signals=sig_json(mv.risks[:8]))
            out.append(Out("alert", gid, aid, uid))

        protect = settings["mode"] == "protect"
        if v.level is Level.RED:
            worst = {x.code for x in raw} & _DELETE_WORTHY or (target_minor and v.score >= 80)
            if protect and settings["auto_delete"] and worst:
                out.append(Out("delete", gid, msg_alert, uid, ev.channel_id, ev.message_id, reason="auto_delete"))
            if settings["warn_targets"] and target and target_minor and self._may_warn(gid, target):
                out.append(Out("warn_dm", gid, msg_alert, target, reason="warn_target"))
        if protect and settings["auto_timeout"] and mv.level is Level.RED and prev_level != "red":
            row = s.member(gid, uid)
            if not row["timeout_at"] or row["timeout_at"] < now() - 86_400:
                s.set_member(gid, uid, timeout_at=now())
                out.append(Out("timeout", gid, msg_alert, uid, seconds=3600, reason="auto_timeout"))
        return out

    def _may_warn(self, gid: int, target: int) -> bool:
        last = self.store.val("SELECT MAX(at) FROM events WHERE guild_id=? AND user_id=? AND kind='warned'",
                              gid, target, default=0)
        if last and last > now() - 86_400:
            return False
        self.store.event(gid, target, "warned")
        return True

    # --- joins / leaves / profile changes ---------------------------------------------------
    def on_join(self, ev: JoinEvent) -> list[Out]:
        s, gid, m = self.store, ev.guild_id, ev.member
        if m.is_bot:
            self._upsert(gid, m, joined_at=ev.at, left_at=None)
            return []
        self.events_seen.append(ev.at)
        self._upsert(gid, m, joined_at=ev.at, left_at=None, invite_code=ev.invite_code, inviter_id=ev.inviter_id)
        s.event(gid, m.id, "join", {"invite": ev.invite_code}, at=ev.at)
        s.bump(gid, "joins", at=ev.at)
        settings = s.settings(gid)
        out: list[Out] = []

        gs = self._gs(gid)
        new_account = age_days(m.id) < 7
        gs.joins.append((ev.at, m.id, new_account))
        while gs.joins and ev.at - gs.joins[0][0] > 2 * RAID_WINDOW:
            gs.joins.popleft()
        recent = [j for j in gs.joins if ev.at - j[0] <= RAID_WINDOW]
        burst = len(recent) >= RAID_JOINS or sum(j[2] for j in gs.joins) >= RAID_NEW
        if settings["raid_protection"] and burst:
            if ev.at > gs.raid_until:
                aid = s.add_alert(gid, kind="raid", level="red", score=80, title="alert.t.raid",
                                  params={"n": len(gs.joins)}, signals=[])
                s.bump(gid, "raids")
                out.append(Out("alert", gid, aid))
            gs.raid_until = ev.at + 300
            for _, uid, _ in gs.joins:
                s.set_member(gid, uid, raid_join=1)
        in_raid = ev.at <= gs.raid_until

        flags = s.network_flags(m.id, exclude_guild=gid) if settings["network_share"] else []
        scored = self.rescore(gid, m.id)
        assert scored is not None
        v = scored[0]
        if flags:
            aid = s.add_alert(gid, kind="network", level="red", score=max(v.score, 70), user_id=m.id,
                              title="alert.t.network", params={"n": len(flags)}, signals=sig_json(v.risks[:6]))
            out.append(Out("alert", gid, aid, m.id))
        elif v.level is Level.RED or (v.level is Level.YELLOW and settings["alert_min_level"] == "yellow"
                                      and any(x.severe for x in v.signals)):
            aid = s.add_alert(gid, kind="join", level=v.level.value, score=v.score, user_id=m.id,
                              title="alert.t.join", params={}, signals=sig_json(v.risks[:6]))
            out.append(Out("alert", gid, aid, m.id))

        if settings["mode"] == "protect":
            risky = v.level is not Level.GREEN or bool(flags)
            if settings["quarantine_role_id"] and (
                    (settings["quarantine_new_accounts"] and risky) or (in_raid and settings["raid_protection"])):
                out.append(Out("quarantine", gid, user_id=m.id, reason="raid" if in_raid else "risky_join"))
            elif in_raid and settings["raid_protection"] and new_account:
                out.append(Out("timeout", gid, user_id=m.id, seconds=3600, reason="raid"))
        return out

    def on_leave(self, gid: int, uid: int, at: int | None = None) -> None:
        if self.store.member(gid, uid):
            self.store.set_member(gid, uid, left_at=at or now())
            self.store.event(gid, uid, "leave", at=at)
            self.store.bump(gid, "leaves")

    def on_member_update(self, gid: int, m: MemberInfo) -> None:
        row = self.store.member(gid, m.id)
        if row and (row["username"], row["display"]) != (m.username, m.display):
            self.store.event(gid, m.id, "name_change", {"from": row["display"] or row["username"],
                                                        "to": m.display or m.username})
        self._upsert(gid, m)
        if row and row["role_age"] != m.role_age:
            self.rescore(gid, m.id)

    def seed_member(self, gid: int, m: MemberInfo, joined_at: int | None) -> None:
        """Existing member seen at startup / guild join: profile only, no join event."""
        row = self.store.member(gid, m.id)
        self._upsert(gid, m, joined_at=joined_at if row is None or row["joined_at"] is None else row["joined_at"])

    def on_delete(self, gid: int, message_id: int) -> None:
        author = self.store.mark_deleted(gid, message_id)
        if author:
            self.store.event(gid, author, "deleted_flagged", {"message_id": str(message_id)})
            self.rescore(gid, author)

    def on_mod_action(self, gid: int, uid: int, kind: str, *, by: int | None, by_name: str | None,
                      source: str = "discord") -> None:
        s = self.store
        if s.member(gid, uid) is None:
            s.upsert_member(gid, uid, username=str(uid))
        s.event(gid, uid, "action", {"kind": kind, "by": by_name, "source": source})
        s.bump(gid, "actions")
        if kind in ("ban", "kick"):
            s.set_member(gid, uid, status="actioned", status_by=by)
        if kind == "ban" and s.settings(gid)["network_share"]:
            row = s.member(gid, uid)
            child_safety = s.val("SELECT COUNT(*) FROM observations WHERE guild_id=? AND user_id=? AND target_minor=1 "
                                 "AND weight>0", gid, uid)
            if child_safety or (row and row["level"] == "red"):
                s.flag_network(uid, gid, "child_safety")
        self.rescore(gid, uid)

    def on_report(self, gid: int, reporter: MemberInfo, target: MemberInfo, *, channel_id: int | None,
                  message_id: int | None, content: str | None, channel_name: str = "") -> list[Out]:
        s = self.store
        self._upsert(gid, reporter)
        if s.member(gid, target.id) is None:
            self._upsert(gid, target)
        if not s.add_report(gid, reporter.id, target.id, channel_id, message_id):
            return []
        s.event(gid, target.id, "reported", {"by": reporter.display or reporter.username})
        s.bump(gid, "reports")
        scored = self.rescore(gid, target.id)
        assert scored is not None
        mv = scored[0]
        sigs = list(mv.risks[:6])
        if content:
            sigs = list(analyze_message(content)) + context_signals(content) + sigs
        level = "red" if mv.level is Level.RED else "yellow"
        aid = s.add_alert(gid, kind="report", level=level, score=max(mv.score, 40), user_id=target.id,
                          target_id=reporter.id, title="alert.t.report", params={"channel": channel_name},
                          signals=sig_json(sigs), channel_id=channel_id, message_id=message_id)
        if content and s.settings(gid)["quote_in_alerts"]:
            self._remember_quote(aid, content)
        return [Out("alert", gid, aid, target.id, channel_id, message_id)]

    def events_per_min(self) -> int:
        t = now()
        return sum(1 for at in self.events_seen if t - at <= 60)
