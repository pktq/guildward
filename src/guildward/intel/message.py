"""Is this sketchy?: public entry point for the message check.

The detection rules themselves are loaded at runtime (see intel/rules): the private `guildward_private.rules`
package in production, the small public example set otherwise. The user-facing strings for every
`msg.*` code live here, because what a kid is told is not secret; how we detect it is.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable

from guildward.core.i18n import register
from guildward.core.models import Signal
from guildward.intel.behavior import STAGE_OF
from guildward.intel.rules import rules

MESSAGE_BASE = 10
MULTI_STAGE = 20
SOFT_HINT = 20  # weights below this are hints: they feed memory, not the multi-stage bonus


def analyze_message(text: str, model: Iterable[Signal] = ()) -> tuple[Signal, ...]:
    """Risk signals for one message. Empty tuple = nothing found.

    `model` = what the local message model (intel/semantic.py) found in the same text, if it ran.
    """
    if not text or not text.strip():
        return ()
    found = tuple(rules().analyze_message(text))
    model = tuple(model)
    return fuse(found, model) if model else found


def fuse(found: Iterable[Signal], model: Iterable[Signal]) -> tuple[Signal, ...]:
    """Rules ∪ model, strongest weight per category. A rule's params and severity always survive."""
    best: dict[str, Signal] = {}
    for s in found:
        if s.code not in best or s.weight > best[s.code].weight:
            best[s.code] = s
    rule_codes = set(best)
    for s in model:
        cur = best.get(s.code)
        if cur is None:
            best[s.code] = s
        elif s.weight > cur.weight:
            best[s.code] = dataclasses.replace(cur, weight=s.weight)
    if "msg.multi_stage" not in rule_codes:
        stages = {STAGE_OF[s.code] for s in best.values() if s.code in STAGE_OF and s.weight >= SOFT_HINT}
        if len(stages) >= 2:
            best["msg.multi_stage"] = Signal("msg.multi_stage", MULTI_STAGE)
    return tuple(sorted(best.values(), key=lambda s: (not s.severe, -s.weight)))


register({
    "msg.age_probe": {
        "en": "Asks how old you are. Strangers who ask this early are a warning sign.",
        "sv": "Frågar hur gammal du är. Främlingar som frågar det tidigt är ett varningstecken.",
    },
    "msg.age_gap": {
        "en": "An adult talking about your age next to theirs. Adults shouldn't be chatting up kids online.",
        "sv": "En vuxen som jämför sin ålder med din. Vuxna ska inte försöka bli kompis med barn på nätet.",
    },
    "msg.isolation": {
        "en": "Wants you to move to {app}. People who pull you off Discord may want a place where no one is watching.",
        "sv": "Vill att ni flyttar till {app}. Den som drar bort dig från Discord kan vilja vara där ingen ser.",
    },
    "msg.isolation_private": {
        "en": "Wants a private call or chat with just you. That can be a way to get you alone.",
        "sv": "Vill ha ett privat samtal eller en chatt med bara dig. Det kan vara ett sätt att få dig ensam.",
    },
    "msg.secrecy": {
        "en": "Asks you to keep secrets or hide things from your parents. Safe people don't ask you to hide things.",
        "sv": "Ber dig hålla hemligheter eller dölja saker för dina föräldrar. Schyssta personer ber dig inte "
        "göra det.",
    },
    "msg.photo_request": {
        "en": "Asks for photos or video of you. Never send pictures of yourself to people you only know online.",
        "sv": "Ber om bilder eller video på dig. Skicka aldrig bilder på dig själv till någon du bara känner på nätet.",
    },
    "msg.sexual": {
        "en": "Talks about sexual stuff. That is never okay from someone online.",
        "sv": "Pratar om sexuella saker. Det är aldrig okej från någon på nätet.",
    },
    "msg.gifts": {
        "en": "Offers free stuff like Robux, Nitro or money. Gifts from strangers usually come with a catch.",
        "sv": "Erbjuder gratisgrejer som Robux, Nitro eller pengar. Presenter från främlingar har oftast en baksida.",
    },
    "msg.meeting": {
        "en": "Wants to meet you in real life. Never meet someone from online unless a parent knows and comes along.",
        "sv": "Vill träffa dig på riktigt. Träffa aldrig någon från nätet om inte en förälder vet om det och "
        "följer med.",
    },
    "msg.personal_info": {
        "en": "Asks where you live, your school, your number or if you're alone. Keep that private.",
        "sv": "Frågar var du bor, vilken skola du går på, ditt nummer eller om du är ensam. Håll det för dig själv.",
    },
    "msg.flattery": {
        "en": "Lays on the compliments, like saying you're mature or that only they get you. Tricksters often start "
        "this way.",
        "sv": "Smickrar dig mycket, typ att du är mogen eller att bara de förstår dig. Så börjar ofta de som vill "
        "lura barn.",
    },
    "msg.scam_link": {
        "en": "Looks like a scam. Fake free Nitro, prizes and 'verify your account' tricks steal accounts. "
        "Don't click, log in or scan anything.",
        "sv": "Ser ut som en bluff. Falsk gratis-Nitro, vinster och ”verifiera ditt konto” används för att stjäla "
        "konton. Klicka inte, logga inte in och skanna ingenting.",
    },
    "msg.pressure": {
        "en": "Pressures or threatens you. If someone threatens to share pictures: don't send more or pay, and "
        "tell an adult you trust.",
        "sv": "Pressar eller hotar dig. Om någon hotar att sprida bilder: skicka inget mer, betala inte och "
        "berätta för en vuxen du litar på.",
    },
    "msg.multi_stage": {
        "en": "Several warning signs in one message. That mix is typical of people trying to trick kids.",
        "sv": "Flera varningstecken i samma meddelande. Just den blandningen är typisk för folk som försöker "
        "lura barn.",
    },
})
