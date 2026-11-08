"""Shared flags: what every Guildward user's checks and reports say about one account.

An account many kids independently find sketchy gets flagged for the next kid. Brigading an innocent
classmate is blunted three ways: new reporter accounts count little or nothing, reports fade (90-day
half-life), and "flagged" needs evidence beyond reports (red checks, a Guard ban, or a strong alt link).
Only the owner or a Guard child-safety ban can confirm; only the owner can clear.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from guildward.core.i18n import register
from guildward.core.models import Signal

REPORT_REASONS = ("age_pics", "sexual", "threat", "meet", "scam", "hate", "other")
FLAG_LEVELS = ("none", "watch", "flagged", "confirmed", "cleared")
_STICKY = ("confirmed", "cleared")
_BAD = ("flagged", "confirmed")

DAY = 86_400
HALF_LIFE_DAYS = 90
LIVE_REPORT = 0.1  # decayed weight below this no longer counts as a report

WATCH_SCORE = 1.75  # two full-weight reports within ~5 weeks
WATCH_MIN_REPORTS = 2
WATCH_RED_CHECKERS = 3
FLAG_SCORE = 2.75  # three full-weight reports within ~5 weeks
FLAG_MIN_REPORTS = 3
FLAG_RED_CHECKERS = 2
NAME_CHURN = 3

_RANK = ("strong", "medium", "weak")
_STRENGTH = {"handle": "strong", "payment": "strong", "script": "medium", "avatar": "weak", "name": "weak"}


@dataclass(frozen=True, slots=True)
class Report:
    weight: float  # reporter_weight() at report time
    at: int  # unix seconds
    reason: str


@dataclass(frozen=True, slots=True)
class Link:
    kind: str  # handle|payment|script|avatar|name
    other_id: int
    other_level: str  # none|watch|flagged|confirmed|cleared


@dataclass(frozen=True, slots=True)
class CrowdFacts:
    user_id: int
    now: int
    checkers: int = 0  # distinct Guildward users who checked it
    red_checkers: int = 0  # ... and got red
    reports: tuple[Report, ...] = ()
    flag: str = "none"
    network_guilds: int = 0  # Guard servers that banned it for child safety
    links: tuple[Link, ...] = ()
    deleted: bool = False
    name_changes_30d: int = 0


def reporter_weight(reporter_account_days: float, reporter_flag: str) -> float:
    if reporter_flag in _BAD:
        return 0.0
    d = reporter_account_days
    w = 0.0 if d < 7 else 0.25 if d < 30 else 0.6 if d < 365 else 1.0
    return w / 2 if reporter_flag == "watch" else w


def _decayed(r: Report, now: int) -> float:
    return r.weight * 0.5 ** (max(0, now - r.at) / (HALF_LIFE_DAYS * DAY))


def report_score(reports: Iterable[Report], now: int) -> float:
    return sum(_decayed(r, now) for r in reports)


def _live(f: CrowdFacts) -> list[tuple[Report, float]]:
    return [(r, w) for r in f.reports if (w := _decayed(r, f.now)) >= LIVE_REPORT]


def link_strength(kind: str) -> str:
    return _STRENGTH.get(kind, "weak")


def _bad_links(links: Iterable[Link]) -> list[tuple[str, str, str]]:
    """(other_level, combined strength, best kind) per flagged/confirmed account. Two weak kinds make a medium."""
    kinds: dict[int, set[str]] = defaultdict(set)
    level: dict[int, str] = {}
    for ln in links:
        if ln.other_level in _BAD:
            kinds[ln.other_id].add(ln.kind)
            if level.get(ln.other_id) != "confirmed":
                level[ln.other_id] = ln.other_level
    out = []
    for other, ks in kinds.items():
        best = sorted(ks, key=lambda k: (_RANK.index(link_strength(k)), k))
        top = link_strength(best[0])
        weak = sum(link_strength(k) == "weak" for k in ks)
        s = "medium" if top == "weak" and weak >= 2 else top
        out.append((level[other], s, best[0]))
    return out


def auto_flag(f: CrowdFacts) -> str:
    """none|watch|flagged from the crowd. confirmed/cleared were set by a person and are returned unchanged."""
    if f.flag in _STICKY:
        return f.flag
    live = _live(f)
    score = sum(w for _, w in live)
    corroborated = (
        f.red_checkers >= FLAG_RED_CHECKERS
        or f.network_guilds >= 1
        # Only a human-confirmed account corroborates; auto-flags chaining via planted handles could frame people.
        or any(s == "strong" and lv == "confirmed" for lv, s, _ in _bad_links(f.links))
    )
    if score >= FLAG_SCORE and len(live) >= FLAG_MIN_REPORTS and corroborated:
        return "flagged"
    if (score >= WATCH_SCORE and len(live) >= WATCH_MIN_REPORTS) or f.red_checkers >= WATCH_RED_CHECKERS:
        return "watch"
    return "none"


def crowd_signals(f: CrowdFacts) -> list[Signal]:
    sigs: list[Signal] = []
    if f.deleted:
        sigs.append(Signal("crowd.deleted", 0))
    level = auto_flag(f)
    if level == "cleared":
        return sigs  # the owner reviewed it: no crowd or network warnings
    if f.network_guilds > 0:
        n = f.network_guilds
        sigs.append(Signal("crowd.network", 35 + 15 * (n - 1), {"count": n}, severe=n >= 2))

    live = _live(f)
    params: dict[str, str | int] = {"reports": len(live)}
    if live:
        by_reason: Counter[str] = Counter()
        for r, w in live:
            by_reason[r.reason] += w
        params["reason"] = by_reason.most_common(1)[0][0]
    if level == "confirmed":
        sigs.append(Signal("crowd.confirmed", 60, params, severe=True))
    elif level == "flagged":
        sigs.append(Signal("crowd.flagged", 40, params))
    elif level == "watch":
        sigs.append(Signal("crowd.watch", 20, params))

    if f.red_checkers >= WATCH_RED_CHECKERS:
        weight = min(30, 15 + 5 * (f.red_checkers - WATCH_RED_CHECKERS))
        sigs.append(Signal("crowd.red_checks", weight, {"count": f.red_checkers}))

    links = _bad_links(f.links)
    strong = [x for x in links if x[1] == "strong"]
    medium = [x for x in links if x[1] == "medium"]
    if strong:
        confirmed = any(lv == "confirmed" for lv, _, _ in strong)
        sigs.append(Signal("crowd.linked", 30, {"count": len(strong), "kind": strong[0][2]}, severe=confirmed))
    elif medium:
        sigs.append(Signal("crowd.linked_similar", 15, {"count": len(medium), "kind": medium[0][2]}))

    if f.name_changes_30d >= NAME_CHURN:
        sigs.append(Signal("crowd.name_churn", 10, {"count": f.name_changes_30d}))
    return sigs


register({
    "crowd.confirmed": {
        "en": "Guildward has confirmed this account is not safe for kids. Block it and don't send it anything.",
        "sv": "Guildward har bekräftat att kontot inte är säkert för barn. Blockera det och skicka ingenting till det.",
    },
    "crowd.flagged": {
        "en": "{reports} other Guildward users said this account made them feel unsafe or uncomfortable, and other checks back them up.",
        "sv": "{reports} andra Guildward-användare har sagt att kontot fick dem att känna sig otrygga eller obekväma, och andra kontroller stöder det.",
    },
    "crowd.watch": {
        "en": "Some other Guildward users reported this account or got a warning about it. Be careful.",
        "sv": "Några andra Guildward-användare har anmält kontot eller fått en varning om det. Var försiktig.",
    },
    "crowd.network": {
        "en": "Moderators banned this account from their servers to protect kids. Servers that did this: {count}.",
        "sv": "Moderatorer har bannat kontot från sina servrar för att skydda barn. Antal servrar: {count}.",
    },
    "crowd.red_checks": {
        "en": "{count} other Guildward users got a red warning when they checked this account.",
        "sv": "{count} andra Guildward-användare fick en röd varning när de kollade kontot.",
    },
    "crowd.linked": {
        "en": "This account uses the same contact info (like a Snapchat name, phone number or payment tag) as an account Guildward warns about. It may be the same person.",
        "sv": "Kontot använder samma kontaktuppgifter (som ett Snapchat-namn, telefonnummer eller betalnamn) som ett konto Guildward varnar för. Det kan vara samma person.",
    },
    "crowd.linked_similar": {
        "en": "This account sends the same messages, or has the same picture and name, as an account Guildward warns about. It might be the same person.",
        "sv": "Kontot skickar samma meddelanden, eller har samma bild och namn, som ett konto Guildward varnar för. Det kan vara samma person.",
    },
    "crowd.name_churn": {
        "en": "This account changed its name {count} times in the last month. That can be a way to hide who they are.",
        "sv": "Kontot har bytt namn {count} gånger den senaste månaden. Det kan vara ett sätt att dölja vem man är.",
    },
    "crowd.deleted": {
        "en": "This account has been deleted.",
        "sv": "Kontot har raderats.",
    },
    # Report-button labels, written as the kid's own words.
    "crowd.reason.age_pics": {"en": "Asked how old I am or for pictures", "sv": "Frågade hur gammal jag är eller bad om bilder"},
    "crowd.reason.sexual": {"en": "Said sexual things", "sv": "Sa sexuella saker"},
    "crowd.reason.threat": {"en": "Threatened me", "sv": "Hotade mig"},
    "crowd.reason.meet": {"en": "Wanted to meet in real life", "sv": "Ville träffas på riktigt"},
    "crowd.reason.scam": {"en": "Tried to scam me", "sv": "Försökte lura mig"},
    "crowd.reason.hate": {"en": "Was hateful or bullied me", "sv": "Var elak eller mobbade mig"},
    "crowd.reason.other": {"en": "Something else felt wrong", "sv": "Något annat kändes fel"},
})
