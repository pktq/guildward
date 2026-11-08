"""Link checker: is this URL a scam, a look-alike, a token grabber, a download or an adult site?

`static_signals` needs no network. `check_url` adds redirect expansion (SSRF-guarded), domain age (RDAP)
and optional Google Safe Browsing, each failure-tolerant. Nothing here logs URLs (query strings can hold
tokens); at most the bare domain at debug level. `intel/*` never imports discord.
"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import logging
import re
import time
import unicodedata
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath

import aiohttp
from aiohttp.abc import AbstractResolver

from guildward.core.i18n import register
from guildward.core.models import Confidence, Kind, Signal, Verdict, build_verdict

log = logging.getLogger(__name__)

LINK_BASE = 10
MAX_HOPS = 4
CACHE_TTL = 3600.0
USER_AGENT = "Mozilla/5.0 (compatible; GuildwardLinkCheck/1.0)"

# --- data -------------------------------------------------------------------------------------------

# Real domains (exact or any subdomain), by brand.
OFFICIAL: dict[str, tuple[str, ...]] = {
    "Discord": ("discord.com", "discord.gg", "discordapp.com", "discordapp.net", "discord.media", "discord.gift",
                "discord.gifts", "discord.new", "discord.app", "discord.dev", "discord.design", "discord.store",
                "discordstatus.com", "discordmerch.com", "dis.gd"),
    "Steam": ("steampowered.com", "steamcommunity.com", "steamstatic.com", "steamcontent.com", "valvesoftware.com",
              "steam.com"),
    "Roblox": ("roblox.com", "rbxcdn.com", "roblox.link", "robloxlabs.com"),
    "Epic Games": ("epicgames.com", "fortnite.com", "unrealengine.com", "fab.com"),
    "Instagram": ("instagram.com", "cdninstagram.com"),
    "Snapchat": ("snapchat.com", "snap.com", "snapkit.com"),
    "TikTok": ("tiktok.com", "tiktokcdn.com"),
    "YouTube": ("youtube.com", "youtu.be", "ytimg.com"),
    "Twitch": ("twitch.tv", "twitchcdn.net"),
    "Minecraft": ("minecraft.net", "mojang.com"),
    "Google": ("google.com", "google.se", "gstatic.com"),
    "Microsoft": ("microsoft.com", "xbox.com", "live.com"),
    "GitHub": ("github.com", "githubusercontent.com"),
    "Spotify": ("spotify.com", "scdn.co"),
    "Tenor": ("tenor.com", "giphy.com", "imgur.com"),
}
_OFFICIAL_DOMAINS = {d: b for b, ds in OFFICIAL.items() for d in ds}

# Long names: edit distance + containment. Short/common words are matched exactly only (homoglyph or TLD swap),
# or when sitting next to a scam word, otherwise "team.com" would look like Steam.
_FUZZY_BRANDS = ("discord", "discordapp", "roblox", "steamcommunity", "steampowered", "epicgames", "instagram",
                 "snapchat", "fortnite", "minecraft", "tiktok", "youtube", "microsoft")
_EXACT_BRANDS = ("steam", "twitch", "google", "github", "spotify", "xbox", "playstation")
_BRAND_DISPLAY = {"discordapp": "Discord", "steamcommunity": "Steam", "steampowered": "Steam", "epicgames": "Epic Games",
                  "fortnite": "Epic Games"}
_SCAM_WORDS = ("free", "gift", "nitro", "robux", "login", "verify", "claim", "hack", "giveaway")

SUSPICIOUS_TLDS = frozenset(
    "tk ml ga cf gq xyz top click work rest zip mov icu cyou buzz monster sbs cfd gift site online".split()
)
TWO_PART_SUFFIXES = frozenset(
    "co.uk org.uk ac.uk gov.uk com.au net.au org.au com.br com.mx com.tr com.cn com.ar co.jp co.nz co.za co.in "
    "co.kr com.sg com.hk com.ua com.pl".split()
)
# Free hosting: anyone can get a subdomain, so the registrable domain says nothing about the owner.
FREE_HOSTS = frozenset(
    "github.io pages.dev vercel.app netlify.app herokuapp.com workers.dev web.app firebaseapp.com glitch.me repl.co "
    "blogspot.com wixsite.com weebly.com 000webhostapp.com ngrok.io ngrok-free.app trycloudflare.com".split()
)
SHORTENERS = frozenset(
    "bit.ly tinyurl.com t.co goo.gl is.gd v.gd cutt.ly rb.gy shorturl.at ow.ly buff.ly tiny.cc t.ly rebrand.ly bl.ink "
    "s.id lnkd.in soo.gd clck.ru adf.ly bit.do shorte.st qr.ae shorturl.asia".split()
)
IP_LOGGERS = frozenset(
    "grabify.link iplogger.org iplogger.com iplogger.ru 2no.co yip.su ipgrabber.ru ipgraber.ru bmwforum.co "
    "leancoding.co stopify.co freegiftcards.co joinmy.site curiouscat.club catsnthings.fun catsnthings.com "
    "gyazos.com lovebird.guru blasze.tk blasze.com ezstat.ru spottyfly.com ps3cfw.com".split()
)
# Seed only; the rules below catch the long tail.
KNOWN_BAD = frozenset(
    "discordgift.site discord-nitro.xyz discord-give.com discorcl.gift dlscord.gift discordc.gift steamcommunlty.com "
    "steamcomminuty.com robloxx.com.ge".split()
)
HARD_DOWNLOADS = frozenset(
    ".exe .scr .bat .cmd .msi .com .pif .jar .vbs .ps1 .apk .dmg .lnk .hta .js .jse .wsf .reg .appimage".split()
)
ARCHIVES = frozenset(".zip .rar .7z .iso .tar .gz".split())
_ADULT_TOKENS = frozenset("porn porno xxx sex sexy nude nudes nsfw hentai camgirl camgirls escort escorts".split())
_ADULT_NAMES = ("pornhub", "xvideos", "xnxx", "redtube", "xhamster", "youporn", "onlyfans", "chaturbate", "rule34",
                "e621", "fansly", "stripchat", "bongacams")
_DATING_NAMES = ("tinder", "badoo", "omegle", "chatroulette", "ome.tv", "bazoocam", "hookup", "meetme", "lovoo",
                 "dating", "emerald.chat", "chatrandom")
_STRONG_SCAM = ("freenitro", "nitrogift", "nitrofree", "discordnitro", "freerobux", "robuxgenerator", "robuxfree",
                "freevbucks", "vbucks", "freeskins", "freesteam", "steamgift", "giftnitro", "nitrogenerator",
                "freegift", "getrobux")
_WEAK_SCAM = ("nitro", "robux", "claim", "giveaway", "airdrop", "generator", "unban", "cheat", "hack", "login",
              "verify", "signin")
_QR_HINTS = ("qrlogin", "qrcode", "scanqr", "remoteauth", "loginqr")

_URL_RE = re.compile(r"(?i)(?<![@\w.-])(?:https?://|www\.)[^\s<>\"'`|\\^{}]+")
_BARE_RE = re.compile(
    r"(?i)(?<![@\w./-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|net|org|gg|gift|gifts|io|me|tv|co|app|xyz|top|click|site|online|link|ru|tk|ml|ga|cf|gq|ly|to|se|info|"
    r"icu|cyou|buzz|zip|work|rest|live|ws|cc|us|uk|de|fr)(?![a-z0-9-])(?:/[^\s<>\"'`|\\^{}]*)?"
)

# --- URL parsing --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Parts:
    scheme: str
    host: str  # ascii (punycode) lower-case
    uhost: str  # unicode form
    path: str  # path + query, lower-case
    userinfo: bool
    explicit_scheme: bool


def extract_urls(text: str, limit: int = 5) -> list[str]:
    found: list[tuple[int, str]] = []
    for rx in (_URL_RE, _BARE_RE):
        found += [(m.start(), m.group()) for m in rx.finditer(text or "")]
    out: list[str] = []
    for _, raw in sorted(found):
        u = raw.rstrip(".,;:!?)]'\"*_~")
        if u and not any(u in o or o in u for o in out):
            out.append(u)
    return out[:limit]


def _parse(url: str) -> _Parts | None:
    url = url.strip()
    explicit = "://" in url
    try:
        s = urllib.parse.urlsplit(url if explicit else "//" + url, scheme="https")
        host = (s.hostname or "").rstrip(".").lower()
        _ = s.port  # raises on a garbage port
    except ValueError:
        return None
    if not host:
        return None
    try:
        ahost = host if host.isascii() else host.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    try:
        uhost = ahost.encode("ascii").decode("idna") if "xn--" in ahost else ahost
    except UnicodeError:
        uhost = ahost  # malformed punycode is itself suspicious, keep it
    path = (s.path + ("?" + s.query if s.query else "")).lower()
    return _Parts(s.scheme.lower(), ahost, uhost, path, "@" in s.netloc, explicit)


def registrable(host: str) -> str:
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    last2 = ".".join(labels[-2:])
    if last2 in TWO_PART_SUFFIXES or last2 in FREE_HOSTS:
        return ".".join(labels[-3:])
    return last2


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        # http://3232235777 and http://0x7f000001 are legal spellings of an IPv4 address
        return bool(re.fullmatch(r"\d{6,10}|0x[0-9a-f]+", host))


def _official_brand(host: str) -> str | None:
    labels = host.split(".")
    for i in range(len(labels) - 1):
        brand = _OFFICIAL_DOMAINS.get(".".join(labels[i:]))
        if brand:
            return brand
    return None


# --- look-alike matching ------------------------------------------------------------------------------

_CONFUSABLE = str.maketrans({
    "0": "o", "1": "l", "!": "l", "|": "l", "i": "l", "5": "s", "$": "s", "3": "e", "4": "a", "@": "a", "8": "b",
    "9": "g", "ı": "l", "ł": "l",
    # Cyrillic / Greek look-alikes
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "ѕ": "s", "і": "l", "ј": "j", "ԁ": "d",
    "ɡ": "g", "ɑ": "a", "ο": "o", "ν": "v", "ι": "l", "α": "a", "ρ": "p", "τ": "t",
})


def skeleton(label: str) -> str:
    s = unicodedata.normalize("NFKD", label.lower())
    s = "".join(c for c in s if not unicodedata.combining(c)).replace("-", "").replace("_", "")
    return s.translate(_CONFUSABLE).replace("rn", "m").replace("vv", "w").replace("cl", "d")


def _distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _brand_match(uhost: str) -> tuple[str, str] | None:
    """('lookalike'|'name', brand) when this non-official host imitates a brand, else None."""
    sk = skeleton(registrable(uhost).split(".")[0])
    for b in _FUZZY_BRANDS:
        bs = skeleton(b)
        if sk == bs or _distance(sk, bs) <= (2 if len(bs) >= 10 else 1):
            return "lookalike", _BRAND_DISPLAY.get(b, b.capitalize())
    for b in _EXACT_BRANDS:
        if sk == skeleton(b):
            return "lookalike", b.capitalize()
    for b in _FUZZY_BRANDS:
        if skeleton(b) in sk:
            return "name", _BRAND_DISPLAY.get(b, b.capitalize())
    if any(w in sk for w in _SCAM_WORDS):
        for b in _EXACT_BRANDS:
            if b in sk:
                return "name", b.capitalize()
    return None


# --- static signals -----------------------------------------------------------------------------------


def static_signals(url: str) -> list[Signal]:
    p = _parse(url)
    if p is None:
        return [Signal("link.malformed", 30)]
    host, dom = p.host, registrable(p.host)
    ip = _is_ip(host)
    sigs: list[Signal] = []

    def add(code: str, weight: int, severe: bool = False, **params: str | int) -> None:
        sigs.append(Signal(code, weight, params, severe))

    brand = None if ip else _official_brand(host)
    compact = re.sub(r"[^a-z0-9]", "", host.rsplit(".", 1)[0] + p.path)

    if ip:
        add("link.ip_literal", 45, domain=host)
    elif host in KNOWN_BAD or dom in KNOWN_BAD:
        add("link.known_bad", 80, True, domain=dom)
    if dom in IP_LOGGERS or host in IP_LOGGERS:
        add("link.iplogger", 70, True, domain=dom)
    if dom in SHORTENERS:
        add("link.shortener", 20, domain=dom)
    if p.userinfo:
        add("link.userinfo", 45)
    if p.scheme == "http" and p.explicit_scheme:
        add("link.insecure", 10)

    if not ip:
        if "xn--" in host:
            add("link.punycode", 40, domain=p.uhost)
        if not brand:
            m = _brand_match(p.uhost)
            if m and m[0] == "lookalike":
                add("link.brand_lookalike", 70, True, domain=dom, brand=m[1])
            elif m:
                add("link.brand_in_name", 45, domain=dom, brand=m[1])
            else:
                sub = ".".join(host.split(".")[:-len(dom.split("."))])
                hit = next((b for b in _FUZZY_BRANDS if b in skeleton(sub)), None)
                if hit:
                    add("link.brand_subdomain", 60, True, domain=dom, brand=_BRAND_DISPLAY.get(hit, hit.capitalize()))
        tld = host.rsplit(".", 1)[-1]
        if dom in FREE_HOSTS:
            add("link.free_host", 15, domain=dom)
        elif tld in SUSPICIOUS_TLDS and not brand:
            add("link.bad_tld", 20, tld=tld)
        if host.count(".") - dom.count(".") >= 3:
            add("link.many_subdomains", 15)

        if set(re.split(r"[.\-_]", p.uhost)) & _ADULT_TOKENS or any(n in p.uhost.replace("-", "") for n in _ADULT_NAMES):
            add("link.adult", 55, True, domain=dom)
        elif any(n in p.uhost for n in _DATING_NAMES):
            add("link.dating", 40, domain=dom)

    ext = PurePosixPath(p.path.split("?")[0]).suffix
    if ext in HARD_DOWNLOADS:
        add("link.download", 60, ext=ext)
    elif ext in ARCHIVES:
        add("link.archive", 25, ext=ext)

    if (brand == "Discord" and p.path.startswith("/ra/")) or (not brand and any(h in compact for h in _QR_HINTS)):
        add("link.qr_login", 65, True)
    if not brand:
        if any(k in compact for k in _STRONG_SCAM):
            add("link.scam_path", 35)
        elif any(k in compact for k in _WEAK_SCAM):
            add("link.scam_hint", 15)

    if brand and not any(s.weight > 0 for s in sigs):
        add("link.official", -25, brand=brand)
    return sigs


# --- network ------------------------------------------------------------------------------------------

_cache: dict[str, tuple[float, object]] = {}
_MISS = object()


def _cache_get(key: str) -> object:
    hit = _cache.get(key)
    return hit[1] if hit and time.monotonic() - hit[0] < CACHE_TTL else _MISS


def _cache_put(key: str, value: object) -> None:
    if len(_cache) > 2048:
        _cache.clear()
    _cache[key] = (time.monotonic(), value)


async def _resolve(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, port)
    return [i[4][0] for i in infos]


def _all_global(addrs: list[str]) -> bool:
    try:
        return bool(addrs) and all(ipaddress.ip_address(a.split("%")[0]).is_global for a in addrs)
    except ValueError:
        return False


async def _safe_target(url: str) -> bool:
    """SSRF gate, run on every hop: http(s) only, ports 80/443, and every resolved address must be global."""
    try:
        s = urllib.parse.urlsplit(url)
        host, port = s.hostname, s.port
    except ValueError:
        return False
    if s.scheme not in ("http", "https") or not host or port not in (None, 80, 443) or "@" in s.netloc:
        return False
    if _is_ip(host):
        return _all_global([host])  # odd spellings (decimal/hex) fail to parse and are refused
    try:
        return _all_global(await _resolve(host, port or (443 if s.scheme == "https" else 80)))
    except (OSError, UnicodeError):
        return False


class GlobalOnlyResolver(AbstractResolver):
    """For the ClientSession: refuses non-global IPs at connect time, closing the DNS-rebinding gap."""

    def __init__(self) -> None:
        self._inner = aiohttp.DefaultResolver()

    async def resolve(self, host: str, port: int = 0, family: int = 0) -> list:
        hosts = await self._inner.resolve(host, port, family)
        if not _all_global([h["host"] for h in hosts]):
            raise OSError("refused: not a public address")
        return hosts

    async def close(self) -> None:
        await self._inner.close()


def make_session() -> aiohttp.ClientSession:
    """Session for check_url: no cookies, public addresses only (even if DNS changes between check and connect)."""
    return aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(resolver=GlobalOnlyResolver()),
        cookie_jar=aiohttp.DummyCookieJar(),
        headers={"User-Agent": USER_AGENT},
    )


async def _hop(session: aiohttp.ClientSession, url: str, timeout: float) -> str | None:
    """One request, no redirect following, body never read; returns the Location header if redirected."""
    to = aiohttp.ClientTimeout(total=timeout)
    for method in ("HEAD", "GET"):
        async with session.request(method, url, allow_redirects=False, timeout=to) as r:
            if r.status in (301, 302, 303, 307, 308):
                return r.headers.get("Location") or None
            if method == "HEAD" and r.status in (403, 405, 501):
                continue
            return None
    return None


async def expand(url: str, session: aiohttp.ClientSession, timeout: float = 5.0) -> tuple[str, str | None]:
    """Follow redirects by hand. Returns (final_url, problem), problem in {None, 'blocked', 'too_many'}."""
    cur = url if "://" in url else "https://" + url
    for hop in range(MAX_HOPS + 1):
        if not await _safe_target(cur):
            return cur, "blocked"
        try:
            loc = await _hop(session, cur, timeout)
        except (aiohttp.ClientError, TimeoutError, OSError, ValueError):
            return cur, None
        if not loc:
            return cur, None
        if hop == MAX_HOPS:
            return cur, "too_many"
        cur = urllib.parse.urljoin(cur, loc)
    return cur, None


def domain_age_days(rdap: dict, now: datetime | None = None) -> float | None:
    """Days since the RDAP 'registration' event, or None when absent/unparseable."""
    events = rdap.get("events", []) if isinstance(rdap, dict) else []
    for ev in events:
        if isinstance(ev, dict) and ev.get("eventAction") == "registration":
            try:
                d = datetime.fromisoformat(str(ev["eventDate"]).replace("Z", "+00:00"))
            except (KeyError, ValueError):
                return None
            d = d if d.tzinfo else d.replace(tzinfo=UTC)
            return ((now or datetime.now(UTC)) - d).total_seconds() / 86400
    return None


async def _domain_age(session: aiohttp.ClientSession, dom: str, timeout: float) -> float | None:
    cached = _cache_get("age:" + dom)
    if cached is not _MISS:
        return cached  # type: ignore[return-value]
    age = None
    try:
        async with session.get(f"https://rdap.org/domain/{dom}", allow_redirects=True, max_redirects=3,
                               timeout=aiohttp.ClientTimeout(total=timeout),
                               headers={"Accept": "application/rdap+json"}) as r:
            if r.status == 200:
                age = domain_age_days(json.loads(await r.content.read(300_000)))
    except (aiohttp.ClientError, TimeoutError, OSError, ValueError):
        log.debug("rdap failed for %s", dom)
        return None  # failures aren't cached
    _cache_put("age:" + dom, age)
    return age


async def _safe_browsing(session: aiohttp.ClientSession, urls: list[str], key: str, timeout: float) -> bool | None:
    body = {
        "client": {"clientId": "guildward", "clientVersion": "1"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": u} for u in urls],
        },
    }
    ck = "sb:" + hashlib.sha256("\n".join(u.split("?")[0] for u in urls).encode()).hexdigest()
    cached = _cache_get(ck)
    if cached is not _MISS:
        return cached  # type: ignore[return-value]
    try:
        async with session.post("https://safebrowsing.googleapis.com/v4/threatMatches:find", params={"key": key},
                                json=body, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            if r.status != 200:
                return None
            hit = bool((await r.json(content_type=None)).get("matches"))
    except (aiohttp.ClientError, TimeoutError, OSError, ValueError):
        return None  # never log: the exception text can carry the API key
    _cache_put(ck, hit)
    return hit


@dataclass(frozen=True, slots=True)
class LinkResult:
    url: str
    final_url: str
    domain: str
    verdict: Verdict


def _merge(groups: list[list[Signal]]) -> list[Signal]:
    best: dict[str, Signal] = {}
    for s in (s for g in groups for s in g):
        if s.code not in best or abs(s.weight) > abs(best[s.code].weight):
            best[s.code] = s
    return list(best.values())


async def check_url(url: str, *, session: aiohttp.ClientSession, safe_browsing_key: str | None = None,
                    timeout: float = 5.0) -> LinkResult:
    first = static_signals(url)
    p = _parse(url)
    if p is None or any(s.code == "link.official" for s in first):
        dom = registrable(p.host) if p else ""
        return LinkResult(url, url, dom, build_verdict(Kind.LINK, first, base=LINK_BASE, confidence=Confidence.LOW))

    final, problem = await expand(url, session, timeout)
    fp = _parse(final) or p
    dom = registrable(fp.host)
    groups = [first]
    network = fp.host != p.host or problem is not None
    if fp.host != p.host:
        groups.append(static_signals(final))
        if dom != registrable(p.host) and registrable(p.host) not in SHORTENERS:
            groups.append([Signal("link.redirects", 10, {"domain": dom})])
    if problem == "blocked":
        groups.append([Signal("link.blocked", 40)])
    elif problem == "too_many":
        groups.append([Signal("link.too_many_redirects", 20)])

    tasks: dict[str, asyncio.Future] = {}
    if not _is_ip(fp.host) and dom not in FREE_HOSTS and problem != "blocked" and not _official_brand(fp.host):
        tasks["age"] = asyncio.ensure_future(_domain_age(session, dom, timeout))
    if safe_browsing_key and problem != "blocked":
        tasks["sb"] = asyncio.ensure_future(
            _safe_browsing(session, list(dict.fromkeys([url, final])), safe_browsing_key, timeout))
    res = dict(zip(tasks, await asyncio.gather(*tasks.values(), return_exceptions=True), strict=True))
    age, sb = res.get("age"), res.get("sb")
    if isinstance(age, float):
        network = True
        if age < 30:
            groups.append([Signal("link.new_domain_30", 45, {"days": int(age)})])
        elif age < 180:
            groups.append([Signal("link.new_domain_180", 15, {"days": int(age)})])
    if isinstance(sb, bool):
        network = True
        if sb:
            groups.append([Signal("link.safe_browsing", 80, {}, True)])
    conf = Confidence.MEDIUM if network else Confidence.LOW
    return LinkResult(url, final, dom, build_verdict(Kind.LINK, _merge(groups), base=LINK_BASE, confidence=conf))


async def check_links(text: str, *, session: aiohttp.ClientSession,
                      safe_browsing_key: str | None = None) -> list[LinkResult]:
    out = await asyncio.gather(
        *(check_url(u, session=session, safe_browsing_key=safe_browsing_key) for u in extract_urls(text)),
        return_exceptions=True)
    return [r for r in out if isinstance(r, LinkResult)]


# --- strings ------------------------------------------------------------------------------------------

register({
    "link.official": {
        "en": "This is a real {brand} address.",
        "sv": "Det här är en riktig {brand}-adress.",
    },
    "link.known_bad": {
        "en": "{domain} is a known scam website.",
        "sv": "{domain} är en känd bedrägerisida.",
    },
    "link.brand_lookalike": {
        "en": "{domain} is made to look like {brand} but it is NOT {brand}. Scammers copy names with small spelling tricks.",
        "sv": "{domain} är gjord för att se ut som {brand} men är INTE {brand}. Bedragare kopierar namn med små stavningstrick.",
    },
    "link.brand_in_name": {
        "en": "{domain} has {brand} in its name but is not run by {brand}.",
        "sv": "{domain} har {brand} i namnet men drivs inte av {brand}.",
    },
    "link.brand_subdomain": {
        "en": "The {brand} part is just decoration at the front. The page really belongs to {domain}.",
        "sv": "{brand}-delen är bara utsmyckning längst fram. Sidan tillhör egentligen {domain}.",
    },
    "link.punycode": {
        "en": "The address uses special look-alike letters ({domain}). Scammers use them to fake real names.",
        "sv": "Adressen använder speciella lika-tecken ({domain}). Bedragare använder dem för att fejka riktiga namn.",
    },
    "link.ip_literal": {
        "en": "The link is just numbers ({domain}) instead of a name. Real sites almost never do that.",
        "sv": "Länken är bara siffror ({domain}) i stället för ett namn. Riktiga sidor gör nästan aldrig så.",
    },
    "link.bad_tld": {
        "en": "The ending .{tld} is cheap and often used by scam sites.",
        "sv": "Ändelsen .{tld} är billig och används ofta av bedrägerisidor.",
    },
    "link.many_subdomains": {
        "en": "The address has lots of parts chained together, a trick to hide where it really goes.",
        "sv": "Adressen har många delar efter varandra, ett trick för att dölja vart den egentligen går.",
    },
    "link.scam_path": {
        "en": "It talks about free Nitro, Robux, skins or gifts. Free stuff like that is almost always a scam.",
        "sv": "Den handlar om gratis Nitro, Robux, skins eller presenter. Sånt gratis är nästan alltid bedrägeri.",
    },
    "link.scam_hint": {
        "en": "Words in the address like login, claim or giveaway are often used to trick people.",
        "sv": "Ord i adressen som login, claim eller giveaway används ofta för att lura folk.",
    },
    "link.download": {
        "en": "It downloads a program file ({ext}). These can contain viruses or steal your account.",
        "sv": "Den laddar ner en programfil ({ext}). Såna kan innehålla virus eller stjäla ditt konto.",
    },
    "link.archive": {
        "en": "It downloads a packed file ({ext}). \"Game hacks\" and \"cracks\" in these are often viruses.",
        "sv": "Den laddar ner en packad fil ({ext}). \"Spelhack\" och \"cracks\" i såna är ofta virus.",
    },
    "link.iplogger": {
        "en": "This is a tracking link that records your IP address (a clue to where you are) when you open it.",
        "sv": "Det här är en spårlänk som sparar din IP-adress (en ledtråd om var du är) när du öppnar den.",
    },
    "link.shortener": {
        "en": "A shortened link hides where it really goes.",
        "sv": "En förkortad länk döljer vart den egentligen går.",
    },
    "link.adult": {
        "en": "This looks like an adult (18+) website.",
        "sv": "Det här ser ut som en vuxensida (18+).",
    },
    "link.dating": {
        "en": "This is a dating or random-stranger chat site. Not for kids.",
        "sv": "Det här är en dejtingsida eller slumpchatt med främlingar. Inte för barn.",
    },
    "link.qr_login": {
        "en": "This is a QR / remote login link. If you scan or open it, someone can take over your account.",
        "sv": "Det här är en QR- eller fjärrinloggningslänk. Om du skannar eller öppnar den kan någon ta över ditt konto.",
    },
    "link.userinfo": {
        "en": "The address hides its real destination behind an @ sign.",
        "sv": "Adressen döljer sitt riktiga mål bakom ett @-tecken.",
    },
    "link.insecure": {
        "en": "The page is not encrypted (http).",
        "sv": "Sidan är inte krypterad (http).",
    },
    "link.free_host": {
        "en": "It is on a free website host ({domain}) where anyone can put up a page.",
        "sv": "Den ligger på en gratis webbhotell-tjänst ({domain}) där vem som helst kan lägga upp en sida.",
    },
    "link.malformed": {
        "en": "This doesn't look like a normal web address.",
        "sv": "Det här ser inte ut som en vanlig webbadress.",
    },
    "link.redirects": {
        "en": "It sends you on to a different site ({domain}).",
        "sv": "Den skickar dig vidare till en annan sida ({domain}).",
    },
    "link.blocked": {
        "en": "It points somewhere we won't look, like a computer inside a private network. Suspicious.",
        "sv": "Den pekar någonstans vi inte tittar, som en dator i ett privat nätverk. Misstänkt.",
    },
    "link.too_many_redirects": {
        "en": "It bounces you around many times before landing somewhere.",
        "sv": "Den skickar runt dig många gånger innan du hamnar någonstans.",
    },
    "link.new_domain_30": {
        "en": "The website was created only {days} days ago. Scam sites are usually brand new.",
        "sv": "Webbplatsen skapades för bara {days} dagar sedan. Bedrägerisidor är oftast helt nya.",
    },
    "link.new_domain_180": {
        "en": "The website is fairly new ({days} days old).",
        "sv": "Webbplatsen är ganska ny ({days} dagar gammal).",
    },
    "link.safe_browsing": {
        "en": "Google's safety list flags this page as dangerous.",
        "sv": "Googles säkerhetslista markerar sidan som farlig.",
    },
    "title.link.green": {"en": "This link looks okay", "sv": "Den här länken ser okej ut"},
    "title.link.yellow": {"en": "Careful with this link", "sv": "Var försiktig med den här länken"},
    "title.link.red": {"en": "Don't click this link", "sv": "Klicka inte på den här länken"},
    "todo.link.green": {
        "en": "Nothing bad found. Still, never type your password on a page you got to from a link.",
        "sv": "Inget farligt hittades. Skriv ändå aldrig ditt lösenord på en sida du kommit till via en länk.",
    },
    "todo.link.yellow": {
        "en": "Don't log in or download anything from it. If you're unsure, ask a grown-up first.",
        "sv": "Logga inte in och ladda inte ner något därifrån. Är du osäker, fråga en vuxen först.",
    },
    "todo.link.red": {
        "en": "Don't open it and don't log in through it. Open Discord (or the app) yourself instead. "
        "Tell a grown-up and block whoever sent it.",
        "sv": "Öppna den inte och logga inte in via den. Öppna Discord (eller appen) själv i stället. "
        "Berätta för en vuxen och blockera den som skickade den.",
    },
})
