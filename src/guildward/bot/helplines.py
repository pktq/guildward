"""Who a kid can call, per country, for the help flows.

Discord's locale is a language, not a country (most English speakers anywhere use en-US), so the country is the
kid's own pick in /help, saved with their Guildward settings. Until they pick: Swedish -> Sweden, anything else
-> "somewhere else", which points to services that work in every country.

Numbers and links checked against each service's own pages in November 2026.
"""

from __future__ import annotations

from typing import Any

from guildward.core.i18n import Lang

REGIONS = ("se", "us", "gb", "au", "ca", "intl")
FLAGS = {"se": "🇸🇪", "us": "🇺🇸", "gb": "🇬🇧", "au": "🇦🇺", "ca": "🇨🇦", "intl": "🌍"}

# Phrases dropped into the help texts as {emergency}, {talk}, {police}, {crisis}, {hotline}, {removal}.
# Each is (English, Swedish). {removal} starts with a space or is empty.
PHRASES: dict[str, dict[str, tuple[str, str]]] = {
    "se": {
        "emergency": ("**112**", "**112**"),
        "talk": ("Bris on **116 111** (call, text or chat)", "Bris på **116 111** (ring, sms:a eller chatta)"),
        "police": ("the police on **114 14**", "polisen på **114 14**"),
        "crisis": ("Självmordslinjen on **90101**", "Självmordslinjen på **90101**"),
        "hotline": ("the ECPAT Hotline (anonymous)", "ECPAT Hotline (anonymt)"),
        "removal": (" Ditt ECPAT can also help get pictures removed.",
                    " Ditt ECPAT kan också hjälpa till att få bort bilder."),
    },
    "us": {
        "emergency": ("**911**", "**911**"),
        "talk": ("the 988 Lifeline (call or text **988**)", "988 Lifeline (ring eller sms:a **988**)"),
        "police": ("the police, or the FBI at **tips.fbi.gov**", "polisen, eller FBI på **tips.fbi.gov**"),
        "crisis": ("the 988 Lifeline (call or text **988**)", "988 Lifeline (ring eller sms:a **988**)"),
        "hotline": ("NCMEC's CyberTipline (**1-800-843-5678**)", "NCMEC:s CyberTipline (**1-800-843-5678**)"),
        "removal": ("", ""),
    },
    "gb": {
        "emergency": ("**999**", "**999**"),
        "talk": ("Childline on **0800 1111**", "Childline på **0800 1111**"),
        "police": ("the police on **101**", "polisen på **101**"),
        "crisis": ("Samaritans on **116 123**", "Samaritans på **116 123**"),
        "hotline": ("Childline's Report Remove", "Childlines Report Remove"),
        "removal": (" Childline's Report Remove can also help get them removed.",
                    " Childlines Report Remove kan också hjälpa till att få bort dem."),
    },
    "au": {
        "emergency": ("**000**", "**000**"),
        "talk": ("Kids Helpline on **1800 55 1800**", "Kids Helpline på **1800 55 1800**"),
        "police": ("the police on **131 444**, or the ACCCE at accce.gov.au/report",
                   "polisen på **131 444**, eller ACCCE på accce.gov.au/report"),
        "crisis": ("Lifeline on **13 11 14**", "Lifeline på **13 11 14**"),
        "hotline": ("the ACCCE (accce.gov.au/report)", "ACCCE (accce.gov.au/report)"),
        "removal": (" eSafety can also help get pictures removed.",
                    " eSafety kan också hjälpa till att få bort bilder."),
    },
    "ca": {
        "emergency": ("**911**", "**911**"),
        "talk": ("Kids Help Phone on **1-800-668-6868** (or text **686868**)",
                 "Kids Help Phone på **1-800-668-6868** (eller sms:a **686868**)"),
        "police": ("the police, or Cybertip.ca", "polisen, eller Cybertip.ca"),
        "crisis": ("**988** (call or text)", "**988** (ring eller sms:a)"),
        "hotline": ("Cybertip.ca", "Cybertip.ca"),
        "removal": (" NeedHelpNow.ca can also help get pictures removed.",
                    " NeedHelpNow.ca kan också hjälpa till att få bort bilder."),
    },
    "intl": {
        "emergency": ("your local emergency number", "ditt lokala nödnummer"),
        "talk": ("a child helpline in your country (childhelplineinternational.org)",
                 "en stödlinje för barn i ditt land (childhelplineinternational.org)"),
        "police": ("the police where you live", "polisen där du bor"),
        "crisis": ("a crisis line in your country", "en krislinje i ditt land"),
        "hotline": ("a hotline in your country (inhope.org)", "en hotline i ditt land (inhope.org)"),
        "removal": ("", ""),
    },
}

# Link buttons. Help flows name slots ("talk", "police", ...); each country fills the ones it has.
URLS: dict[str, str] = {
    "bris_chat": "https://barn.bris.se/",
    "ecpat_kids": "https://dittecpat.se/kontakta-oss/",
    "ecpat_hotline": "https://ecpat.se/hotline/",
    "ecpat_platforms": "https://dittecpat.se/plattformsguiden/",
    "police_report": "https://polisen.se/utsatt-for-brott/polisanmalan/",
    "police_tip": "https://polisen.se/om-polisen/kontakt/tipsa-polisen/tipsa-polisen-om-sexuella-overgrepp-mot-barn/",
    "mind": "https://mind.se/stod-kunskap/prata-eller-chatta-med-volontar/sjalvmordslinjen/",
    "discord_form": "https://discord.com/report",
    "lifeline988": "https://988lifeline.org/",
    "fbi_tips": "https://tips.fbi.gov/",
    "cybertip": "https://report.cybertip.org/",
    "childline": "https://www.childline.org.uk/",
    "report_remove": "https://www.childline.org.uk/remove",
    "ceop": "https://www.ceop.police.uk/Safety-Centre/",
    "samaritans": "https://www.samaritans.org/",
    "kidshelpline": "https://kidshelpline.com.au/",
    "accce": "https://www.accce.gov.au/report",
    "esafety": "https://www.esafety.gov.au/report",
    "lifeline_au": "https://www.lifeline.org.au/",
    "kidshelpphone": "https://kidshelpphone.ca/",
    "cybertip_ca": "https://www.cybertip.ca/",
    "needhelpnow": "https://needhelpnow.ca/",
    "ca988": "https://988.ca/",
    "helplines": "https://childhelplineinternational.org/helplines/",
    "inhope": "https://www.inhope.org/",
}
SLOTS: dict[str, dict[str, str]] = {
    "se": {"talk": "bris_chat", "police": "police_report", "police_tip": "police_tip", "hotline": "ecpat_hotline",
           "kids_org": "ecpat_kids", "crisis": "mind", "eu_form": "discord_form", "platforms": "ecpat_platforms"},
    "us": {"talk": "lifeline988", "police": "fbi_tips", "hotline": "cybertip", "kids_org": "cybertip"},
    "gb": {"talk": "childline", "police": "ceop", "hotline": "report_remove", "removal": "report_remove",
           "crisis": "samaritans"},
    "au": {"talk": "kidshelpline", "police": "accce", "hotline": "accce", "removal": "esafety",
           "crisis": "lifeline_au"},
    "ca": {"talk": "kidshelpphone", "police": "cybertip_ca", "hotline": "cybertip_ca", "removal": "needhelpnow",
           "crisis": "ca988"},
    "intl": {"talk": "helplines", "hotline": "inhope"},
}
FALLBACK = {"police_tip": "police"}


def default_region(lang: Lang) -> str:
    return "se" if lang == "sv" else "intl"


def region_for(bot: Any, user_id: int, lang: Lang) -> str:
    """The kid's saved country, or the default for their language."""
    pocket = getattr(bot, "pocket", None)
    saved = pocket.region(user_id) if pocket is not None else None
    return saved if saved in REGIONS else default_region(lang)


def phrases(region: str, lang: Lang) -> dict[str, str]:
    i = 1 if lang == "sv" else 0
    return {k: v[i] for k, v in PHRASES.get(region, PHRASES["intl"]).items()}


def slot_url(region: str, slot: str) -> str | None:
    """A slot ("talk", "police", ...) to a URL key for this country, or None if it has no such service."""
    slots = SLOTS.get(region, SLOTS["intl"])
    return slots.get(slot) or (slots.get(FALLBACK[slot]) if slot in FALLBACK else None)
