"""Same-person links: marks that tie accounts run by one person (or one gang) together.

Writing-style fingerprinting is unreliable on short chat messages and would link kids who share slang,
so this uses the strong links instead: off-platform handles and payment tags a sender pushes, copy-pasted
opener scripts, and re-uploaded avatars / near-identical names. Marks are hashed with `mark_key` before
storage, so third parties' raw handles are never kept.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass

from guildward.core.text import _fold, normalize

# Script marks: MinHash over word 3-shingles, banded for LSH. Plain 64-bit simhash measured 9-17 bits apart
# for one-word edits of a 30-word script (unrelated messages: 26-36), too close to band reliably.
SCRIPT_BANDS = 16
SCRIPT_ROWS = 2  # min-hashes per band: P(band equal) = Jaccard^2
SCRIPT_MATCH_BANDS = 5  # equal bands (from one message pair) that mean "same script"
SCRIPT_MIN_WORDS = 6
_SHINGLE = 3
_P = (1 << 61) - 1
_PERM = [
    (int.from_bytes(hashlib.blake2b(b"a%d" % i, digest_size=8).digest(), "big") % (_P - 1) + 1,
     int.from_bytes(hashlib.blake2b(b"b%d" % i, digest_size=8).digest(), "big") % _P)
    for i in range(SCRIPT_BANDS * SCRIPT_ROWS)
]


@dataclass(frozen=True, slots=True)
class Mark:
    kind: str  # handle|payment|script|avatar|name
    value: str  # normalised plaintext; only ever stored as mark_key()


def mark_key(secret: bytes, m: Mark) -> str:
    return hmac.new(secret, f"{m.kind}:{m.value}".encode(), hashlib.sha256).hexdigest()[:32]


# --- off-platform handles and payment tags ---------------------------------------------------------------

_PLATFORMS = {
    "snapchat": "snap", "snap": "snap", "snapa": "snap", "snappa": "snap", "sc": "snap",
    "instagram": "insta", "insta": "insta", "ig": "insta",
    "tiktok": "tiktok", "tik tok": "tiktok",
    "telegram": "telegram", "tele": "telegram", "tg": "telegram",
    "whatsapp": "whatsapp", "whats app": "whatsapp",
    "kik": "kik", "signal": "signal", "wickr": "wickr",  # Session handles are IDs: see _SESSION_ID
    "discord": "discord", "dc": "discord",
    "cashapp": "cashapp", "cash app": "cashapp", "venmo": "venmo", "paypal": "paypal",
}
_PAYMENT = {"cashapp", "venmo", "paypal"}
_PLATFORM_RE = "|".join(sorted((re.escape(k) for k in _PLATFORMS), key=len, reverse=True))
_HANDLE = r"[a-z0-9][a-z0-9._-]{1,31}"
_CUE_WORD = r"(?:me|mig|user ?name|name|namn|användarnamn|id|handle|tag|it'?s|is|är|e|at)"
_HANDLE_AFTER = re.compile(
    rf"\b(?P<p>{_PLATFORM_RE})\b(?P<cue>[\s,:=>-]*(?:{_CUE_WORD}\b[\s,:=>-]*){{0,3}})(?P<at>@?)(?P<h>{_HANDLE})"
)
_HANDLE_BEFORE = re.compile(rf"@(?P<h>{_HANDLE})\s+(?:on|på)\s+(?P<p>{_PLATFORM_RE})\b")
# "add me jake_09" with no platform named means Discord; only handle-shaped tokens ("add me in game" is not).
_ADD_ME = re.compile(rf"\b(?:add|adda|lägg till)\s+(?:me|mig)\s*[:-]?\s*@?(?P<h>{_HANDLE})")
# Possessive / request words before the platform make a plain-word handle believable ("my snap is jakesmith").
_INTRO = re.compile(r"\b(?:my|mitt|min|add|adda|lägg till|hmu|hit me up|follow|följ|text me|skriv|dm me)\b")
# "is"/"its" alone are not enough ("ig its fine", "insta is better"); they need an _INTRO word before.
_EXPLICIT_CUE = re.compile(r"[:=-]")
_URLS = [
    (re.compile(r"(?:t|telegram)\.me/(?P<h>[a-z0-9_]{4,32})"), "handle", "telegram"),
    (re.compile(r"instagram\.com/(?P<h>[a-z0-9._]{2,30})"), "handle", "insta"),
    (re.compile(r"tiktok\.com/@(?P<h>[a-z0-9._]{2,24})"), "handle", "tiktok"),
    (re.compile(r"snapchat\.com/add/(?P<h>[a-z0-9._-]{2,15})"), "handle", "snap"),
    (re.compile(r"kik\.me/(?P<h>[a-z0-9._]{2,20})"), "handle", "kik"),
    (re.compile(r"cash\.app/\$(?P<h>[a-z][a-z0-9_]{1,19})"), "payment", "cashapp"),
    (re.compile(r"paypal\.me/(?P<h>[a-z0-9._-]{2,30})"), "payment", "paypal"),
    (re.compile(r"venmo\.com/(?:u/)?(?P<h>[a-z0-9_-]{2,30})"), "payment", "venmo"),
]
_WA_ME = re.compile(r"wa\.me/\+?(?P<n>\d{8,15})")
_EMAIL = re.compile(r"(?<![\w.+-])[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}")
_SESSION_ID = re.compile(r"\b05[0-9a-f]{64}\b")
_PHONE = re.compile(r"(?<![\w+])(\+?\d[\d \-().]{6,18}\d)(?!\w)")
_DATE = re.compile(r"\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}")
_PHONE_CUE = re.compile(
    r"\b(?:whats ?app|wa|signal|telegram|number|nummer|numret|nr|phone|tel|telefon|mobil|call|ring|text|sms"
    r"|swish|swisha)\b"
)
_CASHTAG = re.compile(r"(?<![\w$])\$(?P<h>[a-z][a-z0-9_]{2,19})\b")
_PAY_CUE = re.compile(r"\b(?:cash ?app|cash|send|pay|paid|skicka|betala|money|pengar|venmo|paypal|tip|donate)\b")

_STOP_WORDS = """
me my mig min mitt mina is are am be the a an and or if on in at to too so pls plz please now rn back here there
then than also again instead it its it's that this what who why how when where you your yours u ur i im i'm we us
they them he she him her his hers ill later tomorrow today tonight sometime soon lol lmao haha hahaha xd ok okay
yes no nope yeah yea yep sure bro bruh dude man girl guys och eller på är att det den du jag dig så nu här där inte
har ha kan vill ska med för till om men då va vad ja nej jo sen imorgon ikväll idag också igen account acc name
username profile story stories streak streaks down broken boring dead private public same gone new old banned hacked
deleted blocked sucks cool fun better best good bad works working not dont don't cant can't wont won't do does did
have has got get add adda follow send chat call video pic pics photo photos message msg dm dms text game games ingame
server link it's mine just only first real fake main alt more much very really hmm idk fine great trash lame
worse dumb stupid weird annoying free safe lit literally actually always never still kinda basically honestly
probably currently finally lowkey highkey totally super pretty gonna wanna gotta full empty open closed off
"""
_STOP = frozenset(_STOP_WORDS.split()) | {p for k in _PLATFORMS for p in k.split()}


def _clean(h: str) -> str:
    return h.strip("._-'")


def _handle_ok(h: str, *, at: bool, explicit: bool) -> bool:
    if len(h) < 3 or h in _STOP or not re.search(r"[a-z]", h):  # "dc at 9.30" is a time, not a handle
        return False
    if at or re.search(r"[\d._]", h):
        return True
    return explicit and len(h) >= 4


def _phone_marks(s: str) -> list[Mark]:
    out = [Mark("handle", f"phone:{m['n'][-9:]}") for m in _WA_ME.finditer(s)]
    cue = bool(_PHONE_CUE.search(s))
    for m in _PHONE.finditer(s):
        raw = m.group(1)
        digits = re.sub(r"\D", "", raw)
        if not 8 <= len(digits) <= 15 or _DATE.fullmatch(raw.strip()):
            continue
        if cue or raw.startswith(("+", "00")):
            out.append(Mark("handle", f"phone:{digits[-9:]}"))  # last 9 digits: same number with or without +46/0
    return out


def handle_marks(text: str) -> list[Mark]:
    """Off-platform handles (kind handle) and payment tags (kind payment) pushed in a message."""
    s = _fold(text).replace("’", "'")
    out: list[Mark] = []

    def add(platform: str, h: str) -> None:
        out.append(Mark("payment" if platform in _PAYMENT else "handle", f"{platform}:{h}"))

    for m in _EMAIL.finditer(s):
        out.append(Mark("handle", f"email:{m.group()}"))
    no_email = _EMAIL.sub(" ", s)
    for rx, kind, platform in _URLS:
        out += [Mark(kind, f"{platform}:{_clean(m['h'])}") for m in rx.finditer(no_email)]
    out += [Mark("handle", f"session:{m.group()}") for m in _SESSION_ID.finditer(no_email)]
    for m in _HANDLE_AFTER.finditer(no_email):
        h = _clean(m["h"])
        explicit = bool(_EXPLICIT_CUE.search(m["cue"]) or _INTRO.search(no_email[max(0, m.start() - 30):m.start()]))
        if _handle_ok(h, at=bool(m["at"]), explicit=explicit):
            add(_PLATFORMS[m["p"]], h)
    for m in _HANDLE_BEFORE.finditer(no_email):
        if _handle_ok(h := _clean(m["h"]), at=True, explicit=True):
            add(_PLATFORMS[m["p"]], h)
    for m in _ADD_ME.finditer(no_email):
        if _handle_ok(h := _clean(m["h"]), at=False, explicit=False):  # needs a digit, dot or underscore
            add("discord", h)
    pay_cue = bool(_PAY_CUE.search(no_email))
    for m in _CASHTAG.finditer(no_email):
        h = m["h"]
        # "$nap" / "$ex" are leetspeak for snap / sex, not a Cash App tag.
        if f"s{h}" in _STOP or f"s{h}" in {"sex", "shit", "sexy", "send"}:
            continue
        if pay_cue or re.search(r"[\d_]", h):
            add("cashapp", h)
    out += _phone_marks(no_email)
    return out


# --- script reuse ------------------------------------------------------------------------------------------


def _h64(s: str) -> int:
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "big")


def script_marks(text: str) -> list[Mark]:
    """LSH band marks of a message's word 3-shingles; a copy-pasted script shares most bands across accounts."""
    words = normalize(text).split()
    if len(words) < SCRIPT_MIN_WORDS:
        return []
    shingles = {_h64(" ".join(words[i:i + _SHINGLE])) for i in range(len(words) - _SHINGLE + 1)}
    mins = [min((a * x + b) % _P for x in shingles) for a, b in _PERM]
    marks = []
    for i in range(SCRIPT_BANDS):
        band = mins[i * SCRIPT_ROWS:(i + 1) * SCRIPT_ROWS]
        digest = hashlib.blake2b(b"".join(v.to_bytes(8, "big") for v in band), digest_size=6).hexdigest()
        marks.append(Mark("script", f"b{i}:{digest}"))
    return marks


def extract_marks(text: str) -> list[Mark]:
    """Every mark in one message: handles, payment tags, script bands. Deduplicated, order kept."""
    if not text or not text.strip():
        return []
    return list(dict.fromkeys(handle_marks(text) + script_marks(text)))


# --- profile -----------------------------------------------------------------------------------------------

_GENERIC_NAME_WORDS = """
gamer gaming games game player plays playz user official real the its im not xx xo ttv yt tv live gg pro noob
king queen lord master dark shadow ghost ninja dragon wolf cat dog cool epic super mega ultra girl boy kid baby bby
babe cute love lover fan roblox minecraft fortnite valorant discord bot music art anime edits editz alt main account
acc daddy mommy sweet princess angel devil demon killer sniper legend beast boss chill vibes sad lol xd tiktok insta
snap hello hey just only
"""
_GENERIC_NAME_PARTS = sorted(_GENERIC_NAME_WORDS.split(), key=len, reverse=True)


def name_skeleton(name: str) -> str:
    s = re.sub(r"[\W\d_]+", "", normalize(name, leet=False))
    return re.sub(r"(.)\1+", r"\1", s)


def _distinctive(skel: str) -> bool:
    if len(skel) < 6:
        return False
    rest = skel
    for part in _GENERIC_NAME_PARTS:
        rest = rest.replace(part, "")
    return len(rest) >= 4


def profile_marks(username: str, global_name: str | None, avatar: str | None) -> list[Mark]:
    marks = [Mark("avatar", avatar)] if avatar else []
    for name in (username, global_name):
        if name and _distinctive(skel := name_skeleton(name)):
            marks.append(Mark("name", skel))
    return list(dict.fromkeys(marks))
