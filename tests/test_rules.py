"""Public side of the rule split: loader behaviour, example rules sanity, every msg.* code translated."""

import re

import pytest

from guildward.core.i18n import LANGS, has, missing_translations, t
from guildward.core.models import Confidence, Kind, Level, build_verdict
from guildward.intel import rules as rules_mod
from guildward.intel.message import MESSAGE_BASE, analyze_message


def level(text: str) -> Level:
    return build_verdict(Kind.MESSAGE, analyze_message(text), base=MESSAGE_BASE, confidence=Confidence.LOW).level


@pytest.mark.parametrize(("text", "want"), [
    ("gg that was close", Level.GREEN),
    ("my snap score is 400k lol", Level.GREEN),
    ("how old are you?", Level.YELLOW),
    ("add me on snap and dont tell your parents", Level.RED),
    ("skicka en bild på dig", Level.YELLOW),
    ("hur gammal e du? lägg till mig på snap", Level.RED),
])
def test_loaded_rules_catch_the_blatant_cases(text, want):
    # Holds for the example set and must keep holding for the private set.
    assert level(text) is want or (want is Level.YELLOW and level(text) is Level.RED)


def test_every_message_code_is_translated_and_never_echoes_input():
    assert missing_translations() == []
    text = "how old are you, add me on snap, dont tell your parents, send a pic of you, where do you live, free nitro"
    sigs = analyze_message(text)
    assert len(sigs) >= 6
    for s in sigs:
        assert has(s.code), s.code
        assert all(str(v) not in text for v in s.params.values() if len(str(v)) > 8)
        for lang in LANGS:
            assert not re.search(r"\{\w+\}", t(s.code, lang, **s.params))


def test_missing_private_dir_fails_loudly(monkeypatch, tmp_path):
    rules_mod.rules.cache_clear()
    monkeypatch.setenv("GUILDWARD_PRIVATE", str(tmp_path / "nope"))
    with pytest.raises(RuntimeError, match="not a directory"):
        rules_mod.rules()
    monkeypatch.setenv("GUILDWARD_PRIVATE", str(tmp_path))  # exists, but no package in it
    with pytest.raises((ModuleNotFoundError, RuntimeError)):  # RuntimeError if a copy is installed elsewhere
        rules_mod.rules()
    monkeypatch.delenv("GUILDWARD_PRIVATE")
    rules_mod.rules.cache_clear()
