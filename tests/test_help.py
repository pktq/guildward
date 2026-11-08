"""'I need help' content: every screen renders in both languages inside Discord's limits, links are https."""

import asyncio
import re
from datetime import UTC, datetime, timedelta, timezone

import discord
import pytest

from guildward.bot import help as h
from guildward.core.i18n import LANGS, missing_translations, t


def _run(fn, *a, **kw):
    async def go():
        return fn(*a, **kw)
    return asyncio.run(go())  # discord.py views want a running loop


def _assert_limits(e: discord.Embed) -> None:
    assert e.title and len(e.title) <= 256
    assert len(e.description or "") <= 4096
    assert len(e.fields) <= 25
    for f in e.fields:
        assert 0 < len(f.name) <= 256 and 0 < len(f.value) <= 1024
    assert len(e.footer.text or "") <= 2048
    assert len(e) <= 6000
    assert not re.search(r"help\.\w", str(e.to_dict())), "untranslated key leaked into output"


def _assert_view(v: discord.ui.View, lang: str) -> None:
    assert len(v.children) <= 25
    for item in v.children:
        if isinstance(item, discord.ui.Button):
            assert item.url and item.url.startswith("https://"), item.url
            assert 0 < len(item.label) <= 80
        else:
            assert isinstance(item, discord.ui.Select)
            assert item.custom_id == h.PICK_ID.format(lang=lang)
            assert len(item.options) <= 25 and len(item.placeholder) <= 150
            for o in item.options:
                assert 0 < len(o.label) <= 100 and len(o.description or "") <= 100
    assert v.is_persistent()


def test_i18n_complete():
    assert missing_translations() == []


@pytest.mark.parametrize("lang", LANGS)
def test_menu(lang):
    embed, view = _run(h.help_menu, lang)
    _assert_limits(embed)
    _assert_view(view, lang)
    assert "112" in embed.description and "116 111" in embed.description
    picker = next(i for i in view.children if isinstance(i, discord.ui.Select))
    assert [o.value for o in picker.options] == [*h.SITUATIONS, h.SETTINGS]


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("key", h.SITUATIONS)
def test_every_situation(key, lang):
    embed, view = _run(h.situation_embed, key, lang)
    _assert_limits(embed)
    _assert_view(view, lang)
    assert "112" in embed.fields[0].value
    assert sum(isinstance(i, discord.ui.Button) for i in view.children) >= 3


@pytest.mark.parametrize("lang", LANGS)
def test_sextortion_follows_guidance(lang):
    embed, view = _run(h.situation_embed, "threat", lang)
    text = embed.description.lower()
    musts = {"en": ("don't pay", "don't delete", "screenshot", "block", "report", "adult", "not your fault",
                    "take it down", "114 14"),
             "sv": ("betala inte", "radera inte", "skärmdump", "blockera", "rapportera", "vuxen", "inte ditt fel",
                    "take it down", "114 14")}[lang]
    for m in musts:
        assert m in text, m
    urls = {b.url for b in view.children if isinstance(b, discord.ui.Button)}
    assert any("takeitdown.ncmec.org" in u for u in urls)
    assert any("bris.se" in u for u in urls)
    assert ("https://report.cybertip.org/" in urls) == (lang == "en")


@pytest.mark.parametrize("lang", LANGS)
def test_settings(lang):
    embed, view = _run(h.settings_embed, lang)
    _assert_limits(embed)
    _assert_view(view, lang)


def test_situation_for_routes_and_falls_back():
    assert _run(h.situation_for, "settings", "en")[0].title == _run(h.settings_embed, "en")[0].title
    assert _run(h.situation_for, "nonsense", "sv")[0].title == _run(h.situation_embed, "other", "sv")[0].title
    with pytest.raises(KeyError):
        _run(h.situation_embed, "nonsense", "en")


def test_picker_callback_edits_message():
    async def go():
        _, view = h.help_menu("sv")
        picker = next(i for i in view.children if isinstance(i, discord.ui.Select))
        picker._values = ["scam"]  # what discord.py sets from the interaction payload
        seen = {}

        async def edit_message(**kw):
            seen.update(kw)

        inter = type("I", (), {"response": type("R", (), {"edit_message": staticmethod(edit_message)})()})()
        await picker.callback(inter)
        return seen
    seen = asyncio.run(go())
    assert seen["embed"].title.endswith(t("help.scam.title", "sv"))
    assert isinstance(seen["view"], discord.ui.View)


def test_persistent_views():
    views = _run(h.persistent_views)
    assert [v.children[0].custom_id for v in views] == [h.PICK_ID.format(lang=lang) for lang in LANGS]
    assert all(v.is_persistent() for v in views)


@pytest.mark.parametrize("lang", LANGS)
def test_quick_links(lang):
    links = h.quick_links(lang)
    assert 2 <= len(links) <= 3
    for label, url in links:
        assert 0 < len(label) <= 80 and url.startswith("https://") and not label.startswith("help.")


def _evidence(**over):
    kw = dict(lang="en", sender_name="evil_*guy*", sender_id=123456789012345678,
              sender_created=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
              message_url="https://discord.com/channels/@me/1/2", sent_at=datetime(2026, 11, 6, 21, 30),
              excerpt="send pics **now** or else")
    return h.evidence_embed(**(kw | over))


def test_evidence_fields_and_escaping():
    e = _evidence()
    _assert_limits(e)
    body = "\n".join(f.value for f in e.fields)
    assert "```\n123456789012345678\n```" in body
    assert r"evil\_\*guy\*" in body
    assert r"\*\*now\*\*" in body
    assert "https://discord.com/channels/@me/1/2" in body
    assert "2026-10-01 12:00 UTC" in body and "2026-11-06 21:30 UTC" in body  # naive treated as UTC


def test_evidence_converts_timezones_and_skips_missing():
    cet = timezone(timedelta(hours=1))
    e = _evidence(sender_created=datetime(2026, 10, 1, 13, 0, tzinfo=cet), sent_at=None, excerpt=None,
                  message_url="javascript:alert(1)", lang="sv")
    _assert_limits(e)
    body = "\n".join(f.value for f in e.fields)
    assert "2026-10-01 12:00 UTC" in body
    assert "javascript" not in body
    assert len(e.fields) == 3  # sender, created, how to save


@pytest.mark.parametrize("raw", ["a" * 2000, "*_" * 1000, "`" * 900 + "x", "@everyone " * 200])
def test_evidence_excerpt_truncated_after_escaping(raw):
    e = _evidence(excerpt=raw)
    _assert_limits(e)
    excerpt = next(f.value for f in e.fields if f.name == t("help.ev.excerpt", "en"))
    assert len(excerpt) <= h.MAX_EXCERPT
    assert excerpt.endswith("…")
    assert "@everyone" not in excerpt


def test_evidence_worst_case_still_fits():
    e = _evidence(sender_name="*" * 200, excerpt="|" * 5000)
    _assert_limits(e)
