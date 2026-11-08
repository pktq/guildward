"""Server Intel, layer 2: a structural safety audit of a server whose admins invited Guard.

What the outside view (intel/server.py) can't see: AutoMod rules, media filter, who holds admin,
how many moderators there are, NSFW channels in a server full of kids, and what Guard itself can do.
Each check is pass/fail with a severity and, where Discord's API allows, a one-click fix id.
Live signals (open alerts, raids, red members) are added by guard/reports.py on top.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from guildward.core.i18n import register
from guildward.core.models import Signal

# discord AutoModRuleTriggerType values
AM_KEYWORD, AM_SPAM, AM_PRESET, AM_MENTION, AM_PROFILE = 1, 3, 4, 5, 6
_WEIGHT = {"high": 15, "medium": 8, "low": 3}


@dataclass(frozen=True, slots=True)
class GuildFacts:
    member_count: int
    verification_level: int  # 0 none .. 4 highest
    content_filter: int  # 0 disabled, 1 members without roles, 2 all members
    mfa_level: int  # 1 = moderators need 2FA
    nsfw_level: int  # 3 = age restricted
    automod_triggers: frozenset[int] = field(default_factory=frozenset)
    nsfw_channels: int = 0
    everyone_mentions: bool = False  # @everyone may ping @everyone
    admin_humans: int = 0
    admin_bots: int = 0
    mods: int = 0  # humans who can kick/ban/timeout/manage messages
    has_rules_channel: bool = False
    guard_missing: tuple[str, ...] = ()
    alert_channel_public: bool = False  # Guard's alert channel is visible to @everyone
    minors_est: int = 0


@dataclass(frozen=True, slots=True)
class Check:
    id: str
    ok: bool
    severity: str  # high | medium | low
    fix: str | None
    params: dict[str, int | str] = field(default_factory=dict)

    @property
    def signal(self) -> Signal | None:
        return None if self.ok else Signal(f"audit.{self.id}", _WEIGHT[self.severity], self.params)


def audit_guild(f: GuildFacts) -> list[Check]:
    kids = f.minors_est > 0
    checks = [
        Check("guard_permissions", not f.guard_missing, "high", None, {"perms": ", ".join(f.guard_missing)}),
        Check("alert_channel", not f.alert_channel_public, "high", None),
        Check("verification", f.verification_level >= 2, "high" if f.verification_level == 0 else "medium",
              "verification"),
        Check("content_filter", f.content_filter == 2, "high" if f.content_filter == 0 else "medium",
              "content_filter"),
        Check("automod_presets", AM_PRESET in f.automod_triggers, "medium", "automod_presets"),
        Check("automod_mentions", AM_MENTION in f.automod_triggers, "medium", "automod_mentions"),
        Check("automod_spam", AM_SPAM in f.automod_triggers, "low", "automod_spam"),
        Check("everyone_mentions", not f.everyone_mentions, "medium", "everyone_mentions"),
        Check("mfa", f.mfa_level >= 1, "medium", None),
        Check("nsfw_channels", f.nsfw_channels == 0 or not kids, "high", None, {"n": f.nsfw_channels}),
        Check("age_restricted", f.nsfw_level != 3 or not kids, "high", None),
    ]
    if f.member_count >= 20:
        per_mod = f.member_count / f.mods if f.mods else f.member_count
        checks.append(Check("mod_coverage", f.mods > 0 and per_mod <= 150, "high" if not f.mods else "medium",
                            None, {"mods": f.mods, "per": round(per_mod)}))
    checks.append(Check("admin_sprawl", f.admin_humans <= max(3, f.member_count // 200), "medium", None,
                        {"n": f.admin_humans}))
    checks.append(Check("admin_bots", f.admin_bots <= 2, "low", None, {"n": f.admin_bots}))
    checks.append(Check("rules_channel", f.has_rules_channel, "low", None))
    return checks


def audit_signals(checks: list[Check]) -> list[Signal]:
    sigs = [c.signal for c in checks if c.signal]
    if not any(c.severity in ("high", "medium") and not c.ok for c in checks):
        sigs.append(Signal("audit.strong", -10))
    return sigs


def _c(cid: str, label: tuple[str, str], ok: tuple[str, str], bad: tuple[str, str],
       todo: tuple[str, str]) -> dict[str, dict[str, str]]:
    return {
        f"audit.{cid}.label": {"en": label[0], "sv": label[1]},
        f"audit.{cid}.ok": {"en": ok[0], "sv": ok[1]},
        f"audit.{cid}": {"en": bad[0], "sv": bad[1]},
        f"audit.{cid}.todo": {"en": todo[0], "sv": todo[1]},
    }


register({
    **_c("guard_permissions", ("Guard's permissions", "Guards behörigheter"),
         ("Guard has every permission it needs.", "Guard har alla behörigheter den behöver."),
         ("Guard is missing permissions: {perms}.", "Guard saknar behörigheter: {perms}."),
         ("Give Guard's role the missing permissions so it can act on alerts.",
          "Ge Guards roll de saknade behörigheterna så att den kan agera på larm.")),
    **_c("alert_channel", ("Private alert channel", "Privat larmkanal"),
         ("Only moderators can see Guard's alerts.", "Bara moderatorer kan se Guards larm."),
         ("Everyone can see the alert channel, so Guard isn't posting alerts there (they name kids).",
          "Alla kan se larmkanalen, så Guard postar inga larm där (de nämner barn)."),
         ("Hide the alert channel from @everyone, or run /guard setup with a private channel.",
          "Dölj larmkanalen för @everyone, eller kör /guard setup med en privat kanal.")),
    **_c("verification", ("Verification level", "Verifieringsnivå"),
         ("New members must wait or verify before they can talk.", "Nya medlemmar måste vänta eller verifiera sig innan de kan skriva."),
         ("New accounts can talk right away. Throwaway accounts get in easily.",
          "Nya konton kan skriva direkt. Engångskonton kommer lätt in."),
         ("Raise verification to Medium (account older than 5 minutes) or higher.",
          "Höj verifieringen till Medel (kontot äldre än 5 minuter) eller högre.")),
    **_c("content_filter", ("Explicit media filter", "Filter för explicit media"),
         ("Explicit images are filtered for everyone.", "Explicita bilder filtreras för alla."),
         ("Explicit images are not filtered for all members.", "Explicita bilder filtreras inte för alla medlemmar."),
         ("Turn on the explicit media filter for all members.", "Slå på filtret för explicit media för alla medlemmar.")),
    **_c("automod_presets", ("AutoMod word filters", "AutoMod-ordfilter"),
         ("Discord's sexual-content and slur filters are on.", "Discords filter för sexuellt innehåll och skällsord är på."),
         ("Discord's built-in sexual-content filter is off.", "Discords inbyggda filter för sexuellt innehåll är av."),
         ("Turn on AutoMod's commonly flagged words filter (sexual content, slurs, profanity).",
          "Slå på AutoMods filter för vanligt flaggade ord (sexuellt innehåll, skällsord, svordomar).")),
    **_c("automod_mentions", ("Mention spam protection", "Skydd mot massomnämnanden"),
         ("Mass-mention spam is blocked.", "Spam med massomnämnanden blockeras."),
         ("Nothing stops one account from pinging dozens of members.", "Inget hindrar ett konto från att pinga dussintals medlemmar."),
         ("Turn on AutoMod's mention spam rule.", "Slå på AutoMods regel mot massomnämnanden.")),
    **_c("automod_spam", ("Spam filter", "Spamfilter"),
         ("Suspected spam is blocked.", "Misstänkt spam blockeras."),
         ("Discord's spam filter is off.", "Discords spamfilter är av."),
         ("Turn on AutoMod's suspected spam rule.", "Slå på AutoMods regel mot misstänkt spam.")),
    **_c("everyone_mentions", ("@everyone pings", "@everyone-pingar"),
         ("Regular members can't ping @everyone.", "Vanliga medlemmar kan inte pinga @everyone."),
         ("Any member can ping @everyone, a favourite raid trick.", "Alla medlemmar kan pinga @everyone, ett favorittrick vid raider."),
         ("Remove 'Mention @everyone' from the @everyone role.", "Ta bort 'Nämn @everyone' från rollen @everyone.")),
    **_c("mfa", ("2FA for moderators", "2FA för moderatorer"),
         ("Moderators must use two-factor login.", "Moderatorer måste använda tvåstegsinloggning."),
         ("Moderators don't need 2FA. A stolen mod account can do a lot of harm.",
          "Moderatorer behöver inte 2FA. Ett stulet mod-konto kan göra stor skada."),
         ("Server owner: Server Settings → Safety Setup → require 2FA for moderator actions.",
          "Serverägaren: Serverinställningar → Säkerhetsinställningar → kräv 2FA för moderatoråtgärder.")),
    **_c("nsfw_channels", ("Age-restricted channels", "Åldersbegränsade kanaler"),
         ("No age-restricted channels next to young members.", "Inga åldersbegränsade kanaler bredvid unga medlemmar."),
         ("{n} age-restricted (NSFW) channel(s) in a server with members under 18.",
          "{n} åldersbegränsade (NSFW) kanaler i en server med medlemmar under 18."),
         ("Remove NSFW channels, or move adult content to a separate 18+ server.",
          "Ta bort NSFW-kanaler, eller flytta vuxeninnehåll till en separat 18+-server.")),
    **_c("age_restricted", ("Server age rating", "Serverns åldersgräns"),
         ("The server is not marked 18+.", "Servern är inte markerad 18+."),
         ("The server is marked 18+ but members under 18 are active here.",
          "Servern är markerad 18+ men medlemmar under 18 är aktiva här."),
         ("Remove members under 18 or the adult content.", "Ta bort medlemmar under 18 eller vuxeninnehållet.")),
    **_c("mod_coverage", ("Moderator coverage", "Moderatortäckning"),
         ("{mods} moderators, about one per {per} members.", "{mods} moderatorer, ungefär en per {per} medlemmar."),
         ("Only {mods} moderator(s): about one per {per} members.", "Bara {mods} moderator(er): ungefär en per {per} medlemmar."),
         ("Aim for at least one active moderator per 150 members.", "Sikta på minst en aktiv moderator per 150 medlemmar.")),
    **_c("admin_sprawl", ("Administrator role", "Administratörsroll"),
         ("Admin rights are limited to a few people.", "Adminrättigheter är begränsade till ett fåtal."),
         ("{n} people have Administrator. Every one of them can remove all protections.",
          "{n} personer har Administratör. Var och en kan ta bort alla skydd."),
         ("Give moderators only the permissions they need instead of Administrator.",
          "Ge moderatorer bara de behörigheter de behöver i stället för Administratör.")),
    **_c("admin_bots", ("Bots with Administrator", "Bottar med Administratör"),
         ("Few or no bots have Administrator.", "Få eller inga bottar har Administratör."),
         ("{n} bots have Administrator. A hacked bot can wreck the server.",
          "{n} bottar har Administratör. En hackad bot kan förstöra servern."),
         ("Take Administrator away from bots that don't need it.", "Ta bort Administratör från bottar som inte behöver det.")),
    **_c("rules_channel", ("Rules channel", "Regelkanal"),
         ("The server has a rules channel.", "Servern har en regelkanal."),
         ("No rules channel is set.", "Ingen regelkanal är vald."),
         ("Set a rules channel that says how members may contact each other.",
          "Välj en regelkanal som säger hur medlemmar får kontakta varandra.")),
    "audit.strong": {"en": "Strong safety settings.", "sv": "Starka säkerhetsinställningar."},
    # live server signals (guard/reports.py)
    "live.open_red": {"en": "{n} red alert(s) waiting for a moderator.", "sv": "{n} röda larm väntar på en moderator."},
    "live.red_members": {"en": "{n} member(s) currently rated red.", "sv": "{n} medlem(mar) har just nu rött betyg."},
    "live.raid": {"en": "A join raid happened in the last 7 days.", "sv": "En raid skedde under de senaste 7 dagarna."},
    "live.slow_response": {"en": "Alerts take about {min} minutes to get handled.", "sv": "Det tar ungefär {min} minuter innan larm hanteras."},
    "live.stale_alerts": {"en": "{n} alert(s) open for more than a day.", "sv": "{n} larm har varit öppna i mer än ett dygn."},
    "live.flag_rate": {"en": "{rate} flagged messages per 1,000 this week.", "sv": "{rate} flaggade meddelanden per 1 000 den här veckan."},
    "live.quiet": {"en": "No alerts in the last 7 days.", "sv": "Inga larm under de senaste 7 dagarna."},
    "live.fast_response": {"en": "Moderators handle alerts fast (about {min} minutes).", "sv": "Moderatorerna hanterar larm snabbt (ungefär {min} minuter)."},
})
