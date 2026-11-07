"""Red-flag categories for *names*: server names, descriptions, channel names, usernames, bios.

Messages have their own, conversation-oriented rules in intel/message.py. Names are short and
deliberate, so a hit here says something about what the space or person advertises.
The patterns themselves come from the loaded rule set (intel/rules).
"""

from __future__ import annotations

from enum import StrEnum

from guildward.core.text import normalize
from guildward.intel.rules import rules


class NameFlag(StrEnum):
    ADULT = "adult"  # sexual / 18+ content advertised
    DATING = "dating"  # e-dating, bf/gf hunting
    DM_BAIT = "dm_bait"  # "dms open", "add me"
    MINOR_BAIT = "minor_bait"  # advertises young ages next to adult themes, or known abuse slang
    TEEN = "teen"  # mentions teens/kids; harmless alone, dangerous next to ADULT/DATING
    IMPERSONATION = "impersonation"  # fake staff / giveaway / famous creator


def flags_in(*texts: str | None) -> frozenset[NameFlag]:
    found: set[NameFlag] = set()
    for text in texts:
        if not text:
            continue
        # Plain pass keeps digits ("18+", "13f"); leet pass catches "n5fw", "s3xy".
        hay = f"{normalize(text, leet=False)} | {normalize(text)}"
        found.update(flag for flag, rx in rules().NAME_PATTERNS.items() if rx.search(hay))
    return frozenset(found)
