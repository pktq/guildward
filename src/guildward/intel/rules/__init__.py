"""Loads the detection rule set: private in production, public example otherwise.

The code that *uses* rules is open source; the rules themselves (exact patterns, weights and the
labeled test corpus) live in the private `guildward_private.rules` package, so abusers can't read them and
phrase around them. Detection runs on our server, so the private rules never reach users either.

Resolution order:
1. `GUILDWARD_PRIVATE=<dir>` env var: <dir> is put on sys.path and `guildward_private.rules` must import from it.
2. `guildward_private.rules` already importable (installed in the environment).
3. `guildward.intel.rules.example`: small public set, enough for tests, CI and self-hosting.

A rule set is any module with:
    analyze_message(text: str) -> Iterable[Signal]       # codes "msg.*", translated in intel/message.py
    NAME_PATTERNS: Mapping[NameFlag, re.Pattern[str]]   # matched against normalized names
"""

from __future__ import annotations

import importlib
import os
import sys
from functools import cache
from types import ModuleType

PRIVATE = "guildward_private.rules"
_REQUIRED = ("analyze_message", "NAME_PATTERNS")


@cache
def rules() -> ModuleType:
    path = os.environ.get("GUILDWARD_PRIVATE", "").strip()
    if path:
        if not os.path.isdir(path):
            raise RuntimeError(f"GUILDWARD_PRIVATE={path!r} is not a directory")
        sys.path.insert(0, path)
    try:
        mod = importlib.import_module(PRIVATE)
    except ModuleNotFoundError as e:
        # A broken private package (or a wrong GUILDWARD_PRIVATE) must fail loudly, not degrade silently.
        if e.name not in (PRIVATE, PRIVATE.split(".")[0]) or path:
            raise
        mod = importlib.import_module(f"{__name__}.example")
    if path and not os.path.abspath(mod.__file__ or "").startswith(os.path.abspath(path)):
        raise RuntimeError(f"GUILDWARD_PRIVATE={path!r} has no {PRIVATE}; another copy was found at {mod.__file__}")
    missing = [a for a in _REQUIRED if not hasattr(mod, a)]
    if missing:
        raise RuntimeError(f"rule set {mod.__name__} lacks {missing}")
    return mod


def is_private() -> bool:
    return rules().__name__ == PRIVATE
