"""'I need help' content: every screen renders in both languages inside Discord's limits, links are https."""

import asyncio
import re
from datetime import UTC, datetime, timedelta, timezone

import discord
import pytest

from guildward.bot import help as h
from guildward.bot import helplines as hl
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
            select = item.item if isinstance(item, h.RegionPicker) else item
            assert isinstance(select, discord.ui.Select)
            assert (select.custom_id == h.PICK_ID.format(lang=lang)
                    or select.custom_id.startswith(f"gw:help:where:{lang}:"))
            assert len(select.custom_id) <= 100
            assert len(select.options) <= 25 and len(select.placeholder) <= 150
            for o in select.options:
                assert 0 < len(o.label) <= 100 and len(o.description or "") <= 100
    assert v.is_persistent()


def test_i18n_complete():
    assert missing_translations() == []


EMERGENCY = {"se": "112", "us": "911", "gb": "999", "au": "000", "ca": "911"}


@pytest.mark.parametrize("lang", LANGS)
def test_menu(lang):
    embed, view = _run(h.help_menu, lang)
    _assert_limits(embed)
    _assert_view(view, lang)
    if lang == "sv":  # Swedish speakers start on Sweden
        assert "112" in embed.description and "116 111" in embed.description
    else:  # everyone else starts on help that works anywhere, until they pick a country
        assert "emergency number" in embed.description and "116 111" not in embed.description
    picker = next(i for i in view.children if isinstance(i, discord.ui.Select))
    assert [o.value for o in picker.options] == [*h.SITUATIONS, h.SETTINGS]
    where = next(i for i in view.children if isinstance(i, h.RegionPicker))
    assert [o.value for o in where.item.options] == list(hl.REGIONS)


@pytest.mark.parametrize("region", hl.REGIONS)
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("key", h.SITUATIONS)
def test_every_situation_in_every_country(key, lang, region):
    embed, view = _run(h.situation_embed, key, lang, region)
    _assert_limits(embed)
    _assert_view(view, lang)
    text = embed.description + embed.fields[0].value
    assert "{" not in text and "}" not in text, "unfilled placeholder"
    if region in EMERGENCY:
        assert EMERGENCY[region] in embed.fields[0].value
    if region != "se":  # no Swedish numbers outside Sweden
        assert "116 111" not in text and "114 14" not in text and "90101" not in text
    assert sum(isinstance(i, discord.ui.Button) for i in view.children) >= 3


@pytest.mark.parametrize("region", hl.REGIONS)
@pytest.mark.parametrize("lang", LANGS)
def test_sextortion_follows_guidance(lang, region):
    embed, view = _run(h.situation_embed, "threat", lang, region)
    text = embed.description.lower()
    musts = {"en": ("don't pay", "don't delete", "screenshot", "block", "report", "adult", "not your fault",
                    "take it down", "police"),
             "sv": ("betala inte", "radera inte", "skärmdump", "blockera", "rapportera", "vuxen", "inte ditt fel",
                    "take it down", "polis")}[lang]
    for m in musts:
        assert m in text, m
    urls = {b.url for b in view.children if isinstance(b, discord.ui.Button)}
    assert any("takeitdown.ncmec.org" in u for u in urls)
    want = {"se": "bris.se", "us": "988lifeline.org", "gb": "childline.org.uk", "au": "kidshelpline.com.au",
            "ca": "kidshelpphone.ca", "intl": "childhelplineinternational.org"}[region]
    assert any(want in u for u in urls), urls
    assert ("https://discord.com/report" in urls) == (region == "se")  # Discord's EU form, Sweden only


def test_region_picker_saves_and_redraws():
    class Pocket:
        def __init__(self):
            self.saved = {}

        def touch_user(self, uid, lang):
            pass

        def set_region(self, uid, region):
            self.saved[uid] = region

        def region(self, uid):
            return self.saved.get(uid)

    async def go():
        pocket, seen = Pocket(), {}
        picker = h.RegionPicker("en", "threat", "intl")
        picker.item._values = ["gb"]

        async def edit_message(**kw):
            seen.update(kw)

        inter = type("I", (), {"client": type("C", (), {"pocket": pocket})(), "user": type("U", (), {"id": 7})(),
                               "response": type("R", (), {"edit_message": staticmethod(edit_message)})()})()
        await picker.callback(inter)
        return pocket, seen
    pocket, seen = asyncio.run(go())
    assert pocket.saved == {7: "gb"}
    assert "999" in seen["embed"].fields[0].value and "0800 1111" in seen["embed"].description
    assert hl.region_for(type("B", (), {"pocket": pocket})(), 7, "sv") == "gb"  # the pick beats the language
    assert hl.region_for(object(), 7, "sv") == "se" and hl.region_for(object(), 7, "en") == "intl"


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

        inter = type("I", (), {"client": object(), "user": type("U", (), {"id": 1})(),
                               "response": type("R", (), {"edit_message": staticmethod(edit_message)})()})()
        await picker.callback(inter)
        return seen
    seen = asyncio.run(go())
    assert seen["embed"].title.endswith(t("help.scam.title", "sv"))
    assert isinstance(seen["view"], discord.ui.View)


def test_persistent_views():
    views = _run(h.persistent_views)
    assert [v.children[0].custom_id for v in views] == [h.PICK_ID.format(lang=lang) for lang in LANGS]
    assert all(v.is_persistent() for v in views)


@pytest.mark.parametrize("region", hl.REGIONS)
@pytest.mark.parametrize("lang", LANGS)
def test_quick_links(lang, region):
    links = h.quick_links(lang, region)
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
