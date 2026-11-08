"""'I need help': calm first steps per situation, an evidence card, and Discord's own safety settings.

Numbers, links and Discord menu paths were checked against each organisation's own pages in November 2026.
Views are stateless: URL buttons plus one Select whose custom_id carries the language, so it keeps working
in ephemeral messages and after a restart once registered with `bot.add_view(...)` (see `persistent_views`).
"""

from __future__ import annotations

from datetime import UTC, datetime

import discord

from guildward.core.i18n import LANGS, Lang, register, t

SITUATIONS = ("threat", "pics", "meet", "scam", "bully", "other")
SETTINGS = "settings"  # extra picker option; not a situation
PICK_ID = "gw:help:pick:{lang}"

HELP_COLOR = 0x3B82C4
SETTINGS_COLOR = 0x2EA043
EVIDENCE_COLOR = 0x57606A
MAX_EXCERPT = 500

EMOJI = {"threat": "🛑", "pics": "📵", "meet": "📍", "scam": "🎣", "bully": "💬", "other": "❓", SETTINGS: "🔒"}


def _support(article: int, lang: Lang) -> str:
    return f"https://support.discord.com/hc/{'sv' if lang == 'sv' else 'en-us'}/articles/{article}"


def _url(key: str, lang: Lang) -> str:
    return {
        "bris_chat": "https://barn.bris.se/",
        "ecpat_kids": "https://dittecpat.se/kontakta-oss/",
        "ecpat_hotline": "https://ecpat.se/hotline/",
        "ecpat_platforms": "https://dittecpat.se/plattformsguiden/",
        "police_report": "https://polisen.se/utsatt-for-brott/polisanmalan/",
        "police_tip": "https://polisen.se/om-polisen/kontakt/tipsa-polisen/tipsa-polisen-om-sexuella-overgrepp-mot-barn/",
        "mind": "https://mind.se/stod-kunskap/prata-eller-chatta-med-volontar/sjalvmordslinjen/",
        "takeitdown": "https://takeitdown.ncmec.org/sv/" if lang == "sv" else "https://takeitdown.ncmec.org/",
        "cybertip": "https://report.cybertip.org/",
        "helplines": "https://childhelplineinternational.org/helplines/",
        "discord_report": "https://discord.com/safety/360044103651-reporting-abusive-behavior-to-discord",
        "discord_form": "https://discord.com/report",
        "discord_safety": "https://discord.com/safety",
        "discord_family": "https://discord.com/safety-family-center",
        "discord_teen": _support(42178056096663, lang),
        "discord_privacy": _support(217916488, lang),
        "discord_hacked": _support(24160905919511, lang),
    }[key]


# Swedish resources first in both languages (Sweden-first); English adds US/international lines.
LINKS: dict[str, tuple[str, ...]] = {
    "threat": ("takeitdown", "bris_chat", "ecpat_kids", "police_report", "discord_report", "discord_form", "mind"),
    "pics": ("bris_chat", "takeitdown", "ecpat_kids", "ecpat_hotline", "police_tip", "discord_report", "discord_form"),
    "meet": ("bris_chat", "police_report", "discord_report", "discord_privacy"),
    "scam": ("discord_hacked", "discord_report", "police_report", "bris_chat"),
    "bully": ("bris_chat", "discord_privacy", "discord_report", "police_report"),
    "other": ("bris_chat", "ecpat_kids", "discord_safety", "discord_report"),
    SETTINGS: ("discord_teen", "discord_privacy", "discord_family", "discord_safety", "ecpat_platforms"),
}
EN_EXTRA: dict[str, tuple[str, ...]] = {"threat": ("cybertip", "helplines"), "pics": ("cybertip", "helplines")}


def _links(key: str, lang: Lang) -> list[tuple[str, str]]:
    keys = LINKS[key] + (EN_EXTRA.get(key, ()) if lang == "en" else ())
    return [(t(f"help.link.{k}", lang), _url(k, lang)) for k in keys]


def quick_links(lang: Lang) -> list[tuple[str, str]]:
    """(label, url) pairs for URL buttons under an automatic alert DM."""
    return [(t(f"help.link.{k}", lang), _url(k, lang)) for k in ("bris_chat", "discord_report", "discord_privacy")]


class SituationPicker(discord.ui.Select):
    def __init__(self, lang: Lang, current: str | None = None) -> None:
        options = [
            discord.SelectOption(label=t(f"help.opt.{k}", lang), description=t(f"help.opt.{k}.desc", lang),
                                 value=k, emoji=EMOJI[k], default=k == current)
            for k in (*SITUATIONS, SETTINGS)
        ]
        super().__init__(custom_id=PICK_ID.format(lang=lang), placeholder=t("help.pick", lang), options=options,
                         min_values=1, max_values=1, row=0)
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        embed, view = situation_for(self.values[0], self.lang)
        await interaction.response.edit_message(embed=embed, view=view)


def _view(lang: Lang, current: str | None, links: list[tuple[str, str]]) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(SituationPicker(lang, current))
    for label, url in links:
        view.add_item(discord.ui.Button(label=label, url=url))
    return view


def persistent_views() -> list[discord.ui.View]:
    """One picker view per language, for `bot.add_view` at startup so old menus keep working."""
    return [_view(lang, None, []) for lang in LANGS]


def _footer(embed: discord.Embed, lang: Lang) -> discord.Embed:
    return embed.set_footer(text=t("help.footer", lang))


def help_menu(lang: Lang) -> tuple[discord.Embed, discord.ui.View]:
    embed = discord.Embed(title=f"💙 {t('help.menu.title', lang)}", description=t("help.menu.body", lang),
                          color=HELP_COLOR)
    return _footer(embed, lang), _view(lang, None, [(t("help.link.bris_chat", lang), _url("bris_chat", lang))])


def situation_embed(key: str, lang: Lang) -> tuple[discord.Embed, discord.ui.View]:
    if key not in SITUATIONS:
        raise KeyError(key)
    embed = discord.Embed(title=f"{EMOJI[key]} {t(f'help.{key}.title', lang)}",
                          description=t(f"help.{key}.steps", lang), color=HELP_COLOR)
    embed.add_field(name=t("help.contacts.title", lang), value=t("help.contacts", lang), inline=False)
    return _footer(embed, lang), _view(lang, key, _links(key, lang))


def situation_for(key: str, lang: Lang) -> tuple[discord.Embed, discord.ui.View]:
    """Select callback logic: any picker value (or an unknown one from an old menu) to content."""
    if key == SETTINGS:
        return settings_embed(lang)
    return situation_embed(key if key in SITUATIONS else "other", lang)


SETTINGS_FIELDS = ("dms", "friends", "content", "bothers", "parent", "age")


def settings_embed(lang: Lang) -> tuple[discord.Embed, discord.ui.View]:
    embed = discord.Embed(title=f"{EMOJI[SETTINGS]} {t('help.settings.title', lang)}",
                          description=t("help.settings.intro", lang), color=SETTINGS_COLOR)
    for f in SETTINGS_FIELDS:
        embed.add_field(name=t(f"help.settings.{f}", lang), value=t(f"help.settings.{f}.body", lang), inline=False)
    return _footer(embed, lang), _view(lang, SETTINGS, _links(SETTINGS, lang))


def _escape(text: str) -> str:
    return discord.utils.escape_mentions(discord.utils.escape_markdown(text, ignore_links=False))


def _excerpt(text: str) -> str:
    raw, cut = text.strip(), False
    out = _escape(raw)
    while len(out) > MAX_EXCERPT:  # escaping adds backslashes, so trim the source until the escaped form fits
        raw, cut = raw[: len(raw) - max(1, len(out) - MAX_EXCERPT + 1)], True
        out = _escape(raw)
    return out[: MAX_EXCERPT - 1] + "…" if cut else out


def _when(dt: datetime) -> str:
    dt = (dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt).astimezone(UTC)
    return f"{discord.utils.format_dt(dt, 'F')}\n`{dt:%Y-%m-%d %H:%M} UTC`"


def evidence_embed(*, lang: Lang, sender_name: str, sender_id: int, sender_created: datetime,
                   message_url: str | None, sent_at: datetime | None, excerpt: str | None) -> discord.Embed:
    embed = discord.Embed(title=t("help.ev.title", lang), description=t("help.ev.intro", lang), color=EVIDENCE_COLOR)
    embed.add_field(name=t("help.ev.sender", lang),
                    value=t("help.ev.sender_value", lang, name=_escape(sender_name)[:100], id=int(sender_id)),
                    inline=False)
    embed.add_field(name=t("help.ev.created", lang), value=_when(sender_created), inline=True)
    if sent_at is not None:
        embed.add_field(name=t("help.ev.sent", lang), value=_when(sent_at), inline=True)
    if message_url and message_url.startswith("https://discord.com/channels/") and " " not in message_url:
        embed.add_field(name=t("help.ev.link", lang), value=message_url[:300], inline=False)
    if excerpt and excerpt.strip():
        embed.add_field(name=t("help.ev.excerpt", lang), value=_excerpt(excerpt), inline=False)
    embed.add_field(name=t("help.ev.how", lang), value=t("help.ev.how_value", lang), inline=False)
    return _footer(embed, lang)


register({
    "help.footer": {
        "en": "Guildward · Only you can see this · Nothing here is saved",
        "sv": "Guildward · Bara du ser detta · Inget här sparas",
    },
    # menu
    "help.menu.title": {"en": "You did the right thing by asking", "sv": "Det var rätt av dig att fråga"},
    "help.menu.body": {
        "en": "You're not in trouble. Pick what's happening below and you'll get simple steps, one at a time.\n\n"
              "🚨 **In danger right now?** Call **112**.\n"
              "💬 **Want to talk to a person?** Bris: call or text **116 111**, or chat. Any time, free, "
              "and you don't have to say your name.\n\n"
              "Nothing you pick here is saved or sent to anyone.",
        "sv": "Du har inte gjort något fel, och du kommer inte att få skäll. Välj vad som händer här nedanför, "
              "så får du enkla steg, ett i taget.\n\n"
              "🚨 **Är du i fara just nu?** Ring **112**.\n"
              "💬 **Vill du prata med en människa?** Bris: ring eller sms:a **116 111**, eller chatta. Dygnet runt, "
              "gratis, och du behöver inte säga vem du är.\n\n"
              "Inget du väljer här sparas eller skickas till någon.",
    },
    "help.pick": {"en": "What's happening?", "sv": "Vad är det som händer?"},
    "help.opt.threat": {"en": "Someone threatens to share my pictures", "sv": "Någon hotar att sprida bilder på mig"},
    "help.opt.threat.desc": {
        "en": "They want money, more pictures, or something else",
        "sv": "De vill ha pengar, fler bilder eller något annat",
    },
    "help.opt.pics": {
        "en": "Someone asks for pictures or sends sexual stuff",
        "sv": "Någon ber om bilder eller skickar sexuella saker",
    },
    "help.opt.pics.desc": {
        "en": "Nudes, sexual chat, or pictures you didn't want",
        "sv": "Nakenbilder, sexchatt eller bilder du inte ville se",
    },
    "help.opt.meet": {"en": "Someone wants to meet or knows where I live", "sv": "Någon vill träffas eller vet var jag bor"},
    "help.opt.meet.desc": {
        "en": "Asks where you live, your school, or to meet up",
        "sv": "Frågar var du bor, vilken skola du går på eller vill ses",
    },
    "help.opt.scam": {
        "en": "Scam, hacked account, or someone wants money",
        "sv": "Bedrägeri, hackat konto eller någon vill ha pengar",
    },
    "help.opt.scam.desc": {
        "en": "Gift cards, Nitro, codes, passwords or \"free\" stuff",
        "sv": "Presentkort, Nitro, koder, lösenord eller \"gratis\" grejer",
    },
    "help.opt.bully": {"en": "Bullying, hate or threats", "sv": "Mobbning, hat eller hot"},
    "help.opt.bully.desc": {
        "en": "Mean messages, being shut out on purpose, or threats",
        "sv": "Elaka meddelanden, att bli utfryst eller hotad",
    },
    "help.opt.other": {"en": "Something else feels wrong", "sv": "Något annat känns fel"},
    "help.opt.other.desc": {"en": "You don't have to know exactly what it is", "sv": "Du behöver inte veta exakt vad det är"},
    "help.opt.settings": {"en": "Make my Discord safer", "sv": "Gör mitt Discord säkrare"},
    "help.opt.settings.desc": {
        "en": "Discord's own safety settings, step by step",
        "sv": "Discords egna säkerhetsinställningar, steg för steg",
    },
    # who can help (every situation)
    "help.contacts.title": {"en": "Who can help", "sv": "Här får du hjälp"},
    "help.contacts": {
        "en": "🚨 Danger right now: **112** (Sweden and the rest of the EU)\n"
              "💬 Bris, for under-18s: call or text **116 111**, or chat. Any time, free, anonymous.\n"
              "🛡️ Ditt ECPAT, for under-18s: **020-11 21 00** (weekdays) or chat.\n"
              "👮 Police: **114 14** to report something that already happened.\n"
              "🌍 Not in Sweden? Find a child helpline in your country with the button below. "
              "In the US: NCMEC, **1-800-843-5678**.",
        "sv": "🚨 Fara just nu: **112**\n"
              "💬 Bris, för dig under 18: ring eller sms:a **116 111**, eller chatta. Dygnet runt, gratis, anonymt.\n"
              "🛡️ Ditt ECPAT, för dig under 18: **020-11 21 00** (vardagar) eller chatt.\n"
              "👮 Polisen: **114 14** för att anmäla något som redan har hänt.\n"
              "🌍 Inte i Sverige? Hitta en stödlinje för barn i ditt land på childhelplineinternational.org.",
    },
    # situations
    "help.threat.title": {"en": "Someone is threatening to share pictures", "sv": "Någon hotar att sprida bilder på dig"},
    "help.threat.steps": {
        "en": "**This is not your fault.** The person threatening you is the one committing a crime. "
              "You're not in trouble, and this can be fixed.\n\n"
              "1. **Don't pay, and don't send anything more.** Paying almost never makes it stop. They usually just ask for more.\n"
              "2. **Stop replying, but don't delete the chat** or your account. The chat is evidence.\n"
              "3. **Save evidence.** Screenshot the chat and their profile, and write down their @username and user ID.\n"
              "4. **Report, then block.** Right-click or long-press their message → **Report Message**. Then block them.\n"
              "5. **Tell an adult you trust, today.** A parent, someone else in your family, a teacher or the school "
              "counsellor. If that feels too hard, start by calling Bris on **116 111**.\n"
              "6. **Report it to the police** on **114 14**. They can act even if the person lives in another country.\n"
              "7. **Get the pictures taken down.** Take It Down works for pictures taken before you turned 18, on apps "
              "and sites that take part. Your picture never leaves your phone. Ditt ECPAT can also help get pictures removed.\n\n"
              "If it all feels like too much, or you're thinking about hurting yourself, call **112** or "
              "Självmordslinjen on **90101** right now. You matter more than any picture.",
        "sv": "**Det här är inte ditt fel.** Den som hotar dig är den som begår ett brott. "
              "Du kommer inte att få skäll, och det går att lösa.\n\n"
              "1. **Betala inte, och skicka inget mer.** Att betala får nästan aldrig det att sluta. Oftast vill de bara ha mer.\n"
              "2. **Sluta svara, men radera inte chatten** eller ditt konto. Chatten är bevis.\n"
              "3. **Spara bevis.** Ta skärmdumpar på chatten och profilen, och skriv upp personens @användarnamn och användar-ID.\n"
              "4. **Rapportera och blockera sedan.** Högerklicka eller håll inne på meddelandet → **Rapportera meddelande**. "
              "Blockera sedan personen.\n"
              "5. **Berätta för en vuxen du litar på, i dag.** En förälder, någon annan i familjen, en lärare eller "
              "skolkuratorn. Om det känns för svårt kan du börja med att ringa Bris på **116 111**.\n"
              "6. **Anmäl till polisen** på **114 14**. De kan göra något även om personen bor i ett annat land.\n"
              "7. **Få bort bilderna.** Take It Down fungerar för bilder som togs innan du fyllde 18, på appar och sajter "
              "som är med. Bilden lämnar aldrig din mobil. Ditt ECPAT kan också hjälpa till att få bort bilder.\n\n"
              "Om allt känns för mycket, eller om du tänker på att skada dig själv: ring **112** eller "
              "Självmordslinjen på **90101** direkt. Du är viktigare än någon bild.",
    },
    "help.pics.title": {
        "en": "Someone asks for pictures or sends sexual stuff",
        "sv": "Någon ber om bilder eller skickar sexuella saker",
    },
    "help.pics.steps": {
        "en": "**You did nothing wrong.** Asking a young person for sexual pictures, or sending them sexual stuff, "
              "is not okay, and it can be a crime.\n\n"
              "1. **You never have to send anything.** Saying no, or just not answering, is always okay. "
              "Even if they're nice, or say they're your age.\n"
              "2. **Don't forward or save sexual pictures**, not even to show friends. Show an adult on your screen instead.\n"
              "3. **Save evidence:** screenshot the chat and their profile (not the sexual picture itself), and write down "
              "their @username and user ID.\n"
              "4. **Report, then block.** Right-click or long-press the message → **Report Message**. Don't delete the chat.\n"
              "5. **Tell an adult you trust**, or talk to Bris on **116 111**.\n"
              "6. **Already sent a picture?** It's not too late, and it's still not your fault. Take It Down can help get it "
              "removed. If they start threatening you, pick \"Someone threatens to share my pictures\" in the menu.\n"
              "7. **Saw sexual pictures of a child?** Report it anonymously to the ECPAT Hotline, or to the police on **114 14**.",
        "sv": "**Du har inte gjort något fel.** Det är inte okej att be en ung person om sexuella bilder eller skicka "
              "sexuella saker till dem, och det kan vara ett brott.\n\n"
              "1. **Du behöver aldrig skicka något.** Det är alltid okej att säga nej eller att bara inte svara. "
              "Även om personen är snäll eller säger att hen är lika gammal som du.\n"
              "2. **Skicka inte vidare och spara inte sexuella bilder**, inte ens för att visa kompisar. Visa en vuxen "
              "på din skärm i stället.\n"
              "3. **Spara bevis:** ta skärmdumpar på chatten och profilen (men inte på själva den sexuella bilden), och "
              "skriv upp @användarnamn och användar-ID.\n"
              "4. **Rapportera och blockera sedan.** Högerklicka eller håll inne på meddelandet → **Rapportera meddelande**. "
              "Radera inte chatten.\n"
              "5. **Berätta för en vuxen du litar på**, eller prata med Bris på **116 111**.\n"
              "6. **Har du redan skickat en bild?** Det är inte för sent, och det är fortfarande inte ditt fel. "
              "Take It Down kan hjälpa till att få bort den. Om personen börjar hota dig, välj "
              "\"Någon hotar att sprida bilder på mig\" i menyn.\n"
              "7. **Har du sett sexuella bilder på ett barn?** Tipsa anonymt till ECPAT Hotline, eller till polisen på **114 14**.",
    },
    "help.meet.title": {"en": "Someone wants to meet or knows where you live", "sv": "Någon vill träffas eller vet var du bor"},
    "help.meet.steps": {
        "en": "**You were right to stop and ask.** People who want to meet a young person they only know online "
              "are often not who they say they are.\n\n"
              "1. **Don't go to meet them**, and don't say where you live, which school you go to, or where you hang out.\n"
              "2. **In danger right now**, or is someone outside? Call **112**.\n"
              "3. **Tell an adult at home today**, especially if they know your address or school, or say they'll come.\n"
              "4. **Stop replying, but keep the chat.** Screenshot it, write down their @username and user ID, then "
              "**report and block** them.\n"
              "5. **Report it to the police** on **114 14**, together with an adult if you can.\n"
              "6. **Hide clues about where you are.** Check your profile, pictures and connected accounts for your school, "
              "town or face. User Settings → **Data & Privacy** → **Profile Privacy**.",
        "sv": "**Det var rätt av dig att stanna upp och fråga.** Personer som vill träffa en ung person som de bara "
              "känner från nätet är ofta inte de som de säger att de är.\n\n"
              "1. **Gå inte och träffa personen**, och berätta inte var du bor, vilken skola du går på eller var du brukar vara.\n"
              "2. **Är du i fara just nu**, eller står någon utanför? Ring **112**.\n"
              "3. **Berätta för en vuxen hemma i dag**, särskilt om personen vet din adress eller skola, eller säger att "
              "hen ska komma.\n"
              "4. **Sluta svara, men spara chatten.** Ta skärmdumpar, skriv upp @användarnamn och användar-ID, och "
              "**rapportera och blockera** sedan personen.\n"
              "5. **Anmäl till polisen** på **114 14**, gärna tillsammans med en vuxen.\n"
              "6. **Göm ledtrådar om var du är.** Kolla din profil, dina bilder och kopplade konton efter skola, ort eller "
              "ansikte. Användarinställningar → **Data och integritet** → **Profilsekretess**.",
    },
    "help.scam.title": {
        "en": "Scam, hacked account, or someone wants money",
        "sv": "Bedrägeri, hackat konto eller någon vill ha pengar",
    },
    "help.scam.steps": {
        "en": "**Scammers are good at tricking people, adults too.** Getting fooled doesn't make you stupid.\n\n"
              "1. **Don't pay or send anything:** no money, gift card codes, Nitro, skins or items.\n"
              "2. **Never share your password or login codes**, and never scan a login QR code someone sends you. "
              "Discord staff never DM you to ask for these.\n"
              "3. **A friend acting weird or sending links?** Their account may be hacked. Ask them another way, "
              "like a text or a call.\n"
              "4. **Think you've been hacked?** Change your password, turn on two-factor login (MFA), and remove apps you "
              "don't recognise in User Settings (look for **Authorized Apps**). If your email was changed, the "
              "\"Discord Email Address changed\" email has a link to undo it.\n"
              "5. **Already paid or gave something away?** Tell an adult now. They can contact the bank or app store, "
              "and report it to the police on **114 14**.\n"
              "6. **Report the message** (right-click or long-press → **Report Message**), then block them.",
        "sv": "**Bedragare är bra på att lura folk, vuxna också.** Det betyder inte att du är dum om du blir lurad.\n\n"
              "1. **Betala inte och skicka inget:** inga pengar, presentkortskoder, Nitro, skins eller föremål.\n"
              "2. **Dela aldrig ditt lösenord eller dina inloggningskoder**, och skanna aldrig en QR-kod för inloggning "
              "som någon skickar. Discords personal skickar aldrig DM och ber om sånt.\n"
              "3. **Beter sig en kompis konstigt eller skickar länkar?** Kontot kan vara hackat. Fråga kompisen på något "
              "annat sätt, till exempel med sms eller ett samtal.\n"
              "4. **Tror du att du har blivit hackad?** Byt lösenord, slå på tvåstegsverifiering (MFA) och ta bort appar "
              "du inte känner igen i Användarinställningar (leta efter **Auktoriserade appar**). Om din mejladress har "
              "ändrats finns det en länk för att ångra i mejlet som Discord skickade om ändringen.\n"
              "5. **Har du redan betalat eller gett bort något?** Berätta för en vuxen nu. De kan kontakta banken eller "
              "appbutiken och anmäla till polisen på **114 14**.\n"
              "6. **Rapportera meddelandet** (högerklicka eller håll inne → **Rapportera meddelande**) och blockera sedan personen.",
    },
    "help.bully.title": {"en": "Bullying, hate or threats", "sv": "Mobbning, hat eller hot"},
    "help.bully.steps": {
        "en": "**Nobody deserves this, and it's not your fault.** You don't have to deal with it alone.\n\n"
              "1. **Don't answer back** while you're upset. That's often what they want.\n"
              "2. **Save evidence first:** screenshots that show names, dates and what was said.\n"
              "3. **Block or ignore them.** Block stops them contacting you. Ignore hides their messages, and they won't "
              "know. Right-click their name (phone: tap it → ⋯).\n"
              "4. **Report it** to Discord (right-click or long-press → **Report Message**) and to the server's moderators.\n"
              "5. **Tell an adult you trust.** If it's people from school, tell a teacher or the school counsellor too.\n"
              "6. **Threats to hurt you, hate about who you are, or someone spreading your private stuff** can be crimes. "
              "Report it to the police on **114 14**, or call **112** if you're in danger right now.",
        "sv": "**Ingen förtjänar det här, och det är inte ditt fel.** Du behöver inte klara det själv.\n\n"
              "1. **Svara inte tillbaka** när du är upprörd. Det är ofta det de vill.\n"
              "2. **Spara bevis först:** skärmdumpar där namn, datum och det som skrevs syns.\n"
              "3. **Blockera eller ignorera.** Blockera stoppar dem från att kontakta dig. Ignorera döljer deras meddelanden "
              "utan att de märker det. Högerklicka på namnet (mobil: tryck på det → ⋯).\n"
              "4. **Rapportera** till Discord (högerklicka eller håll inne → **Rapportera meddelande**) och till serverns moderatorer.\n"
              "5. **Berätta för en vuxen du litar på.** Om det är folk från skolan, berätta för en lärare eller skolkuratorn också.\n"
              "6. **Hot om att skada dig, hat mot den du är eller att någon sprider dina privata saker** kan vara brott. "
              "Anmäl till polisen på **114 14**, eller ring **112** om du är i fara just nu.",
    },
    "help.other.title": {"en": "Something feels wrong", "sv": "Något känns fel"},
    "help.other.steps": {
        "en": "**Trust that feeling.** You don't need to know exactly what's wrong to ask for help.\n\n"
              "1. **It's okay to stop replying**, leave a server or block someone. You don't owe anyone an explanation.\n"
              "2. **Talk to someone:** an adult you trust, or Bris on **116 111** (call, text or chat). "
              "Any time, free and anonymous.\n"
              "3. **Save evidence** if it's about a person: screenshots, their @username and user ID.\n"
              "4. **Don't share** your address, school, passwords or pictures with anyone who makes you feel unsure.\n"
              "5. **In danger right now?** Call **112**.",
        "sv": "**Lita på den känslan.** Du behöver inte veta exakt vad som är fel för att be om hjälp.\n\n"
              "1. **Det är okej att sluta svara**, lämna en server eller blockera någon. Du behöver inte förklara dig.\n"
              "2. **Prata med någon:** en vuxen du litar på, eller Bris på **116 111** (ring, sms:a eller chatta). "
              "Dygnet runt, gratis och anonymt.\n"
              "3. **Spara bevis** om det gäller en person: skärmdumpar, @användarnamn och användar-ID.\n"
              "4. **Dela inte** adress, skola, lösenord eller bilder med någon som får dig att känna dig osäker.\n"
              "5. **Är du i fara just nu?** Ring **112**.",
    },
    # settings walkthrough
    "help.settings.title": {"en": "Make your Discord safer", "sv": "Gör ditt Discord säkrare"},
    "help.settings.intro": {
        "en": "Discord has its own safety settings, and if Discord knows you're a teen, many are already on. "
              "Here's how to check them. Menu names can differ a little between app versions.",
        "sv": "Discord har egna säkerhetsinställningar, och om Discord vet att du är tonåring är många redan på. "
              "Så här kollar du dem. Menynamnen kan skilja sig lite mellan olika versioner av appen.",
    },
    "help.settings.dms": {"en": "Who can message you", "sv": "Vem som kan skriva till dig"},
    "help.settings.dms.body": {
        "en": "• **DMs from server members:** User Settings → **Messaging Permissions** (older apps: Content & Social) → "
              "turn off direct messages from server members. For one server only: tap the server name → **Privacy Settings**.\n"
              "• **Message requests:** messages from people you're not friends with land in a separate **Message Requests** "
              "inbox. For teens this is always on. Only accept people you know in real life.\n"
              "• **Spam filter:** keep the DM spam filter on filtering everything.",
        "sv": "• **DM från servermedlemmar:** Användarinställningar → **Meddelandebehörigheter** (äldre appar: Innehåll och "
              "socialt) → stäng av direktmeddelanden från servermedlemmar. För en enda server: tryck på servernamnet → "
              "**Sekretessinställningar**.\n"
              "• **Meddelandeförfrågningar:** meddelanden från folk du inte är vän med hamnar i en egen inkorg, "
              "**Meddelandeförfrågningar**. För tonåringar är det alltid på. Acceptera bara folk du känner i verkligheten.\n"
              "• **Spamfilter:** låt spamfiltret för DM filtrera allt.",
    },
    "help.settings.friends": {"en": "Who can add you as a friend", "sv": "Vem som kan lägga till dig som vän"},
    "help.settings.friends.body": {
        "en": "• User Settings → **Messaging Permissions** → **Friend Requests**: untick **Everyone**, so only friends of "
              "friends (or nobody) can add you.\n"
              "• Discord warns you before you accept a request from someone you share no friends or small servers with. "
              "Take that warning seriously.",
        "sv": "• Användarinställningar → **Meddelandebehörigheter** → **Vänförfrågningar**: bocka ur **Alla**, så att bara "
              "vänners vänner (eller ingen) kan lägga till dig.\n"
              "• Discord varnar dig innan du accepterar en förfrågan från någon som du inte har några gemensamma vänner "
              "eller små servrar med. Ta varningen på allvar.",
    },
    "help.settings.content": {"en": "Pictures, alerts and your profile", "sv": "Bilder, varningar och din profil"},
    "help.settings.content.body": {
        "en": "• **Sensitive content filters:** for teens, sexual or violent pictures are blurred, and from strangers "
              "they're blocked. Teens can't turn this off, and that's on purpose.\n"
              "• **Safety alerts:** when someone new DMs you, Discord may show a safety alert. You can block them right from it.\n"
              "• **Profile privacy:** User Settings → **Data & Privacy** → **Profile Privacy** → "
              "**Friends & Small Servers Only**.",
        "sv": "• **Filter för känsligt innehåll:** för tonåringar suddas sexuella eller våldsamma bilder ut, och från "
              "främlingar blockeras de helt. Tonåringar kan inte stänga av det, och det är meningen.\n"
              "• **Säkerhetsvarningar:** när någon ny skickar DM till dig kan Discord visa en säkerhetsvarning. "
              "Du kan blockera personen direkt därifrån.\n"
              "• **Profilsekretess:** Användarinställningar → **Data och integritet** → **Profilsekretess** → "
              "bara vänner och små servrar.",
    },
    "help.settings.bothers": {"en": "If someone bothers you", "sv": "Om någon stör dig"},
    "help.settings.bothers.body": {
        "en": "• **Report:** right-click or long-press the message → **Report Message**. Report first, then block.\n"
              "• **Block:** right-click their name (phone: tap it → ⋯) → **Block**.\n"
              "• **Ignore:** same menu → **Ignore**. It hides their messages, and they won't know.",
        "sv": "• **Rapportera:** högerklicka eller håll inne på meddelandet → **Rapportera meddelande**. "
              "Rapportera först, blockera sedan.\n"
              "• **Blockera:** högerklicka på namnet (mobil: tryck på det → ⋯) → **Blockera**.\n"
              "• **Ignorera:** samma meny → **Ignorera**. Det döljer deras meddelanden utan att de märker det.",
    },
    "help.settings.parent": {"en": "A parent can help", "sv": "En förälder kan hjälpa till"},
    "help.settings.parent.body": {
        "en": "**Family Center:** User Settings → **Account** → **Family Center** → **My Family** → **Show Code** or "
              "**Copy Link**, and let a parent connect. They see who you add and talk to, but never your messages, and "
              "they can help manage your DM, friend request and filter settings.",
        "sv": "**Familjecenter:** Användarinställningar → **Konto** → **Familjecenter** → **Min familj** → **Visa kod** "
              "eller **Kopiera länk**, och låt en förälder koppla ihop sig med dig. Hen ser vem du lägger till och pratar "
              "med, men aldrig dina meddelanden, och kan hjälpa till med inställningarna för DM, vänförfrågningar och filter.",
    },
    "help.settings.age": {"en": "Check your age group", "sv": "Kolla din åldersgrupp"},
    "help.settings.age.body": {
        "en": "Teen protections only work if Discord knows you're a teen. Check under User Settings → **Account Status**.",
        "sv": "Skydden för tonåringar fungerar bara om Discord vet att du är tonåring. "
              "Kolla under Användarinställningar → **Kontostatus**.",
    },
    # evidence card
    "help.ev.title": {"en": "🧾 Evidence to save", "sv": "🧾 Bevis att spara"},
    "help.ev.intro": {
        "en": "Police and Discord can use this even if the sender deletes their account. "
              "**Screenshot this card now**: it can disappear when you close or restart Discord.",
        "sv": "Polisen och Discord kan använda det här även om avsändaren raderar sitt konto. "
              "**Ta en skärmdump av kortet nu**: det kan försvinna när du stänger eller startar om Discord.",
    },
    "help.ev.sender": {"en": "Who sent it", "sv": "Vem som skickade"},
    "help.ev.sender_value": {
        "en": "@{name}\nUser ID (copy this):\n```\n{id}\n```",
        "sv": "@{name}\nAnvändar-ID (kopiera det här):\n```\n{id}\n```",
    },
    "help.ev.created": {"en": "Account created", "sv": "Kontot skapades"},
    "help.ev.sent": {"en": "Sent", "sv": "Skickat"},
    "help.ev.link": {"en": "Message link", "sv": "Länk till meddelandet"},
    "help.ev.excerpt": {"en": "What they wrote", "sv": "Vad som skrevs"},
    "help.ev.how": {"en": "How to save it", "sv": "Så sparar du det"},
    "help.ev.how_value": {
        "en": "1. **Screenshot** the chat and their profile, so the @name shows.\n"
              "2. **Don't delete the chat**, even after you block them. If they delete messages or their account, "
              "your screenshots and their user ID are what's left.\n"
              "3. **Copy a user ID yourself:** User Settings → **Advanced** → turn on **Developer Mode**, then right-click "
              "their name (phone: tap it → ⋯) → **Copy User ID**. For a message: right-click or long-press → "
              "**Copy Message Link**.",
        "sv": "1. **Ta skärmdumpar** på chatten och profilen, så att @namnet syns.\n"
              "2. **Radera inte chatten**, inte ens efter att du blockerat. Om personen raderar meddelanden eller sitt "
              "konto är dina skärmdumpar och användar-ID:t det som finns kvar.\n"
              "3. **Kopiera ett användar-ID själv:** Användarinställningar → **Avancerat** → slå på **Utvecklarläge** "
              "(Developer Mode), högerklicka sedan på namnet (mobil: tryck på det → ⋯) → **Kopiera användar-ID**. "
              "För ett meddelande: högerklicka eller håll inne → **Kopiera meddelandelänk**.",
    },
    # URL button labels (<= 80 chars)
    "help.link.bris_chat": {"en": "Chat with Bris", "sv": "Chatta med Bris"},
    "help.link.ecpat_kids": {"en": "Ditt ECPAT (under 18)", "sv": "Ditt ECPAT (under 18)"},
    "help.link.ecpat_hotline": {"en": "Report to ECPAT Hotline", "sv": "Tipsa ECPAT Hotline"},
    "help.link.ecpat_platforms": {"en": "Ditt ECPAT platform guide (Swedish)", "sv": "Plattformsguiden (Ditt ECPAT)"},
    "help.link.police_report": {"en": "Police: how to report", "sv": "Polisen: så anmäler du"},
    "help.link.police_tip": {"en": "Tip off the police", "sv": "Tipsa polisen"},
    "help.link.mind": {"en": "Självmordslinjen (Mind)", "sv": "Självmordslinjen (Mind)"},
    "help.link.takeitdown": {"en": "Take It Down: remove pictures", "sv": "Take It Down: få bort bilder"},
    "help.link.cybertip": {"en": "NCMEC CyberTipline (US)", "sv": "NCMEC CyberTipline (USA)"},
    "help.link.helplines": {"en": "Find a helpline in your country", "sv": "Hitta en stödlinje i ditt land"},
    "help.link.discord_report": {"en": "How to report on Discord", "sv": "Så rapporterar du på Discord"},
    "help.link.discord_form": {"en": "Discord report form (EU)", "sv": "Discords anmälningsformulär (EU)"},
    "help.link.discord_safety": {"en": "Discord Safety Center", "sv": "Discords säkerhetscenter"},
    "help.link.discord_family": {"en": "Discord Family Center", "sv": "Discord Familjecenter"},
    "help.link.discord_teen": {"en": "Discord: teen protections", "sv": "Discord: skydd för tonåringar"},
    "help.link.discord_privacy": {"en": "Discord: blocking and privacy", "sv": "Discord: blockering och sekretess"},
    "help.link.discord_hacked": {"en": "Discord: hacked account help", "sv": "Discord: hjälp vid hackat konto"},
})
