"""Person Intel, layer 0: what a public Discord profile says about an account.

Account age is the strongest free signal: groomers and scammers burn through fresh accounts.
Later layers (audited-server behaviour, Safety Network flags) add signals here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from guildward.core.i18n import register
from guildward.core.models import Confidence, Kind, Signal, Verdict, build_verdict
from guildward.core.snowflake import age_days
from guildward.intel.patterns import NameFlag, flags_in

PERSON_BASE = 15


@dataclass(frozen=True, slots=True)
class UserFacts:
    id: int
    username: str
    global_name: str | None = None
    has_avatar: bool = False
    has_banner: bool = False
    is_bot: bool = False
    is_verified_bot: bool = False
    is_system: bool = False  # official Discord system account
    badge_count: int = 0  # public badges (HypeSquad, early supporter, active developer, ...)
    is_self: bool = False  # the person checked themselves
    discord_spammer: bool = False  # Discord's own "likely spammer" flag on the account


def account_age_signals(user_id: int, now: datetime | None = None) -> list[Signal]:
    """Shared with the message check, which also weighs who sent the message."""
    days = age_days(user_id, now)
    d = int(days)
    if days < 2:
        return [Signal("person.age_hours", 40, {"days": d})]
    if days < 7:
        return [Signal("person.age_days", 32, {"days": d})]
    if days < 30:
        return [Signal("person.age_weeks", 20, {"days": d})]
    if days < 180:
        return [Signal("person.age_months", 8, {"days": d})]
    if days > 730:
        return [Signal("person.age_old", -10, {"years": int(days // 365)})]
    return []


def score_user(facts: UserFacts, *, now: datetime | None = None) -> Verdict:
    if facts.is_system:
        return build_verdict(
            Kind.PERSON, [Signal("person.system", -100)], base=PERSON_BASE, confidence=Confidence.LOW
        )

    sigs = account_age_signals(facts.id, now)
    if facts.is_self:
        sigs.append(Signal("person.self", 0))
    if facts.discord_spammer:
        sigs.append(Signal("person.discord_spammer", 45, severe=True))

    if facts.is_bot:
        sigs.append(Signal("person.verified_bot", -10) if facts.is_verified_bot
                    else Signal("person.bot", 5))
    else:
        if not facts.has_avatar:
            sigs.append(Signal("person.default_avatar", 8))
        if facts.has_banner:
            sigs.append(Signal("person.banner", -3))
        if facts.badge_count:
            sigs.append(Signal("person.badges", -4, {"count": facts.badge_count}))

    flags = flags_in(facts.username, facts.global_name)
    sexual = flags & {NameFlag.ADULT, NameFlag.DATING}
    if NameFlag.MINOR_BAIT in flags or (sexual and NameFlag.TEEN in flags):
        sigs.append(Signal("person.name_minor_sexual", 60, severe=True))
    if NameFlag.ADULT in flags:
        sigs.append(Signal("person.name_adult", 45, severe=True))
    if NameFlag.DATING in flags:
        sigs.append(Signal("person.name_dating", 30))
    if NameFlag.DM_BAIT in flags:
        sigs.append(Signal("person.name_dm_bait", 25))
    if NameFlag.IMPERSONATION in flags and not facts.is_verified_bot:
        sigs.append(Signal("person.name_impersonation", 40))

    return build_verdict(Kind.PERSON, sigs, base=PERSON_BASE, confidence=Confidence.LOW)


register({
    "person.age_hours": {
        "en": "This account was created in the last 2 days.",
        "sv": "Kontot skapades under de senaste 2 dagarna.",
    },
    "person.age_days": {
        "en": "This account is only {days} days old. Brand-new accounts are a common warning sign.",
        "sv": "Kontot är bara {days} dagar gammalt. Helt nya konton är ett vanligt varningstecken.",
    },
    "person.age_weeks": {
        "en": "This account is only {days} days old.",
        "sv": "Kontot är bara {days} dagar gammalt.",
    },
    "person.age_months": {
        "en": "This account is fairly new ({days} days).",
        "sv": "Kontot är ganska nytt ({days} dagar).",
    },
    "person.age_old": {
        "en": "This account has existed for {years}+ years.",
        "sv": "Kontot har funnits i {years}+ år.",
    },
    "person.self": {
        "en": "This is your own account.",
        "sv": "Det här är ditt eget konto.",
    },
    "person.discord_spammer": {
        "en": "Discord itself has flagged this account as a likely spammer.",
        "sv": "Discord har själva flaggat kontot som en trolig spammare.",
    },
    "person.system": {
        "en": "This is an official Discord system account.",
        "sv": "Det här är ett officiellt systemkonto från Discord.",
    },
    "person.bot": {
        "en": "This is a bot, not a person. Bots that DM you with offers are often scams.",
        "sv": "Det här är en bot, inte en person. Bottar som skickar DM med erbjudanden är ofta bluff.",
    },
    "person.verified_bot": {
        "en": "A bot verified by Discord.",
        "sv": "En bot som är verifierad av Discord.",
    },
    "person.default_avatar": {
        "en": "No profile picture.",
        "sv": "Ingen profilbild.",
    },
    "person.banner": {
        "en": "Has a custom profile banner.",
        "sv": "Har en egen profilbanner.",
    },
    "person.badges": {
        "en": "Has {count} public Discord badge(s).",
        "sv": "Har {count} offentliga Discord-märken.",
    },
    "person.name_minor_sexual": {
        "en": "Their name mixes young ages with adult or dating words.",
        "sv": "Namnet blandar unga åldrar med vuxen- eller dejtingord.",
    },
    "person.name_adult": {
        "en": "Their name contains adult/sexual words.",
        "sv": "Namnet innehåller vuxna/sexuella ord.",
    },
    "person.name_dating": {
        "en": "Their name looks like they're looking to date online.",
        "sv": "Namnet ser ut som att personen letar efter någon att dejta på nätet.",
    },
    "person.name_dm_bait": {
        "en": "Their name invites people to DM them.",
        "sv": "Namnet uppmanar folk att skicka DM.",
    },
    "person.name_impersonation": {
        "en": "Their name pretends to be Discord staff, a giveaway or a famous creator. "
              "Discord staff never DM you.",
        "sv": "Namnet låtsas vara Discord-personal, en utlottning eller en känd kreatör. "
              "Discord-personal skickar aldrig DM till dig.",
    },
})
