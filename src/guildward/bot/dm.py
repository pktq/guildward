"""Messages a kid sends or forwards to Guildward's own DM: checked automatically.

Forwarding a DM is one long-press on a phone, so this is the lowest-effort check we can offer. A forward
carries the text but not who sent it, so memory is keyed by the conversation it came from instead.
Several forwards in a row are checked together as one conversation.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import TYPE_CHECKING

import discord

from guildward.bot import flows, helplines, render
from guildward.bot import help as kidhelp
from guildward.bot.adapters import parse_invite_code
from guildward.core.i18n import Lang, register, t
from guildward.intel import links

if TYPE_CHECKING:
    from guildward.bot.app import GuildwardBot

log = logging.getLogger(__name__)
BATCH_SECONDS = 4.0
MAX_BATCH = 10
RATE_MAX, RATE_WINDOW = 30, 600  # messages per 10 minutes per kid
_rate: dict[int, deque[float]] = {}
_tasks: set[asyncio.Task] = set()
_HELP_WORDS = {"help", "hjälp", "hjalp", "sos", "/help"}
_pending: dict[int, tuple[list[tuple[str, int | None]], asyncio.TimerHandle | None]] = {}


def _texts(message: discord.Message) -> list[tuple[str, int | None]]:
    """(text, origin channel) for each forwarded snapshot, else the message itself."""
    origin = message.reference.channel_id if message.reference else None
    snaps = [s.content for s in getattr(message, "message_snapshots", []) or [] if s.content]
    out = [(x, origin) for x in snaps]
    if message.content.strip():
        out.append((message.content, None))
    return out


async def on_dm(bot: GuildwardBot, message: discord.Message) -> None:
    kid = message.author.id
    row = bot.pocket.user(kid)
    lang: Lang = row["lang"] if row and row["lang"] in ("en", "sv") else "en"
    bot.pocket.touch_user(kid, lang)
    bot.pocket.set_dm(kid, "ok")
    hits = _rate.setdefault(kid, deque(maxlen=RATE_MAX))
    if len(hits) == RATE_MAX and message.created_at.timestamp() - hits[0] < RATE_WINDOW:
        return  # flood: drop silently rather than amplify into link lookups
    hits.append(message.created_at.timestamp())
    items = _texts(message)
    if not items:
        await message.channel.send(embed=render.notice_embed("dm.empty", lang))
        return
    if len(items) == 1 and items[0][0].strip().casefold() in _HELP_WORDS:
        embed, view = kidhelp.help_menu(lang, helplines.region_for(bot, kid, lang))
        await message.channel.send(embed=embed, view=view)
        return
    batch, handle = _pending.get(kid, ([], None))
    if handle is not None:
        handle.cancel()
    batch.extend(items)
    loop = asyncio.get_running_loop()
    def fire() -> None:
        task = loop.create_task(_flush(bot, kid, lang, message.channel))
        _tasks.add(task)  # keep a reference so the task isn't garbage-collected mid-check
        task.add_done_callback(_tasks.discard)

    _pending[kid] = (batch, loop.call_later(BATCH_SECONDS, fire))


async def _flush(bot: GuildwardBot, kid: int, lang: Lang, channel: discord.abc.Messageable) -> None:
    batch, _ = _pending.pop(kid, ([], None))
    batch = batch[-MAX_BATCH:]
    if not batch:
        return
    try:
        await _check(bot, kid, lang, channel, batch)
    except Exception:
        log.exception("dm check failed")
        await channel.send(embed=render.notice_embed("notice.error", lang))


async def _check(bot: GuildwardBot, kid: int, lang: Lang, channel: discord.abc.Messageable,
                 batch: list[tuple[str, int | None]]) -> None:
    from guildward.bot import commands

    texts = [x for x, _ in batch]
    if len(texts) == 1 and not any(o for _, o in batch):
        only = texts[0].strip()
        if (code := parse_invite_code(only)) and " " not in only:
            res = await commands.invite_result(bot, kid, lang, code)
            if res is None:
                await channel.send(embed=render.notice_embed("notice.invite_gone", lang))
            else:
                await channel.send(embed=res[0], view=res[1])
            return
        urls = links.extract_urls(only, limit=1)
        if urls and urls[0].strip() == only:
            embed, view = await commands.link_result(bot, kid, lang, urls[0])
            await channel.send(embed=embed, view=view)
            return
    origin = next((o for _, o in batch if o), None)
    subject = t("dm.subject_one" if len(texts) == 1 else "dm.subject_many", lang, n=len(texts))
    event = flows.hash_texts(texts)

    async def run(busy: flows.BusyNote | None = None) -> tuple[discord.Embed, discord.ui.View]:
        v = await flows.check_message(bot, kid, lang, texts, author=None,
                                      memory_key=f"c:{origin}" if origin else None, event=event, on_wait=busy)
        commands._count(bot, v)
        embed = render.verdict_embed(v, lang, subject=subject)
        embed.add_field(name=t("dm.tip_title", lang), value=t("dm.tip", lang), inline=False)
        return embed, flows.result_view(bot, kid=kid, lang=lang, v=v, texts=texts, recheck=run)

    note: list[discord.Message] = []

    async def show(e: discord.Embed) -> None:  # first "busy" note is sent, later ones edit it
        if note:
            await note[0].edit(embed=e)
        else:
            note.append(await channel.send(embed=e))

    embed, view = await run(flows.BusyNote(lang, show))
    if note:
        await note[0].edit(embed=embed, view=view)
    else:
        await channel.send(embed=embed, view=view)


register({
    "dm.empty": {
        "en": "Forward me a message (long-press it → Forward → Guildward) or paste a link or invite, and I'll "
              "check it. Type **help** if something happened.",
        "sv": "Vidarebefordra ett meddelande till mig (håll inne → Vidarebefordra → Guildward) eller klistra in en "
              "länk eller inbjudan, så kollar jag. Skriv **hjälp** om något har hänt.",
    },
    "dm.subject_one": {"en": "The message you forwarded", "sv": "Meddelandet du vidarebefordrade"},
    "dm.subject_many": {"en": "The {n} messages you forwarded, read together", "sv": "De {n} meddelandena du skickade, lästa tillsammans"},
    "dm.tip_title": {"en": "Want a better check?", "sv": "Vill du ha en bättre koll?"},
    "dm.tip": {
        "en": "A forward doesn't tell me who sent it. Use **Apps → Is this sketchy?** on the message instead, and "
              "I can also check the account and warn other kids.",
        "sv": "En vidarebefordran visar inte vem som skrev. Använd **Appar → Är det här skumt?** på meddelandet "
              "istället, så kan jag också kolla kontot och varna andra.",
    },
})
