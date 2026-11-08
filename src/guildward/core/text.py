"""Text normalisation so rules match what people actually type: leetspeak, fancy Unicode, spacing tricks.

`normalize` keeps word boundaries (spaces) so regexes can use \\b; `squash` removes all separators
for catching spaced-out evasion like "d m  m e" or "s.n.a.p".
"""

from __future__ import annotations

import re
import unicodedata

_LEET = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i"}
)
# Symbols used as letters only count when glued to a word ("$nap", "sn@p"); a trailing "!" stays punctuation.
_LEET_SYMBOL = re.compile(r"[@$!](?=\w)")
_NON_WORD = re.compile(r"[^\w\såäöæø+]+")
_SPACES = re.compile(r"\s+")
_REPEATS = re.compile(r"(.)\1{2,}")  # "heyyyy" -> "heyy"
# NFKC leaves Cyrillic/Greek look-alikes alone ("ѕnар", "αge"). Lowercase only: it runs after casefold.
_CONFUSABLES = str.maketrans(
    "авсԁеёһніїјкӏмпорԛгѕтуүхԝь" "αβεηικνορτυχγμω",
    "abcdeehhiijklmnopqrstyyxwb" "abenikvoptuxyuw",
)


def _fold(text: str) -> str:
    # NFKC turns fullwidth/mathematical letters (𝓭𝓶 𝓶𝓮) into plain ones; casefold handles ß etc.
    return unicodedata.normalize("NFKC", text).casefold().translate(_CONFUSABLES)


def fold(text: str) -> str:
    """Lowercased, Unicode-folded, repeats squeezed; punctuation, digits and spacing kept (for the model)."""
    return _REPEATS.sub(r"", _fold(text))


def normalize(text: str, *, leet: bool = True) -> str:
    """Lowercased, Unicode-folded text with punctuation turned into spaces. Digits kept unless leet."""
    s = _fold(text)
    s = _REPEATS.sub(r"\1\1", s)
    if leet:
        s = _LEET_SYMBOL.sub(lambda m: m.group().translate(_LEET), s)
    s = _NON_WORD.sub(" ", s.replace("_", " "))
    if leet:
        s = s.translate(_LEET)
    return _SPACES.sub(" ", s).strip()


def squash(text: str) -> str:
    """normalize() with every separator removed: 'd.m m-e' -> 'dmme'."""
    return re.sub(r"[\s_]+", "", normalize(text))


def possible_ages(text: str) -> list[int]:
    """Numbers in the 5..99 range that could be ages, from the raw (non-leet) text."""
    return [int(n) for n in re.findall(r"(?<!\d)(\d{1,2})(?!\d)", _fold(text)) if 5 <= int(n) <= 99]
