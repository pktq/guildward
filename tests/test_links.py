"""Link checker: static rules, SSRF refusal on redirects (fake resolver/session, no internet), RDAP, i18n."""

import asyncio
import json
import string
from datetime import UTC, datetime

import pytest

from guildward.core.i18n import LANGS, _catalog, missing_translations, t
from guildward.core.models import Confidence, Kind, Level, build_verdict
from guildward.intel import links
from guildward.intel.links import check_url, domain_age_days, extract_urls, registrable, static_signals


def codes(url):
    return {s.code for s in static_signals(url)}


def level(url):
    return build_verdict(Kind.LINK, static_signals(url), base=links.LINK_BASE, confidence=Confidence.LOW).level


@pytest.mark.parametrize("url", [
    "https://discorcl.gift/nitro", "https://steamcommunlty.com/gift", "http://dlscord.com/login",
    "https://discord.xyz", "https://dіscord.com/x", "https://xn--dscord-pvf.com", "https://rnicrosoft.com",
    "https://discord.com.free-nitro.xyz/claim", "https://roblox-free-robux.com", "https://grabify.link/ABC",
    "https://example.com/game-hack.exe", "http://192.168.0.5/login", "https://x.org/qr-login",
])
def test_bad_links_are_red(url):
    assert level(url) is Level.RED, [s.code for s in static_signals(url)]


@pytest.mark.parametrize("url", [
    "https://discord.com/channels/1/2", "https://discord.gg/abc", "https://cdn.discordapp.com/attachments/1/a.png",
    "https://store.steampowered.com/app/10", "https://www.roblox.com/games/1", "youtu.be/abc", "https://example.com/",
    "https://team.com", "https://essex.ac.uk",
])
def test_real_links_are_green(url):
    assert level(url) is Level.GREEN, [s.code for s in static_signals(url)]


def test_real_domain_is_reassuring_and_lookalike_is_severe():
    assert "link.official" in codes("https://discord.com")
    assert next(s for s in static_signals("https://discorcl.gift") if s.code == "link.brand_lookalike").severe


def test_specific_signals():
    assert "link.punycode" in codes("https://xn--dscord-pvf.com")
    assert "link.download" in codes("https://cdn.discordapp.com/attachments/1/free.exe")
    assert "link.archive" in codes("https://example.com/a.zip")
    assert "link.ip_literal" in codes("http://8.8.8.8/x") and "link.ip_literal" in codes("http://3232235777/")
    assert "link.shortener" in codes("https://bit.ly/abc")
    assert "link.qr_login" in codes("https://discord.com/ra/abc")
    assert "link.userinfo" in codes("https://discord.com@evil.xyz/")
    assert "link.adult" in codes("https://pornhub.com") and "link.dating" in codes("https://omegle.com")


def test_registrable_and_extract():
    assert registrable("a.b.example.co.uk") == "example.co.uk" and registrable("x.y.com") == "y.com"
    assert extract_urls("see (https://a.com/x?y=1), and discorcl.gift/free. also bob@mail.com") == [
        "https://a.com/x?y=1", "discorcl.gift/free"]
    assert extract_urls("no links here, e.g. so") == []


def test_rdap_parsing():
    now = datetime(2026, 1, 31, tzinfo=UTC)
    fx = {"events": [{"eventAction": "last changed", "eventDate": "2026-01-30T00:00:00Z"},
                     {"eventAction": "registration", "eventDate": "2026-01-01T00:00:00Z"}]}
    assert domain_age_days(fx, now) == 30
    assert domain_age_days({"events": []}, now) is None and domain_age_days({}, now) is None
    assert domain_age_days({"events": [{"eventAction": "registration", "eventDate": "junk"}]}, now) is None


class _Resp:
    def __init__(self, status, headers=None, body=b"{}"):
        self.status, self.headers, self._body = status, headers or {}, body
        self.content = self

    async def read(self, n=-1):
        return self._body

    async def json(self, **_):
        return {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeSession:
    """Maps url -> response (unknown urls 404) and records every URL actually requested."""

    def __init__(self, routes):
        self.routes, self.seen = routes, []

    def request(self, method, url, **kw):
        self.seen.append(url)
        return self.routes.get(url, _Resp(404))

    def get(self, url, **kw):
        return self.request("GET", url)


def fake_dns(monkeypatch, table):
    async def resolve(host, port):
        return table.get(host, ["93.184.216.34"])
    monkeypatch.setattr(links, "_resolve", resolve)
    links._cache.clear()


@pytest.mark.parametrize("target", [
    "http://127.0.0.1/admin", "http://10.0.0.5/", "http://169.254.169.254/latest/meta-data/", "http://[::1]/",
    "http://localhost/", "ftp://example.com/x", "http://example.com:8080/", "http://3232235777/",
    "http://internal.evil/",
])
def test_redirect_to_internal_target_is_refused(monkeypatch, target):
    fake_dns(monkeypatch, {"localhost": ["127.0.0.1"], "internal.evil": ["10.1.2.3"]})
    s = FakeSession({"https://bit.ly/x": _Resp(302, {"Location": target})})
    res = asyncio.run(check_url("https://bit.ly/x", session=s))
    assert s.seen == ["https://bit.ly/x"]  # the internal hop was never requested
    assert "link.blocked" in {x.code for x in res.verdict.signals}


def test_mixed_dns_answer_is_refused(monkeypatch):
    fake_dns(monkeypatch, {"sneaky.example": ["93.184.216.34", "10.0.0.1"]})
    s = FakeSession({})
    res = asyncio.run(check_url("https://sneaky.example/", session=s))
    assert s.seen == [] and "link.blocked" in {x.code for x in res.verdict.signals}


def test_shortener_expansion_surfaces_the_real_target(monkeypatch):
    fake_dns(monkeypatch, {})
    s = FakeSession({
        "https://bit.ly/x": _Resp(301, {"Location": "https://t.ly/y"}),
        "https://t.ly/y": _Resp(302, {"Location": "https://discorcl.gift/free-nitro"}),
    })
    res = asyncio.run(check_url("https://bit.ly/x", session=s))
    assert res.final_url == "https://discorcl.gift/free-nitro" and res.verdict.level is Level.RED
    assert res.verdict.confidence.name == "MEDIUM"


def test_redirect_loop_stops_at_four_hops(monkeypatch):
    fake_dns(monkeypatch, {})
    s = FakeSession({"https://a.example/": _Resp(302, {"Location": "https://a.example/"})})
    res = asyncio.run(check_url("https://a.example/", session=s))
    assert s.seen.count("https://a.example/") == links.MAX_HOPS + 1
    assert "link.too_many_redirects" in {x.code for x in res.verdict.signals}


def test_new_domain_from_rdap_raises_the_score(monkeypatch):
    fake_dns(monkeypatch, {})
    fresh = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = json.dumps({"events": [{"eventAction": "registration", "eventDate": fresh}]}).encode()
    s = FakeSession({"https://rdap.org/domain/example.com": _Resp(200, body=body)})
    res = asyncio.run(check_url("https://example.com/", session=s))
    assert "link.new_domain_30" in {x.code for x in res.verdict.signals}


def test_network_failure_falls_back_to_static(monkeypatch):
    fake_dns(monkeypatch, {})

    class Boom(FakeSession):
        def request(self, *a, **k):
            raise OSError("down")
    res = asyncio.run(check_url("https://discorcl.gift", session=Boom({})))
    assert res.verdict.level is Level.RED


def test_every_link_string_is_translated_and_formats():
    assert missing_translations() == []
    ok = {"domain", "brand", "ext", "days", "tld"}
    for key, entry in _catalog.items():
        if key.startswith(("link.", "title.link.", "todo.link.")):
            for lang in LANGS:
                assert {f for _, f, _, _ in string.Formatter().parse(entry[lang]) if f} <= ok, key
    for lvl in ("green", "yellow", "red"):
        assert t(f"title.link.{lvl}", "sv") != f"title.link.{lvl}" and t(f"todo.link.{lvl}", "en") != f"todo.link.{lvl}"
    emitted = {s.code for u in ("https://discorcl.gift/free-nitro.exe", "http://8.8.8.8", "https://bit.ly/x",
                                 "https://a.b.c.d.xyz", "https://grabify.link/x", "https://discord.com/ra/x")
               for s in static_signals(u)}
    assert all(c in _catalog for c in emitted)
