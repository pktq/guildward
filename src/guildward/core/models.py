"""Shared result types. Every check (server, person, message) produces a Verdict built from Signals.

A Signal is one observed fact with a weight: positive raises risk, negative is reassuring.
Signals carry an i18n code + params, never display text, so the same verdict renders in any language.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from types import MappingProxyType

# Score bands, shared by every kind of check so green/yellow/red mean the same thing everywhere.
YELLOW_AT = 35
RED_AT = 65
# A severe signal (e.g. a server Discord itself marks 18+) forces red whatever else is true.
SEVERE_FLOOR = 75


class Level(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class Confidence(IntEnum):
    """How much data backs the score. Maps to the proposal's layers (L0 outside view .. L3 content)."""

    LOW = 1  # L0: outside view only (invite lookup, public profile)
    MEDIUM = 2  # L1: crowd reports / network data
    HIGH = 3  # L2: admin-invited structural audit
    HIGHEST = 4  # L3: admin-invited content audit


class Kind(StrEnum):
    SERVER = "server"
    PERSON = "person"
    MESSAGE = "message"


@dataclass(frozen=True, slots=True)
class Signal:
    code: str  # i18n key, e.g. "server.age_new"
    weight: int  # +risk / -reassuring
    params: Mapping[str, str | int] = field(default_factory=lambda: MappingProxyType({}))
    severe: bool = False

    @property
    def is_risk(self) -> bool:
        return self.weight > 0


@dataclass(frozen=True, slots=True)
class Verdict:
    kind: Kind
    score: int  # 0-100 threat
    level: Level
    confidence: Confidence
    signals: tuple[Signal, ...]  # strongest first

    @property
    def risks(self) -> tuple[Signal, ...]:
        return tuple(s for s in self.signals if s.weight > 0)

    @property
    def reassurances(self) -> tuple[Signal, ...]:
        return tuple(s for s in self.signals if s.weight < 0)


def level_for(score: int) -> Level:
    if score >= RED_AT:
        return Level.RED
    if score >= YELLOW_AT:
        return Level.YELLOW
    return Level.GREEN


def build_verdict(
    kind: Kind, signals: Iterable[Signal], *, base: int, confidence: Confidence
) -> Verdict:
    sigs = tuple(sorted(signals, key=lambda s: (not s.severe, -abs(s.weight))))
    score = base + sum(s.weight for s in sigs)
    if any(s.severe for s in sigs):
        score = max(score, SEVERE_FLOOR)
    score = max(0, min(100, score))
    return Verdict(kind, score, level_for(score), confidence, sigs)
