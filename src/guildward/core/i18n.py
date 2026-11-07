"""Tiny translation layer: English + Swedish.

Each module that emits Signals registers its own catalog at import, so strings live next to the
rules that produce them. `missing_translations()` lets tests guarantee every key has every language.
"""

from __future__ import annotations

from typing import Literal

Lang = Literal["en", "sv"]
LANGS: tuple[Lang, ...] = ("en", "sv")

Catalog = dict[str, dict[Lang, str]]
_catalog: Catalog = {}


def register(catalog: Catalog) -> None:
    dupes = catalog.keys() & _catalog.keys()
    if dupes:
        raise ValueError(f"duplicate i18n keys: {sorted(dupes)}")
    _catalog.update(catalog)


def lang_for(locale: object) -> Lang:
    """Discord locale (e.g. discord.Locale.swedish -> 'sv-SE') to a supported language."""
    return "sv" if str(locale or "").lower().startswith("sv") else "en"


def t(key: str, lang: Lang, /, **params: object) -> str:
    entry = _catalog.get(key)
    if entry is None:
        return key  # visible in output, caught by tests
    text = entry.get(lang) or entry["en"]
    return text.format(**params) if params else text


def has(key: str) -> bool:
    return key in _catalog


def missing_translations() -> list[str]:
    return [f"{k}:{lang}" for k, v in _catalog.items() for lang in LANGS if not v.get(lang)]
