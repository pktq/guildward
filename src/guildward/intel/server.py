"""Server Intel, layer 0: the outside view any invite gives us without joining.

Input is plain data (InviteFacts) so scoring is testable without Discord; bot/adapters.py fills it.
Later layers (crowd reports, admin audits) add signals and raise confidence; they plug in here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from guildward.core.i18n import register
from guildward.core.models import Confidence, Kind, Signal, Verdict, build_verdict
from guildward.core.snowflake import age_days
from guildward.intel.patterns import NameFlag, flags_in

SERVER_BASE = 20  # an unknown server starts slightly cautious, not neutral

# Discord guild feature flags that mean Discord itself vetted or constrained the server.
_FEATURE_WEIGHTS: dict[str, tuple[str, int]] = {
    "VERIFIED": ("server.verified", -30),
    "PARTNERED": ("server.partnered", -22),
    "DISCOVERABLE": ("server.discoverable", -8),
    "MEMBER_VERIFICATION_GATE_ENABLED": ("server.rules_gate", -4),
    "AUTO_MODERATION": ("server.automod", -5),
}

# discord NSFWLevel: 0 default, 1 explicit, 2 safe, 3 age_restricted
_NSFW_EXPLICIT = 1
_NSFW_AGE_RESTRICTED = 3
# discord VerificationLevel: 0 none, 1 low (verified email), 2 medium, 3 high, 4 highest (phone)
_VERIFY_NONE, _VERIFY_LOW, _VERIFY_HIGH = 0, 1, 3


@dataclass(frozen=True, slots=True)
class InviteFacts:
    code: str
    guild_id: int | None  # None for group-DM / friend invites
    name: str | None = None
    description: str | None = None
    channel_name: str | None = None
    verification_level: int | None = None
    nsfw_level: int | None = None
    features: frozenset[str] = field(default_factory=frozenset)
    member_count: int | None = None
    presence_count: int | None = None
    inviter_id: int | None = None
    is_group_dm: bool = False
    is_friend_invite: bool = False


def _age_signal(prefix: str, snowflake: int, now: datetime | None) -> Signal | None:
    days = age_days(snowflake, now)
    d = int(days)
    if days < 7:
        return Signal(f"{prefix}.age_days", 30 if prefix == "server" else 18, {"days": d})
    if days < 30:
        return Signal(f"{prefix}.age_weeks", 18 if prefix == "server" else 10, {"days": d})
    if days < 90:
        return Signal(f"{prefix}.age_months", 8 if prefix == "server" else 4, {"days": d})
    if days > 730:
        return Signal(f"{prefix}.age_old", -8 if prefix == "server" else -4, {"years": int(days // 365)})
    return None


def _name_signals(facts: InviteFacts) -> list[Signal]:
    flags = flags_in(facts.name, facts.description, facts.channel_name)
    sigs: list[Signal] = []
    sexual = flags & {NameFlag.ADULT, NameFlag.DATING}
    if NameFlag.MINOR_BAIT in flags or (sexual and NameFlag.TEEN in flags):
        sigs.append(Signal("server.name_minor_sexual", 60, severe=True))
    if NameFlag.ADULT in flags:
        sigs.append(Signal("server.name_adult", 45, severe=True))
    if NameFlag.DATING in flags:
        sigs.append(Signal("server.name_dating", 40))
    if NameFlag.DM_BAIT in flags:
        sigs.append(Signal("server.name_dm_bait", 20))
    if NameFlag.IMPERSONATION in flags:
        sigs.append(Signal("server.name_scam", 20))
    return sigs


def score_invite(facts: InviteFacts, *, now: datetime | None = None) -> Verdict:
    sigs: list[Signal] = []

    if facts.is_friend_invite:
        sigs.append(Signal("server.friend_invite", 10))
    elif facts.is_group_dm:
        sigs.append(Signal("server.group_dm", 15))

    if facts.guild_id is not None:
        if s := _age_signal("server", facts.guild_id, now):
            sigs.append(s)

        if facts.nsfw_level == _NSFW_AGE_RESTRICTED:
            sigs.append(Signal("server.nsfw_age_restricted", 60, severe=True))
        elif facts.nsfw_level == _NSFW_EXPLICIT:
            sigs.append(Signal("server.nsfw_explicit", 50, severe=True))

        if facts.verification_level == _VERIFY_NONE:
            sigs.append(Signal("server.verify_none", 10))
        elif facts.verification_level == _VERIFY_LOW:
            sigs.append(Signal("server.verify_low", 4))
        elif (facts.verification_level or 0) >= _VERIFY_HIGH:
            sigs.append(Signal("server.verify_high", -5))

        for feature, (code, weight) in _FEATURE_WEIGHTS.items():
            if feature in facts.features:
                sigs.append(Signal(code, weight))

        if facts.member_count is not None and facts.member_count < 15:
            sigs.append(Signal("server.tiny", 6, {"members": facts.member_count}))

    if facts.inviter_id is not None:
        days = age_days(facts.inviter_id, now)
        if days < 7:
            sigs.append(Signal("server.inviter_new", 15, {"days": int(days)}))
        elif days < 30:
            sigs.append(Signal("server.inviter_young", 8, {"days": int(days)}))

    sigs.extend(_name_signals(facts))
    return build_verdict(Kind.SERVER, sigs, base=SERVER_BASE, confidence=Confidence.LOW)


register({
    "server.age_days": {
        "en": "The server is brand new ({days} days old). Bad servers are often new and short-lived.",
        "sv": "Servern är helt ny ({days} dagar gammal). Dåliga servrar är ofta nya och kortlivade.",
    },
    "server.age_weeks": {
        "en": "The server is only {days} days old.",
        "sv": "Servern är bara {days} dagar gammal.",
    },
    "server.age_months": {
        "en": "The server is fairly new ({days} days old).",
        "sv": "Servern är ganska ny ({days} dagar gammal).",
    },
    "server.age_old": {
        "en": "The server has existed for {years}+ years.",
        "sv": "Servern har funnits i {years}+ år.",
    },
    "server.friend_invite": {
        "en": "This is a friend invite from one person, not a server.",
        "sv": "Det här är en vänlänk från en person, inte en server.",
    },
    "server.group_dm": {
        "en": "This is an invite to a private group chat, where no moderators are watching.",
        "sv": "Det här är en inbjudan till en privat gruppchatt, där inga moderatorer finns.",
    },
    "server.nsfw_age_restricted": {
        "en": "Discord has marked this server as 18+ only.",
        "sv": "Discord har märkt servern som endast för 18+.",
    },
    "server.nsfw_explicit": {
        "en": "Discord has marked this server as having explicit content.",
        "sv": "Discord har märkt servern som en server med explicit innehåll.",
    },
    "server.verify_none": {
        "en": "Anyone can post right away, even accounts made a minute ago.",
        "sv": "Vem som helst kan skriva direkt, även konton som skapades för en minut sedan.",
    },
    "server.verify_low": {
        "en": "Only a verified email is needed to post.",
        "sv": "Det räcker med en verifierad e-post för att skriva.",
    },
    "server.verify_high": {
        "en": "New accounts must wait or verify a phone before posting.",
        "sv": "Nya konton måste vänta eller verifiera telefon innan de kan skriva.",
    },
    "server.verified": {
        "en": "Officially verified by Discord.",
        "sv": "Officiellt verifierad av Discord.",
    },
    "server.partnered": {
        "en": "A Discord Partner server.",
        "sv": "En Discord Partner-server.",
    },
    "server.discoverable": {
        "en": "Listed in Server Discovery, which has safety requirements.",
        "sv": "Finns i Server Discovery, som har säkerhetskrav.",
    },
    "server.rules_gate": {
        "en": "New members must accept the rules first.",
        "sv": "Nya medlemmar måste godkänna reglerna först.",
    },
    "server.automod": {
        "en": "Uses Discord's AutoMod to filter messages.",
        "sv": "Använder Discords AutoMod för att filtrera meddelanden.",
    },
    "server.tiny": {
        "en": "Very small server ({members} members): few people would notice if someone behaves badly.",
        "sv": "Mycket liten server ({members} medlemmar): få skulle märka om någon beter sig illa.",
    },
    "server.inviter_new": {
        "en": "The person who made this invite has an account only {days} days old.",
        "sv": "Personen som skapade inbjudan har ett konto som bara är {days} dagar gammalt.",
    },
    "server.inviter_young": {
        "en": "The person who made this invite has a fairly new account ({days} days).",
        "sv": "Personen som skapade inbjudan har ett ganska nytt konto ({days} dagar).",
    },
    "server.name_minor_sexual": {
        "en": "The server's name or channels mix young ages with adult or dating themes.",
        "sv": "Serverns namn eller kanaler blandar unga åldrar med vuxen- eller dejtingteman.",
    },
    "server.name_adult": {
        "en": "The server's name or channels mention adult/sexual content.",
        "sv": "Serverns namn eller kanaler nämner vuxet/sexuellt innehåll.",
    },
    "server.name_dating": {
        "en": "The server looks like an online dating server.",
        "sv": "Servern ser ut som en nätdejtingserver.",
    },
    "server.name_dm_bait": {
        "en": "The server pushes people to DM each other.",
        "sv": "Servern uppmanar folk att skicka DM till varandra.",
    },
    "server.name_scam": {
        "en": "The server name looks like a giveaway or fake-staff scam.",
        "sv": "Servernamnet ser ut som en bluff: falsk utlottning eller falsk personal.",
    },
})
