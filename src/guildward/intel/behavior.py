"""Behaviour Intel, layer 3: what a member *does* over time in a server that invited Guard.

One message is a hint; a pattern across messages and people is evidence. This module turns a
member's history (observations Guard recorded, who they talked to, reports, moderation, network
flags) into one Verdict on the shared 0-100 scale, plus a prediction of where it is heading.

Pure functions over plain data: no Discord types, no database. guard/engine.py builds the snapshot.

Grooming stages follow the research the proposal cites (O'Connell 2003; Lanning; Winters et al.):
trust building -> risk check -> exclusivity -> isolation -> sexual -> meeting, with coercion at any point.
The same message signals map onto stages, so a contact that walks through several stages with one
child is caught even when no single message is red.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from guildward.core.i18n import register
from guildward.core.models import Confidence, Kind, Signal, Verdict, build_verdict
from guildward.core.text import normalize
from guildward.intel.person import UserFacts, score_user

MEMBER_BASE = 5
WINDOW_DAYS = 30
DAY = 86_400


class Stage(StrEnum):
    TRUST = "trust"
    RISK_CHECK = "risk_check"
    EXCLUSIVITY = "exclusivity"
    ISOLATION = "isolation"
    SEXUAL = "sexual"
    MEETING = "meeting"
    COERCION = "coercion"


STAGE_ORDER = list(Stage)
STAGE_OF: dict[str, Stage] = {
    "msg.flattery": Stage.TRUST,
    "msg.gifts": Stage.TRUST,
    "msg.age_probe": Stage.RISK_CHECK,
    "msg.personal_info": Stage.RISK_CHECK,
    "msg.age_gap": Stage.RISK_CHECK,
    "msg.secrecy": Stage.EXCLUSIVITY,
    "msg.isolation": Stage.ISOLATION,
    "msg.isolation_private": Stage.ISOLATION,
    "behave.dm_request": Stage.ISOLATION,
    "msg.photo_request": Stage.SEXUAL,
    "msg.sexual": Stage.SEXUAL,
    "msg.meeting": Stage.MEETING,
    "msg.pressure": Stage.COERCION,
}
_LATE_STAGES = {Stage.ISOLATION, Stage.SEXUAL, Stage.MEETING, Stage.COERCION}

# --- per-message detectors that need no secret rules ---------------------------------------------

_UNITS = (r"min|mins|minutes?|minuter|hours?|hrs?|h|timmar|sec|s|k|m|%|kg|lbs?|cm|ft|th|st|nd|rd|times|x|msgs?|"
          r"messages|days?|weeks?|months?|dagar|veckor|dollars?|usd|eur|euro|kr|sek|robux|levels?|lvl|wins|"
          r"kills|games|fps|ping|gb|mb|v\d|vs|-\d|/\d|\.\d|:\d|am|pm")
_AGE_DISCLOSURE = [
    re.compile(r"(?:^|[^\w])(?:i ?am|i'm|i’m|im|iam)\s+(?:only\s+|just\s+|turning\s+|almost\s+|now\s+)?"
               r"(\d{1,2})(?:\s*(?:years?|yrs?)(?:\s*old)?|\s*y/?o\b)?(?!\d)(?!\s*(?:" + _UNITS + r")\b)(?!\s*[%$+-]\d)"),
    re.compile(r"(?:^|[^\w])jag (?:är|e|ä)\s+(?:bara\s+|nästan\s+)?(\d{1,2})(?:\s*år)?(?!\d)"
               r"(?!\s*(?:" + _UNITS + r")\b)"),
    re.compile(r"(?:^|[^\w])(?:my age is|age|ålder)\s*[:=]?\s*(\d{1,2})(?!\d)(?!\s*(?:" + _UNITS + r")\b)"),
    re.compile(r"^\s*(\d{1,2})\s*(?:years? old|yrs? old|y/?o|år gammal)\b"),
]


def age_disclosure(text: str) -> int | None:
    """The age a person says they are ("im 13", "I'm 25 years old", "jag är 12"), or None."""
    s = text.casefold().replace("’", "'")
    for rx in _AGE_DISCLOSURE:
        m = rx.search(s)
        if m and 8 <= int(m.group(1)) <= 79:
            return int(m.group(1))
    return None


_MINOR_ROLE = re.compile(r"(?<!\d)(?:1[0-7]|[89])\s*(?:-|–|to|/)\s*1[0-7](?!\d)|under ?18|u18|<\s?18|minor|"
                         r"(?<!\d)1[0-7] ?(?:yo|y/o|years?|år)\b|^\s*1[0-7]\s*$|under ?(?:13|15|16)|kid|teen(?:ager)?s?\b|"
                         r"barn|tonåring|minderårig")
_ADULT_ROLE = re.compile(r"(?<!\d)(?:18|19|2\d)\s*\+|(?<!\d)18 ?- ?\d\d|adult|vuxen|over ?18|över ?18|18 ?or ?older")


def role_age(names: list[str]) -> str | None:
    """'minor' / 'adult' from age roles members pick (e.g. '13-15', '18+'), else None."""
    folded = [n.casefold() for n in names]
    if any(_MINOR_ROLE.search(n) for n in folded):
        return "minor"
    if any(_ADULT_ROLE.search(n) for n in folded):
        return "adult"
    return None


_DM_REQUEST = re.compile(
    r"\b(?:dm|pm|message|msg|text|inbox|snap|whisper) me\b|\bcheck (?:your |ur |yo |my )?(?:dms?|inbox|pms?)\b"
    r"|\bi (?:dm ?ed|dmd|dm d|pm ?ed|pmd|sent) (?:you|u)\b|\b(?:sent|send) (?:you|u) (?:a )?(?:dm|pm|friend request|fr)\b"
    r"|\baccept (?:my )?(?:friend )?(?:request|fr)\b|\b(?:add|friend) me\b|\bslide (?:in|into) (?:my|your|ur) dms?\b"
    r"|\bdms? (?:are |r )?open\b|\bcan i (?:dm|pm|message|text) (?:you|u)\b|\blets? (?:talk|chat) (?:in|on) dms?\b"
    r"|\b(?:skicka|skriv) (?:ett )?(?:dm|pm) (?:till mig)?\b|\bkolla (?:dina |din )?(?:dm|pm)\b|\blägg till mig\b"
    r"|\bkan jag (?:dma|dm a|skriva till) dig\b|\bjag (?:dmade|skrev till) dig\b"
)
_INVITE = re.compile(r"(?:discord\.gg|discord(?:app)?\.com/invite)/[\w-]{2,32}", re.IGNORECASE)


def context_signals(text: str) -> list[Signal]:
    """Signals Guard adds next to the message rules: DM requests and invite links."""
    out: list[Signal] = []
    if _DM_REQUEST.search(normalize(text, leet=False)):
        out.append(Signal("behave.dm_request", 12))
    if _INVITE.search(text):
        out.append(Signal("behave.invite_link", 8))
    return out


# --- member snapshot -> verdict --------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Obs:
    code: str
    weight: int
    params: dict[str, Any]
    target_id: int | None
    target_minor: bool
    channel_id: int | None
    message_id: int | None
    at: int
    deleted: bool


@dataclass(frozen=True, slots=True)
class ContactFacts:
    target_id: int
    target_minor: bool
    msgs: int
    stages: dict[str, int]  # stage -> first time seen with this target
    last_at: int


@dataclass(slots=True)
class MemberSnapshot:
    user: UserFacts
    now: int
    joined_at: int | None = None
    self_age: int | None = None
    minor: bool = False
    adult: bool = False
    status: str = "none"  # none | watch | trusted | actioned
    msg_count: int = 0
    obs: list[Obs] = field(default_factory=list)
    contacts: list[ContactFacts] = field(default_factory=list)
    reporters: int = 0
    mod_actions: int = 0
    network_guilds: int = 0
    name_changes_7d: int = 0
    raid_join: bool = False


_PROBE = {"msg.age_probe", "msg.personal_info"}
_CONTACT = {"msg.isolation", "msg.isolation_private", "behave.dm_request"}
_SEXUAL = {"msg.sexual", "msg.photo_request"}
_SPAM = {"behave.spam", "behave.mass_mention", "behave.invite_link", "behave.automod"}
_AIMED = _PROBE | _CONTACT | _SEXUAL | {"msg.secrecy", "msg.meeting", "msg.gifts", "msg.age_gap", "msg.pressure",
                                        "msg.flattery"}
# Kids ask each other's age and add each other all the time; between minors these are weak.
_PEER_NORMAL = _PROBE | _CONTACT | {"msg.flattery", "msg.gifts"}
_PROFILE_HALVED = {"person.age_hours", "person.age_days", "person.age_weeks", "person.age_months"}


def _recency(at: int, now: int) -> float:
    return max(0.35, 0.5 ** ((now - at) / DAY / 14))


def _spread(obs: list[Obs], per_unit: int, cap: int, now: int) -> tuple[int, int, int]:
    """(weight, distinct targets, minor targets) for a category where breadth matters."""
    targets: dict[int | None, bool] = {}
    for o in obs:
        targets[o.target_id] = targets.get(o.target_id, False) or o.target_minor
    minors = sum(targets.values())
    units = len(targets) + 0.5 * minors
    w = min(cap, round(per_unit * units * _recency(max(o.at for o in obs), now)))
    return w, len(targets), minors


def score_member(snap: MemberSnapshot) -> Verdict:
    now = snap.now
    sigs: list[Signal] = []

    # Profile (layer 0), at half weight for age: in a server, behaviour matters more than account age.
    for s in score_user(snap.user).signals:
        if s.code == "person.self":
            continue
        sigs.append(Signal(s.code, s.weight // 2, s.params, s.severe) if s.code in _PROFILE_HALVED else s)

    obs = [o for o in snap.obs if o.at >= now - WINDOW_DAYS * DAY]
    by_code: dict[str, list[Obs]] = defaultdict(list)
    for o in obs:
        by_code[o.code].append(o)

    def of(codes: set[str]) -> list[Obs]:
        return [o for c in codes for o in by_code.get(c, ())]

    peer = 0.4 if snap.minor else 1.0
    behaviour: list[Signal] = []
    if probe := of(_PROBE):
        w, n, m = _spread(probe, 9, 40, now)
        behaviour.append(Signal("member.probing", round(w * peer), {"n": n, "minors": m}))
    if contact := of(_CONTACT):
        w, n, m = _spread(contact, 10, 40, now)
        behaviour.append(Signal("member.contacting", round(w * peer), {"n": n, "minors": m}))
    if sexual := of(_SEXUAL):
        to_minor = any(o.target_minor for o in sexual)
        behaviour.append(Signal("member.sexual", min(55, 35 + 5 * (len(sexual) - 1) + (10 if to_minor else 0)),
                                {"n": len(sexual)}, severe=to_minor))
    for code, base, minor_bonus in (("msg.secrecy", 25, 10), ("msg.meeting", 25, 15), ("msg.gifts", 12, 8),
                                    ("msg.flattery", 6, 6), ("msg.scam_link", 25, 0)):
        if hits := by_code.get(code):
            w = base + (minor_bonus if any(o.target_minor for o in hits) else 0)
            if code in _PEER_NORMAL:
                w = round(w * peer)
            behaviour.append(Signal("member." + code.split(".", 1)[1], round(w * _recency(hits[-1].at, now)),
                                    {"n": len(hits)}))
    if hits := by_code.get("msg.pressure"):
        behaviour.append(Signal("member.pressure", 40, {"n": len(hits)}, severe=True))
    if hits := by_code.get("msg.age_gap"):
        to_minor = any(o.target_minor for o in hits)
        behaviour.append(Signal("member.age_gap", 30, {"n": len(hits)}, severe=to_minor))
    if spam := of(_SPAM):
        behaviour.append(Signal("member.spam", min(25, 8 + 4 * len(spam)), {"n": len(spam)}))
    sigs += behaviour

    # Patterns across people and over time.
    risky = of(_AIMED)
    minor_targets = {o.target_id for o in risky if o.target_minor and o.target_id}
    if snap.adult and minor_targets:
        severe = bool(of(_SEXUAL | {"msg.meeting"}) and any(o.target_minor for o in of(_SEXUAL | {"msg.meeting"})))
        sigs.append(Signal("member.adult_minor", 30, {"age": snap.self_age or 18, "n": len(minor_targets)},
                           severe=severe))
    if len(minor_targets) >= 2 and not snap.minor:
        sigs.append(Signal("member.many_minors", min(25, 10 + 5 * (len(minor_targets) - 2)),
                           {"n": len(minor_targets)}))
    if best := _worst_contact(snap.contacts):
        k = len(best.stages)
        late = {Stage(s) for s in best.stages} & _LATE_STAGES
        sigs.append(Signal("member.escalation", min(45, 20 + 10 * (k - 3)), {"stages": k},
                           severe=best.target_minor and bool(late) and not snap.minor))
    deleted = [o for o in risky if o.deleted]
    if deleted:
        sigs.append(Signal("member.deleted", min(25, 10 + 5 * (len(deleted) - 1)), {"n": len(deleted)}))

    # Other people and other servers.
    if snap.reporters:
        sigs.append(Signal("member.reported", min(45, 15 * snap.reporters), {"n": snap.reporters},
                           severe=snap.reporters >= 3))
    if snap.mod_actions:
        sigs.append(Signal("member.mod_history", min(30, 10 * snap.mod_actions), {"n": snap.mod_actions}))
    if snap.network_guilds:
        sigs.append(Signal("member.network", min(60, 35 + 15 * (snap.network_guilds - 1)), {"n": snap.network_guilds},
                           severe=snap.network_guilds >= 2))
    if snap.name_changes_7d >= 3:
        sigs.append(Signal("member.name_churn", 12, {"n": snap.name_changes_7d}))
    if snap.raid_join:
        sigs.append(Signal("member.raid", 20))

    # Context and reassurance.
    if snap.minor:
        sigs.append(Signal("member.is_minor", 0, {"age": snap.self_age} if snap.self_age else {}))
    if snap.status == "trusted":
        sigs.append(Signal("member.trusted", -40))
    member_days = (now - snap.joined_at) / DAY if snap.joined_at else 0
    clean = not any(s.weight > 0 for s in behaviour) and not snap.reporters
    if clean and member_days >= 180 and snap.msg_count >= 100:
        sigs.append(Signal("member.longtime_clean", -15, {"days": int(member_days)}))
    elif clean and snap.msg_count >= 30:
        sigs.append(Signal("member.active_clean", -5, {"n": snap.msg_count}))

    sigs = [s for s in sigs if s.weight != 0 or s.code == "member.is_minor"]
    return build_verdict(Kind.PERSON, sigs, base=MEMBER_BASE, confidence=Confidence.HIGHEST)


def _worst_contact(contacts: list[ContactFacts]) -> ContactFacts | None:
    """The contact that walked through the most grooming stages (3+), minors first."""
    hits = [c for c in contacts if len(c.stages) >= 3]
    return max(hits, key=lambda c: (len(c.stages), c.target_minor, c.last_at), default=None)


def stages_in_order(stages: dict[str, int]) -> bool:
    """True when stages were reached roughly in grooming order (the textbook progression)."""
    seen = sorted(stages, key=lambda s: stages[s])
    ranks = [STAGE_ORDER.index(Stage(s)) for s in seen if s in Stage.__members__.values()]
    return ranks == sorted(ranks) and len(ranks) >= 2


@dataclass(frozen=True, slots=True)
class Prediction:
    trajectory: str  # rising | stable | falling
    escalation: str  # none | possible | likely
    code: str
    params: dict[str, Any]


def predict(snap: MemberSnapshot, verdict: Verdict, score_7d_ago: int | None) -> Prediction:
    """Where this member is heading, from the shape of their history rather than its size."""
    delta = verdict.score - (score_7d_ago if score_7d_ago is not None else MEMBER_BASE)
    trajectory = "rising" if delta >= 8 else "falling" if delta <= -8 else "stable"

    recent = snap.now - 3 * DAY
    for c in sorted(snap.contacts, key=lambda c: -len(c.stages)):
        k = len(c.stages)
        fresh = any(t >= recent for t in c.stages.values())
        if c.target_minor and k >= 3 and fresh:
            span_days = max(1, round((max(c.stages.values()) - min(c.stages.values())) / DAY))
            return Prediction(trajectory, "likely", "predict.stages_fast", {"stages": k, "days": span_days})
        if c.target_minor and k >= 2 and stages_in_order(c.stages):
            return Prediction(trajectory, "possible", "predict.stages_order", {"stages": k})
    minors = {o.target_id for o in snap.obs if o.target_minor and o.code in _PROBE | _CONTACT}
    if len(minors) >= 2 and not snap.minor:
        return Prediction(trajectory, "possible", "predict.many_minors", {"n": len(minors)})
    if trajectory == "rising" and verdict.score >= 35:
        return Prediction(trajectory, "possible", "predict.rising", {"delta": delta})
    return Prediction(trajectory, "none", "predict.none", {})


register({
    # stages
    "stage.trust": {"en": "Trust building", "sv": "Bygger förtroende"},
    "stage.risk_check": {"en": "Risk check", "sv": "Kollar risker"},
    "stage.exclusivity": {"en": "Secrecy", "sv": "Hemlighetsmakeri"},
    "stage.isolation": {"en": "Isolation", "sv": "Isolering"},
    "stage.sexual": {"en": "Sexual content", "sv": "Sexuellt innehåll"},
    "stage.meeting": {"en": "Meeting up", "sv": "Vill träffas"},
    "stage.coercion": {"en": "Pressure/threats", "sv": "Press/hot"},
    # context signals (shown in message alerts)
    "behave.dm_request": {"en": "Asks to move the chat to DMs or add them.", "sv": "Vill flytta chatten till DM eller bli tillagd."},
    "behave.invite_link": {"en": "Posts an invite to another server.", "sv": "Lägger upp en inbjudan till en annan server."},
    "behave.spam": {"en": "Same message posted in several channels at once.", "sv": "Samma meddelande i flera kanaler samtidigt."},
    "behave.automod": {"en": "Discord AutoMod blocked one of their messages.", "sv": "Discords AutoMod blockerade ett av hens meddelanden."},
    "behave.mass_mention": {"en": "Mentions many people at once.", "sv": "Nämner många personer samtidigt."},
    "ctx.to_minor": {"en": "Aimed at a member who is under 18.", "sv": "Riktat till en medlem under 18."},
    "ctx.adult_to_minor": {"en": "Sent by a member who said they are {age}, to a member under 18.",
                           "sv": "Skickat av en medlem som sagt att hen är {age}, till en medlem under 18."},
    "ctx.peer": {"en": "Between two members who are both under 18 (lower weight).",
                 "sv": "Mellan två medlemmar som båda är under 18 (lägre vikt)."},
    "ctx.new_account": {"en": "Sender's account is {days} days old.", "sv": "Avsändarens konto är {days} dagar gammalt."},
    "ctx.watched": {"en": "Sender is on the watch list.", "sv": "Avsändaren är bevakad."},
    # member signals (admin-facing)
    "member.probing": {"en": "Asked {n} member(s) their age or personal details ({minors} under 18).",
                       "sv": "Frågade {n} medlem(mar) om ålder eller personliga uppgifter ({minors} under 18)."},
    "member.contacting": {"en": "Tried to move {n} member(s) to DMs or other apps ({minors} under 18).",
                          "sv": "Försökte flytta {n} medlem(mar) till DM eller andra appar ({minors} under 18)."},
    "member.sexual": {"en": "Sexual messages or photo requests ({n}).", "sv": "Sexuella meddelanden eller bildförfrågningar ({n})."},
    "member.secrecy": {"en": "Asked someone to keep secrets ({n}).", "sv": "Bad någon hålla hemligheter ({n})."},
    "member.meeting": {"en": "Tried to meet someone in real life ({n}).", "sv": "Försökte träffa någon på riktigt ({n})."},
    "member.gifts": {"en": "Offered gifts like Robux, Nitro or money ({n}).", "sv": "Erbjöd presenter som Robux, Nitro eller pengar ({n})."},
    "member.flattery": {"en": "Heavy flattery ({n}).", "sv": "Mycket smicker ({n})."},
    "member.scam_link": {"en": "Posted scam links ({n}).", "sv": "Lade upp bluff-länkar ({n})."},
    "member.pressure": {"en": "Pressured or threatened someone ({n}).", "sv": "Pressade eller hotade någon ({n})."},
    "member.age_gap": {"en": "Pointed out an adult/child age gap ({n}).", "sv": "Lyfte fram en åldersskillnad vuxen/barn ({n})."},
    "member.spam": {"en": "Spam: links, invites or mass mentions ({n}).", "sv": "Spam: länkar, inbjudningar eller massomnämnanden ({n})."},
    "member.adult_minor": {"en": "Says they are {age} and aimed risky messages at {n} member(s) under 18.",
                           "sv": "Säger sig vara {age} och riktade riskabla meddelanden till {n} medlem(mar) under 18."},
    "member.many_minors": {"en": "Risky contact with {n} different members under 18.",
                           "sv": "Riskabel kontakt med {n} olika medlemmar under 18."},
    "member.escalation": {"en": "One conversation went through {stages} grooming stages.",
                          "sv": "En konversation gick igenom {stages} grooming-steg."},
    "member.deleted": {"en": "Deleted {n} flagged message(s) after sending.", "sv": "Raderade {n} flaggade meddelanden efter att ha skickat dem."},
    "member.reported": {"en": "Reported by {n} different member(s).", "sv": "Anmäld av {n} olika medlem(mar)."},
    "member.mod_history": {"en": "{n} earlier moderation action(s) in this server.", "sv": "{n} tidigare moderationsåtgärd(er) i servern."},
    "member.network": {"en": "Banned for child safety in {n} other Guard server(s).",
                       "sv": "Bannad för barnsäkerhet i {n} andra Guard-server(rar)."},
    "member.name_churn": {"en": "Changed name {n} times this week.", "sv": "Bytte namn {n} gånger den här veckan."},
    "member.raid": {"en": "Joined during a join burst (possible raid).", "sv": "Gick med under en anstormning (möjlig raid)."},
    "member.is_minor": {"en": "Likely under 18 (from what they said or their roles).",
                        "sv": "Troligen under 18 (utifrån vad hen sagt eller sina roller)."},
    "member.trusted": {"en": "Marked as trusted by a moderator.", "sv": "Markerad som pålitlig av en moderator."},
    "member.longtime_clean": {"en": "Member for {days} days with no warning signs.", "sv": "Medlem i {days} dagar utan varningstecken."},
    "member.active_clean": {"en": "{n} messages with no warning signs.", "sv": "{n} meddelanden utan varningstecken."},
    # predictions
    "predict.stages_fast": {"en": "Contact with a minor moved through {stages} grooming stages in {days} day(s). Escalation is likely.",
                            "sv": "Kontakten med en minderårig gick igenom {stages} grooming-steg på {days} dag(ar). Eskalering är trolig."},
    "predict.stages_order": {"en": "Contact with a minor follows the typical grooming order ({stages} stages so far).",
                             "sv": "Kontakten med en minderårig följer det typiska grooming-mönstret ({stages} steg hittills)."},
    "predict.many_minors": {"en": "Approaching several minors ({n}) at once: a common pattern before moving one to DMs.",
                            "sv": "Närmar sig flera minderåriga ({n}) samtidigt: ett vanligt mönster innan en flyttas till DM."},
    "predict.rising": {"en": "Risk rose by {delta} points this week.", "sv": "Risken steg med {delta} poäng den här veckan."},
    "predict.none": {"en": "No sign of escalation.", "sv": "Inga tecken på eskalering."},
})
