"""Guard embeds: alerts for the moderator channel, reports for /guard commands, the kid-facing safety tip."""

from __future__ import annotations

from typing import Any

import discord

from guildward.bot.render import COLORS, DOTS
from guildward.core.i18n import Lang, register, t
from guildward.core.models import Level

GREY = 0x57606A


def _lv(level: str) -> Level:
    return Level(level)


def alert_embed(a: dict[str, Any], lang: Lang, *, dashboard_url: str | None, quote: bool) -> discord.Embed:
    lv = _lv(a["level"])
    e = discord.Embed(title=f"{DOTS[lv]} {a['title']}"[:256], description=a["summary"][:1500], color=COLORS[lv])
    lines = [("‼️ " if s["severe"] else "⚠️ " if s["weight"] > 0 else "• ") + s["text"]
             for s in a["signals"] if s["weight"] != 0 or s["code"].startswith("ctx.")][:8]
    if lines:
        e.add_field(name=t("g.why", lang), value="\n".join(lines)[:1024], inline=False)
    if quote and a.get("quote"):
        e.add_field(name=t("g.quote", lang), value="```" + discord.utils.escape_markdown(a["quote"])[:900]
                    .replace("```", "'''") + "```", inline=False)
    who = []
    if a.get("user"):
        who.append(f"<@{a['user']['id']}>")
    if a.get("target"):
        who.append(f"→ <@{a['target']['id']}>" + (" 🧒" if a["target"]["minor"] else ""))
    if who:
        e.add_field(name=t("g.who", lang), value=" ".join(who), inline=True)
    e.add_field(name=t("g.score", lang), value=f"**{a['score']}/100**", inline=True)
    links = []
    if a.get("jump_url"):
        links.append(f"[{t('g.jump', lang)}]({a['jump_url']})")
    if dashboard_url and a.get("user"):
        links.append(f"[{t('g.open_dash', lang)}]({dashboard_url})")
    if links:
        e.add_field(name="​", value=" · ".join(links), inline=True)
    if a["status"] != "open":
        e.add_field(name=t("g.status", lang),
                    value=t(f"g.status_{a['status']}", lang, by=a.get("resolved_by") or "?",
                            action=t(f"g.act_{a['action']}", lang) if a.get("action") else "-"), inline=False)
        e.color = GREY
    e.set_footer(text=t("g.footer_alert", lang, id=a["id"]))
    return e


def person_embed(r: dict[str, Any], lang: Lang) -> discord.Embed:
    v, m, p = r["verdict"], r["member"], r["prediction"]
    lv = _lv(v["level"])
    e = discord.Embed(title=f"{DOTS[lv]} {t('g.person_title', lang, name=m['name'])}"[:256],
                      description="\n".join(r["summary"])[:2000], color=COLORS[lv])
    risks = [("‼️ " if s["severe"] else "⚠️ ") + s["text"] for s in v["signals"] if s["weight"] > 0][:8]
    good = ["✅ " + s["text"] for s in v["signals"] if s["weight"] < 0][:3]
    e.add_field(name=t("g.why", lang), value="\n".join(risks + good)[:1024] or t("ui.no_signals", lang), inline=False)
    arrow = {"rising": "📈", "falling": "📉", "stable": "➡️"}[p["trajectory"]]
    e.add_field(name=t("g.prediction", lang), value=f"{arrow} {p['text']}", inline=False)
    if r["contacts"]:
        lines = [f"{DOTS[_lv(c['level'])]} {c['user']['name']}{' 🧒' if c['user']['minor'] else ''}: "
                 + (", ".join(c["stages"]) or t("g.no_stages", lang)) for c in r["contacts"][:5]]
        e.add_field(name=t("g.contacts", lang), value="\n".join(lines)[:1024], inline=False)
    st = r["stats"]
    e.add_field(name=t("g.score", lang), value=f"**{v['score']}/100**", inline=True)
    e.add_field(name=t("g.stats", lang), value=t("g.stats_line", lang, **st), inline=True)
    e.set_footer(text=v["confidence"])
    return e


def overview_embed(o: dict[str, Any], lang: Lang) -> discord.Embed:
    h = o["health"]
    lv = _lv(h["level"])
    e = discord.Embed(title=f"{DOTS[lv]} {t('g.server_title', lang, name=o['guild']['name'], grade=h['grade'])}"[:256],
                      description="\n".join(o["summary"])[:2000], color=COLORS[lv])
    fails = [("🔴 " if c["severity"] == "high" else "🟡 " if c["severity"] == "medium" else "⚪ ") + c["detail"]
             for c in o["audit"] if not c["ok"]]
    if fails:
        e.add_field(name=t("g.fix_these", lang), value="\n".join(fails)[:1024], inline=False)
    if o["top_risks"]:
        e.add_field(name=t("g.top_risks", lang), value="\n".join(
            f"{DOTS[_lv(m['level'])]} <@{m['id']}> {m['score']}: {m['top_signal'] or ''}" for m in o["top_risks"][:5]
        )[:1024], inline=False)
    if o["permissions_missing"]:
        e.add_field(name=t("g.missing", lang), value=", ".join(o["permissions_missing"]), inline=False)
    e.add_field(name=t("g.score", lang), value=f"**{h['score']}/100** · {h['grade']}", inline=True)
    e.set_footer(text=h["confidence"])
    return e


def warn_embed(server: str, lang: Lang) -> discord.Embed:
    e = discord.Embed(title=t("g.warn_title", lang), description=t("g.warn_body", lang, server=server),
                      color=COLORS[Level.YELLOW])
    e.set_footer(text=t("g.warn_footer", lang))
    return e


def notice(key: str, lang: Lang, **params: object) -> discord.Embed:
    return discord.Embed(description=t(key, lang, **params), color=GREY)


register({
    "g.why": {"en": "Why", "sv": "Varför"},
    "g.quote": {"en": "Message (not stored by Guard)", "sv": "Meddelandet (sparas inte av Guard)"},
    "g.who": {"en": "Who", "sv": "Vem"},
    "g.score": {"en": "Risk", "sv": "Risk"},
    "g.jump": {"en": "Jump to message", "sv": "Gå till meddelandet"},
    "g.open_dash": {"en": "Full report", "sv": "Hela rapporten"},
    "g.status": {"en": "Handled", "sv": "Hanterat"},
    "g.status_resolved": {"en": "Resolved by {by} ({action})", "sv": "Löst av {by} ({action})"},
    "g.status_false_positive": {"en": "Marked false alarm by {by}", "sv": "Markerat som falsklarm av {by}"},
    "g.footer_alert": {"en": "Guildward Guard · alert #{id} · message text is never stored",
                       "sv": "Guildward Guard · larm #{id} · meddelandetext sparas aldrig"},
    "g.person_title": {"en": "Member report: {name}", "sv": "Medlemsrapport: {name}"},
    "g.server_title": {"en": "Safety report: {name} (grade {grade})", "sv": "Säkerhetsrapport: {name} (betyg {grade})"},
    "g.prediction": {"en": "Where it's heading", "sv": "Vart det är på väg"},
    "g.contacts": {"en": "Who they talk to", "sv": "Vem hen pratar med"},
    "g.no_stages": {"en": "nothing concerning", "sv": "inget oroande"},
    "g.stats": {"en": "Numbers", "sv": "Siffror"},
    "g.stats_line": {"en": "{messages} msgs · {flagged} flagged · {minor_targets} minors targeted · {reports} reports",
                     "sv": "{messages} medd · {flagged} flaggade · {minor_targets} minderåriga · {reports} anmälningar"},
    "g.fix_these": {"en": "Fix these", "sv": "Åtgärda detta"},
    "g.top_risks": {"en": "Highest-risk members", "sv": "Medlemmar med högst risk"},
    "g.missing": {"en": "Guard is missing permissions", "sv": "Guard saknar behörigheter"},
    "g.warn_title": {"en": "🛡️ A safety tip from Guildward", "sv": "🛡️ Ett säkerhetstips från Guildward"},
    "g.warn_body": {
        "en": "Someone in **{server}** just sent you a message with warning signs, like asking for photos, "
              "secrets, your age, or moving to another app.\n\n**You did nothing wrong.**\n"
              "• Don't reply and don't send anything.\n• Don't move to Snapchat, DMs or any other app with them.\n"
              "• Tell an adult you trust. You won't get in trouble.\n\n"
              "The server's moderators have been told. Need to talk? **Bris: 116 111** (free, anonymous).",
        "sv": "Någon i **{server}** skickade just ett meddelande till dig med varningstecken, som att be om bilder, "
              "hemligheter, din ålder eller att byta till en annan app.\n\n**Du har inte gjort något fel.**\n"
              "• Svara inte och skicka ingenting.\n• Flytta inte till Snapchat, DM eller någon annan app med personen.\n"
              "• Berätta för en vuxen du litar på. Du får inte skäll.\n\n"
              "Serverns moderatorer har fått veta. Vill du prata? **Bris: 116 111** (gratis, anonymt).",
    },
    "g.warn_footer": {"en": "Guildward · free, open-source child safety", "sv": "Guildward · gratis barnsäkerhet med öppen källkod"},
    # buttons
    "g.btn_timeout": {"en": "Timeout 1h", "sv": "Stäng av 1 h"},
    "g.btn_kick": {"en": "Kick", "sv": "Sparka"},
    "g.btn_ban": {"en": "Ban", "sv": "Banna"},
    "g.btn_delete": {"en": "Delete message", "sv": "Radera meddelandet"},
    "g.btn_watch": {"en": "Watch", "sv": "Bevaka"},
    "g.btn_resolve": {"en": "Resolved", "sv": "Löst"},
    "g.btn_false_positive": {"en": "False alarm", "sv": "Falsklarm"},
    "g.btn_dashboard": {"en": "Open dashboard", "sv": "Öppna instrumentpanelen"},
    "g.btn_fix_all": {"en": "Apply recommended settings", "sv": "Använd rekommenderade inställningar"},
    "g.btn_confirm_erase": {"en": "Yes, erase everything", "sv": "Ja, radera allt"},
    # action names
    "g.act_timeout": {"en": "timeout", "sv": "avstängning"},
    "g.act_kick": {"en": "kick", "sv": "sparkad"},
    "g.act_ban": {"en": "ban", "sv": "bannad"},
    "g.act_delete": {"en": "message deleted", "sv": "meddelandet raderat"},
    "g.act_watch": {"en": "watching", "sv": "bevakas"},
    "g.act_resolve": {"en": "no action", "sv": "ingen åtgärd"},
    "g.act_false_positive": {"en": "false alarm", "sv": "falsklarm"},
    "g.act_trust": {"en": "trusted", "sv": "pålitlig"},
    "g.act_clear": {"en": "status cleared", "sv": "status rensad"},
    "g.act_quarantine": {"en": "quarantined", "sv": "i karantän"},
    # results / notices
    "g.done": {"en": "Done: {action}.", "sv": "Klart: {action}."},
    "g.no_perm_user": {"en": "You need the {perm} permission for that.", "sv": "Du behöver behörigheten {perm} för det."},
    "g.no_perm_bot": {"en": "Guard is missing the {perm} permission. Move Guard's role up and give it {perm}.",
                      "sv": "Guard saknar behörigheten {perm}. Flytta upp Guards roll och ge den {perm}."},
    "g.hierarchy": {"en": "Guard can't act on this member: their highest role is above Guard's.",
                    "sv": "Guard kan inte agera mot den här medlemmen: hens högsta roll är över Guards."},
    "g.gone": {"en": "That member or message is no longer here.", "sv": "Medlemmen eller meddelandet finns inte längre kvar."},
    "g.failed": {"en": "Discord refused that action.", "sv": "Discord nekade åtgärden."},
    "g.unknown_alert": {"en": "That alert no longer exists.", "sv": "Larmet finns inte längre."},
    "g.setup_done": {
        "en": "Guard is set up. Alerts go to {channel}, mode: **{mode}**.\n\nNext: run `/guard scan` to learn from recent "
              "history, and open the dashboard for the full picture.",
        "sv": "Guard är installerad. Larm går till {channel}, läge: **{mode}**.\n\nNästa steg: kör `/guard scan` för att lära "
              "av den senaste historiken, och öppna instrumentpanelen för hela bilden.",
    },
    "g.cant_post": {"en": "Guard can't post in {channel}. Give it View Channel, Send Messages and Embed Links there.",
                    "sv": "Guard kan inte skriva i {channel}. Ge den Visa kanal, Skicka meddelanden och Bädda in länkar där."},
    "g.dash_link": {"en": "Your private dashboard link (works once, for 10 minutes). Don't share it.",
                    "sv": "Din privata länk till instrumentpanelen (fungerar en gång, i 10 minuter). Dela den inte."},
    "g.dash_off": {"en": "The dashboard isn't running on this Guard instance.", "sv": "Instrumentpanelen körs inte på den här Guard-instansen."},
    "g.scan_start": {"en": "Scanning the last {days} days of readable channels. This can take a few minutes…",
                     "sv": "Skannar de senaste {days} dagarna i läsbara kanaler. Det kan ta några minuter…"},
    "g.scan_done": {"en": "Scan done: {msgs} messages in {channels} channels, {flagged} flagged, {members} members scored. "
                          "No alerts were sent for old messages; check the dashboard.",
                    "sv": "Skanning klar: {msgs} meddelanden i {channels} kanaler, {flagged} flaggade, {members} medlemmar bedömda. "
                          "Inga larm skickades för gamla meddelanden; kolla instrumentpanelen."},
    "g.scan_busy": {"en": "A scan is already running for this server.", "sv": "En skanning pågår redan för servern."},
    "g.reported": {"en": "Thanks. The moderators have been told, and only they can see who reported. "
                         "If someone is scaring you, tell an adult you trust too.",
                   "sv": "Tack. Moderatorerna har fått veta, och bara de kan se vem som anmälde. "
                         "Om någon skrämmer dig, berätta också för en vuxen du litar på."},
    "g.already_reported": {"en": "You already reported this. The moderators have it.", "sv": "Du har redan anmält detta. Moderatorerna har det."},
    "g.bot_missing": {"en": "Guildward was added to this server with checks only, so Guard can't see it. To use Guard, an admin adds the full bot: {url}",
                      "sv": "Guildward lades till i servern med bara kollar, så Guard kan inte se den. För att använda Guard lägger en admin till hela botten: {url}"},
    "g.not_setup": {"en": "Guard isn't set up here yet. An admin can run `/guard setup`.",
                    "sv": "Guard är inte installerad här än. En admin kan köra `/guard setup`."},
    "g.status_set": {"en": "{name}: {action}.", "sv": "{name}: {action}."},
    "g.erase_confirm": {"en": "This permanently deletes everything Guard knows about this server: members, scores, alerts, "
                              "reports. It can't be undone. Guard keeps running and starts fresh.",
                        "sv": "Det här raderar permanent allt Guard vet om servern: medlemmar, betyg, larm och anmälningar. "
                              "Det går inte att ångra. Guard fortsätter köras och börjar om från noll."},
    "g.erased": {"en": "All Guard data for this server is erased.", "sv": "All Guard-data för servern är raderad."},
    "g.welcome": {"en": "👋 Thanks for adding **Guildward** (Guard). An admin can run `/guard setup` to pick an alert channel. "
                        "Guard never stores message text.",
                  "sv": "👋 Tack för att ni lade till **Guildward** (Guard). En admin kan köra `/guard setup` för att välja larmkanal. "
                        "Guard sparar aldrig meddelandetext."},
    "g.fix_ok_verification": {"en": "Verification raised to Medium.", "sv": "Verifieringen höjd till Medel."},
    "g.fix_ok_content_filter": {"en": "Explicit media filter is on for all members.", "sv": "Filtret för explicit media är på för alla."},
    "g.fix_ok_automod_presets": {"en": "AutoMod word filters added.", "sv": "AutoMod-ordfilter tillagda."},
    "g.fix_ok_automod_spam": {"en": "AutoMod spam rule added.", "sv": "AutoMods spamregel tillagd."},
    "g.fix_ok_automod_mentions": {"en": "AutoMod mention spam rule added.", "sv": "AutoMods regel mot massomnämnanden tillagd."},
    "g.fix_ok_everyone_mentions": {"en": "Regular members can no longer ping @everyone.", "sv": "Vanliga medlemmar kan inte längre pinga @everyone."},
    "g.fix_unknown": {"en": "Unknown fix.", "sv": "Okänd åtgärd."},
    "g.fixes_applied": {"en": "Applied: {done}. Not possible: {failed}.", "sv": "Genomfört: {done}. Gick inte: {failed}."},
    # command strings
    "gcmd.guard": {"en": "Guildward Guard: server safety", "sv": "Guildward Guard: serversäkerhet"},
    "gcmd.setup": {"en": "Set up Guard: alert channel and mode", "sv": "Installera Guard: larmkanal och läge"},
    "gcmd.setup.channel": {"en": "Private channel where moderators get alerts", "sv": "Privat kanal där moderatorer får larm"},
    "gcmd.setup.mode": {"en": "observe = alerts only, protect = Guard also acts", "sv": "observe = bara larm, protect = Guard agerar också"},
    "gcmd.setup.lang": {"en": "Language of alerts", "sv": "Språk för larm"},
    "gcmd.audit": {"en": "Safety report for this server", "sv": "Säkerhetsrapport för servern"},
    "gcmd.report": {"en": "Risk report for one member", "sv": "Riskrapport för en medlem"},
    "gcmd.report.member": {"en": "The member to check", "sv": "Medlemmen att kolla"},
    "gcmd.dashboard": {"en": "Get a private sign-in link to the dashboard", "sv": "Få en privat inloggningslänk till instrumentpanelen"},
    "gcmd.scan": {"en": "Learn from recent message history", "sv": "Lär av den senaste meddelandehistoriken"},
    "gcmd.scan.days": {"en": "How many days back (1-30)", "sv": "Hur många dagar bakåt (1-30)"},
    "gcmd.watch": {"en": "Put a member on the watch list", "sv": "Sätt en medlem på bevakningslistan"},
    "gcmd.trust": {"en": "Mark a member as trusted", "sv": "Markera en medlem som pålitlig"},
    "gcmd.clear": {"en": "Clear a member's watch/trust status", "sv": "Rensa en medlems bevaknings-/pålitlighetsstatus"},
    "gcmd.erase": {"en": "Erase all data Guard holds about this server", "sv": "Radera all data Guard har om servern"},
    "gcmd.ctx_report": {"en": "Report to mods", "sv": "Anmäl till moddar"},
    "gcmd.ctx_member": {"en": "Guard report", "sv": "Guard-rapport"},
})
