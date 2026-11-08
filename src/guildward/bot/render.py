"""Verdict -> Discord embed. Written for a kid: plain words, what it means, what to do next."""

from __future__ import annotations

import discord

from guildward.core.i18n import Lang, register, t
from guildward.core.models import Kind, Level, Verdict

COLORS = {Level.GREEN: 0x2EA043, Level.YELLOW: 0xD29922, Level.RED: 0xDA3633}
DOTS = {Level.GREEN: "🟢", Level.YELLOW: "🟡", Level.RED: "🔴"}
MAX_REASONS = 6

REPORT_URL = "https://support.discord.com/hc/en-us/articles/360000291932"
BRIS_URL = "https://www.bris.se"


def verdict_embed(v: Verdict, lang: Lang, *, subject: str) -> discord.Embed:
    level = v.level.value
    embed = discord.Embed(
        title=f"{DOTS[v.level]} {t(f'title.{v.kind}.{level}', lang)}",
        description=discord.utils.escape_markdown(subject)[:300],
        color=COLORS[v.level],
    )

    lines = [f"⚠️ {t(s.code, lang, **s.params)}" for s in v.risks[:MAX_REASONS]]
    lines += [f"ℹ️ {t(s.code, lang, **s.params)}" for s in v.signals if s.weight == 0]
    lines += [f"✅ {t(s.code, lang, **s.params)}" for s in v.reassurances[: max(0, MAX_REASONS - len(lines))]]
    embed.add_field(name=t("ui.why", lang), value="\n".join(lines) or t("ui.no_signals", lang),
                    inline=False)

    embed.add_field(name=t("ui.todo", lang), value=t(f"todo.{v.kind}.{level}", lang), inline=False)
    embed.add_field(
        name=t("ui.how_sure", lang),
        value=t("ui.score", lang, score=v.score) + "\n" + t(f"confidence.{v.confidence.name.lower()}", lang),
        inline=False,
    )
    embed.set_footer(text=t("ui.footer", lang))
    return embed


def help_buttons(v: Verdict, lang: Lang) -> discord.ui.View | None:
    if v.level is Level.GREEN:
        return None
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label=t("ui.btn_report", lang), url=REPORT_URL))
    if v.level is Level.RED:
        view.add_item(discord.ui.Button(label=t("ui.btn_bris", lang), url=BRIS_URL))
    return view


def notice_embed(key: str, lang: Lang, **params: object) -> discord.Embed:
    return discord.Embed(description=t(key, lang, **params), color=0x57606A).set_footer(
        text=t("ui.footer", lang)
    )


register({
    # titles: title.<kind>.<level>
    f"title.{Kind.SERVER}.green": {"en": "No warning signs found", "sv": "Inga varningstecken hittades"},
    f"title.{Kind.SERVER}.yellow": {"en": "Be careful with this server", "sv": "Var försiktig med den här servern"},
    f"title.{Kind.SERVER}.red": {"en": "High risk: better not join", "sv": "Hög risk: gå hellre inte med"},
    f"title.{Kind.PERSON}.green": {"en": "No warning signs found", "sv": "Inga varningstecken hittades"},
    f"title.{Kind.PERSON}.yellow": {"en": "Be careful with this person", "sv": "Var försiktig med den här personen"},
    f"title.{Kind.PERSON}.red": {"en": "High risk: don't trust this account", "sv": "Hög risk: lita inte på det här kontot"},
    f"title.{Kind.MESSAGE}.green": {"en": "Nothing alarming in this message", "sv": "Inget oroande i meddelandet"},
    f"title.{Kind.MESSAGE}.yellow": {"en": "This message has warning signs", "sv": "Meddelandet har varningstecken"},
    f"title.{Kind.MESSAGE}.red": {"en": "This message is a serious warning sign", "sv": "Meddelandet är ett allvarligt varningstecken"},
    # what to do: todo.<kind>.<level>
    f"todo.{Kind.SERVER}.green": {
        "en": "Looks fine from the outside. Still: never share your age, school or other apps with strangers there.",
        "sv": "Ser bra ut utifrån. Men dela ändå aldrig din ålder, skola eller andra appar med främlingar där.",
    },
    f"todo.{Kind.SERVER}.yellow": {
        "en": "If you join, keep DMs from server members off and leave if anyone asks personal questions.",
        "sv": "Om du går med: stäng av DM från servermedlemmar och lämna om någon ställer personliga frågor.",
    },
    f"todo.{Kind.SERVER}.red": {
        "en": "Don't join. If someone sent you this invite, show it to an adult you trust.",
        "sv": "Gå inte med. Om någon skickade inbjudan till dig, visa den för en vuxen du litar på.",
    },
    f"todo.{Kind.PERSON}.green": {
        "en": "Nothing stands out, but you can't see who's behind any account. Keep personal stuff private.",
        "sv": "Inget sticker ut, men man kan aldrig se vem som finns bakom ett konto. Håll privata saker för dig själv.",
    },
    f"todo.{Kind.PERSON}.yellow": {
        "en": "Don't accept a friend request just because they're in the same server. Never move to another app with them.",
        "sv": "Acceptera inte en vänförfrågan bara för att ni är i samma server. Byt aldrig till en annan app med dem.",
    },
    f"todo.{Kind.PERSON}.red": {
        "en": "Block them (right-click → Block). If they've said anything strange to you, tell an adult you trust.",
        "sv": "Blockera dem (högerklicka → Blockera). Om de har sagt något konstigt till dig, berätta för en vuxen du litar på.",
    },
    f"todo.{Kind.MESSAGE}.green": {
        "en": "Nothing alarming found. If it still feels wrong, trust that feeling and ask someone.",
        "sv": "Inget oroande hittades. Om det ändå känns fel, lita på den känslan och fråga någon.",
    },
    f"todo.{Kind.MESSAGE}.yellow": {
        "en": "Don't answer personal questions or move to another app. Show the chat to an adult you trust.",
        "sv": "Svara inte på personliga frågor och byt inte app. Visa chatten för en vuxen du litar på.",
    },
    f"todo.{Kind.MESSAGE}.red": {
        "en": "Stop replying. Don't send anything, don't delete the chat, and tell an adult you trust now. "
              "You won't get in trouble. Report the message (right-click → Report) and block them. "
              "Bris: call 116 111 (free and anonymous).",
        "sv": "Sluta svara. Skicka ingenting, radera inte chatten, och berätta för en vuxen du litar på nu. "
              "Du kommer inte att få skäll. Anmäl meddelandet (högerklicka → Rapportera) och blockera personen. "
              "Bris: ring 116 111 (gratis och anonymt).",
    },
    # confidence
    "confidence.low": {
        "en": "Based only on what anyone can see from the outside. A hint, not proof.",
        "sv": "Bygger bara på det alla kan se utifrån. En ledtråd, inte ett bevis.",
    },
    "confidence.medium": {
        "en": "Based on the outside view plus reports from the Guildward network.",
        "sv": "Bygger på det som syns utifrån plus rapporter från Guildward-nätverket.",
    },
    "confidence.high": {
        "en": "Based on a safety audit the server's admins allowed.",
        "sv": "Bygger på en säkerhetsgranskning som serverns admins godkänt.",
    },
    "confidence.highest": {
        "en": "Based on a full safety audit, including moderation and chat patterns.",
        "sv": "Bygger på en fullständig säkerhetsgranskning, även moderering och chattmönster.",
    },
    # chrome
    "ui.why": {"en": "Why", "sv": "Varför"},
    "ui.todo": {"en": "What to do", "sv": "Vad du kan göra"},
    "ui.how_sure": {"en": "How sure", "sv": "Hur säkert"},
    "ui.score": {"en": "Risk **{score}/100**", "sv": "Risk **{score}/100**"},
    "ui.no_signals": {"en": "No signals either way.", "sv": "Inga signaler åt något håll."},
    "ui.footer": {
        "en": "Guildward · Only you can see this · Message text is never saved",
        "sv": "Guildward · Bara du ser detta · Meddelandetext sparas aldrig",
    },
    "ui.btn_report": {"en": "How to report", "sv": "Så anmäler du"},
    "ui.btn_bris": {"en": "Talk to Bris", "sv": "Prata med Bris"},
    # subjects
    "subject.server": {"en": "**{name}** · {members} members", "sv": "**{name}** · {members} medlemmar"},
    "subject.group_dm": {"en": "Group chat invite", "sv": "Inbjudan till gruppchatt"},
    "subject.friend": {"en": "Friend invite from {name}", "sv": "Vänlänk från {name}"},
    "subject.person": {"en": "{name}", "sv": "{name}"},
    "subject.message": {"en": "Message from {name}", "sv": "Meddelande från {name}"},
    # notices
    "notice.bad_invite": {
        "en": "That doesn't look like a Discord invite. Paste a link like `discord.gg/abc123`.",
        "sv": "Det där ser inte ut som en Discord-inbjudan. Klistra in en länk som `discord.gg/abc123`.",
    },
    "notice.invite_gone": {
        "en": "That invite is invalid or has expired, so there's nothing to check.",
        "sv": "Inbjudan är ogiltig eller har gått ut, så det finns inget att kolla.",
    },
    "notice.no_text": {
        "en": "This message has no text. Guildward only reads text, never images or files.",
        "sv": "Meddelandet har ingen text. Guildward läser bara text, aldrig bilder eller filer.",
    },
    "notice.cooldown": {
        "en": "Slow down a little: try again in {seconds} seconds.",
        "sv": "Ta det lite lugnt: försök igen om {seconds} sekunder.",
    },
    "notice.error": {
        "en": "Something went wrong on our side. Please try again in a moment.",
        "sv": "Något gick fel hos oss. Försök igen om en stund.",
    },
})

