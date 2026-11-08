"""Public example rule set: catches only the most blatant cases.

It exists so the open-source code runs, tests pass and self-hosters get something useful. The real
rules (evasion handling, Swedish slang, context, false-positive guards, weights tuned on a labeled
corpus) are in the private `guildward_private.rules` package. Keep this set obvious on purpose.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import MappingProxyType

from guildward.core.models import Signal
from guildward.core.text import normalize
from guildward.intel.patterns import NameFlag


def _rx(*parts: str) -> re.Pattern[str]:
    return re.compile(r"(?<![a-zåäö])(?:" + "|".join(parts) + r")(?![a-zåäö])")


# Classifier head for the local message model (intel/semantic.py), trained on a few obvious public examples by
# tools/train_example_head.py. The private set ships the real one.
SEMANTIC_HEAD = Path(__file__).with_name("example_head.npz")

NAME_PATTERNS: dict[NameFlag, re.Pattern[str]] = {
    NameFlag.ADULT: _rx(r"nsfw", r"18 ?\+", r"porn\w*", r"hentai", r"nudes?", r"horny", r"xxx"),
    NameFlag.DATING: _rx(r"e ?dating", r"dating", r"dejt\w*", r"lf ?(?:bf|gf)"),
    NameFlag.DM_BAIT: _rx(r"dms? (?:are )?open", r"open dms?", r"dm me"),
    NameFlag.MINOR_BAIT: _rx(r"1[0-7] ?[fm]", r"jail ?bait"),
    NameFlag.TEEN: _rx(r"teens?", r"kids?", r"tonåringar", r"barn"),
    NameFlag.IMPERSONATION: _rx(r"discord ?(?:staff|support|team)", r"free ?nitro", r"giveaways?"),
}

_APPS = {"snap": "Snapchat", "snapchat": "Snapchat", "insta": "Instagram", "instagram": "Instagram",
         "telegram": "Telegram", "whatsapp": "WhatsApp", "kik": "Kik"}
_ISOLATION = re.compile(
    r"\b(?:add|text|message|dm|hit) me (?:up )?on (?P<app>" + "|".join(_APPS) + r")\b"
    r"|\blägg till mig på (?P<app_sv>" + "|".join(_APPS) + r")\b"
)

# (code, weight, pattern); each code fires once.
_RULES: tuple[tuple[str, int, re.Pattern[str]], ...] = (
    ("msg.age_probe", 30, re.compile(r"\bhow old (?:are|r) (?:you|u)\b|\bhur gammal (?:är|e) (?:du|u)\b")),
    ("msg.secrecy", 45, re.compile(r"\b(?:don t|dont|do not) tell (?:your|ur) (?:parents|mom|dad)\b"
                                   r"|\bour (?:little )?secret\b"
                                   r"|\bsäg inte till (?:dina|din) (?:föräldrar|mamma|pappa)\b")),
    ("msg.photo_request", 55, re.compile(r"\bsend (?:me )?(?:a )?(?:pic|photo|selfie)s? of (?:you|u|yourself)\b"
                                         r"|\bskicka (?:en )?bild på dig\b")),
    ("msg.meeting", 35, re.compile(r"\bwhere do (?:you|u) live\b|\bvar bor (?:du|u)\b")),
    ("msg.scam_link", 40, re.compile(r"\bfree (?:nitro|robux)\b|\bnitro gift\b")),
)
_SCAMS = {"msg.scam_link"}


def analyze_message(text: str) -> tuple[Signal, ...]:
    s = normalize(text)
    found = [Signal(code, weight) for code, weight, rx in _RULES if rx.search(s)]
    if m := _ISOLATION.search(s):
        found.append(Signal("msg.isolation", 30, MappingProxyType({"app": _APPS[m["app"] or m["app_sv"]]})))
    if sum(sig.code not in _SCAMS for sig in found) >= 2:
        found.append(Signal("msg.multi_stage", 20))
    return tuple(found)
