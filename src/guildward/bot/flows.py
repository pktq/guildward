"""The check logic shared by commands, context menus and forwarded DMs, plus the buttons under a result.

Checks combine the outside view (intel/*) with what every Guildward user has seen (pocket.Pocket):
shared flags on the account, handles/scripts linked to flagged accounts, and this kid's own memory
of the same sender. All of it degrades gracefully when the pocket store isn't configured.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import discord

from guildward.bot import help as kidhelp
from guildward.bot import helplines, render
from guildward.bot.adapters import display_name
from guildward.core.i18n import Lang, register, t
from guildward.core.models import Confidence, Kind, Level, Signal, Verdict, build_verdict
from guildward.core.snowflake import created_at
from guildward.intel import ai, crowd, links, semantic
from guildward.intel.behavior import STAGE_OF, STAGE_ORDER, Stage
from guildward.intel.message import MESSAGE_BASE, analyze_message
from guildward.intel.person import account_age_signals

if TYPE_CHECKING:
    from guildward.bot.app import GuildwardBot

log = logging.getLogger(__name__)
_LATE = {Stage.ISOLATION, Stage.SEXUAL, Stage.MEETING, Stage.COERCION}
GRADE_WEIGHT = {"A": -15, "B": -8, "C": 0, "D": 10, "F": 20}
VIEW_TIMEOUT = 900


def with_signals(v: Verdict, extra: list[Signal], *, base: int, confidence: Confidence | None = None) -> Verdict:
    if not extra:
        return v
    conf = max(v.confidence, confidence or v.confidence)
    return build_verdict(v.kind, [*v.signals, *extra], base=base, confidence=conf)


def crowd_extra(bot: GuildwardBot, uid: int, lang: Lang) -> list[Signal]:
    return bot.pocket.account_signals(uid) if bot.pocket else []


def known_marks(bot: GuildwardBot, text: str) -> list[Signal]:
    if not bot.pocket:
        return []
    seen, out = set(), []
    for kind, _uid, level in bot.pocket.match_text(text):
        if kind in seen:
            continue
        seen.add(kind)
        out.append(Signal("pocket.handle_known", 35 if level == "confirmed" else 25,
                          {"kind": t(f"pocket.kind.{kind}", "en")}, severe=level == "confirmed"))
    return out


def _localise(sigs: list[Signal], lang: Lang) -> list[Signal]:
    return [dataclasses.replace(s, params={**s.params, "kind": t(f"pocket.kind.{s.params['kind']}", lang)})
            if s.code == "pocket.handle_known" and s.params.get("kind") in _KIND_KEYS else s for s in sigs]


_KIND_KEYS = {"handle", "payment", "script", "avatar", "name"}


async def link_extra(bot: GuildwardBot, text: str) -> list[Signal]:
    if not bot.web or "." not in text:
        return []
    try:
        results = await links.check_links(text, session=bot.web, safe_browsing_key=bot.settings.safe_browsing_key
                                          or None)
    except Exception:  # a link lookup must never break the message check
        log.warning("link check failed", exc_info=True)
        return []
    out: list[Signal] = []
    for r in results:
        if r.verdict.level is not Level.GREEN:
            out += list(r.verdict.risks[:2])
    return out


def conversation_signal(codes_per_msg: list[set[str]], lang: Lang) -> Signal | None:
    """Grooming steps spread over several messages: what a single-message check can't see."""
    first: dict[Stage, int] = {}
    for i, codes in enumerate(codes_per_msg):
        for c in codes:
            if (st := STAGE_OF.get(c)) is not None:
                first.setdefault(st, i)
    if len(first) < 2:
        return None
    stages = sorted(first, key=STAGE_ORDER.index)
    names = ", ".join(t(f"stage.{s.value}", lang) for s in stages)
    k = len(stages)
    return Signal("pocket.convo", min(40, 10 * k), {"stages": names}, severe=k >= 3 and bool(set(stages) & _LATE))


# --- the three checks -------------------------------------------------------------------------
async def check_message(bot: GuildwardBot, kid: int, lang: Lang, texts: list[str], *, author: discord.abc.User | None,
                        memory_key: str | int | None, event: str | int | None = None,
                        on_wait: Callable[[int], Awaitable[None]] | None = None) -> Verdict:
    """One message (context menu) or several (forwarded). `author` known only for the context menu.

    event identifies what was checked (message id, or a hash of forwarded texts) so memory counts it once.
    on_wait(place) runs if the local model is busy for a few seconds (see semantic.kid_check).
    """
    model = await semantic.kid_check(texts, on_wait=on_wait)
    per_msg = [list(analyze_message(x, m)) for x, m in zip(texts, model.signals, strict=True)]
    merged: dict[str, Signal] = {}
    for sigs in per_msg:
        for s in sigs:
            if s.code not in merged or s.weight > merged[s.code].weight:
                merged[s.code] = s
    content: list[Signal] = []  # what the text itself shows; the only part that feeds shared flags
    joined = "\n".join(texts)
    if (cs := conversation_signal([{s.code for s in sigs} for sigs in per_msg], lang)) is not None:
        content.append(cs)
    content += await link_extra(bot, joined)
    extra: list[Signal] = _localise(known_marks(bot, joined), lang)
    if model.unfinished:
        extra.append(Signal("ai.unfinished", 0))  # shown as a note; the view adds "Check again"
    own = author is not None and author.id == kid
    if author is not None and not own:
        extra += [dataclasses.replace(s, weight=s.weight // 2) for s in account_age_signals(author.id) if s.weight > 0]
        if author.public_flags.spammer:
            extra.append(Signal("person.discord_spammer", 30))
        extra += crowd_extra(bot, author.id, lang)
    risky = [c for c in merged if c.startswith("msg.")]
    if bot.pocket and memory_key is not None and not own:
        bot.pocket.remember(kid, memory_key, risky, event if event is not None else hash_texts(texts))
        if risky and (ps := bot.pocket.pattern_signal(kid, memory_key, lang)) is not None:
            extra.append(ps)
    conf = Confidence.MEDIUM if bot.pocket else Confidence.LOW
    v = build_verdict(Kind.MESSAGE, [*merged.values(), *content, *extra], base=MESSAGE_BASE, confidence=conf)
    if bot.pocket and author is not None and not own:
        # Record the content-only level: crowd flags must not feed their own corroboration.
        own_v = build_verdict(Kind.MESSAGE, [*merged.values(), *content], base=MESSAGE_BASE, confidence=conf)
        p = bot.pocket
        p.see_account(author.id, author.name, author.global_name, author.avatar.key if author.avatar else None)
        p.record_check(kid, author.id, "message", own_v.level.value)
        if own_v.level is not Level.GREEN and p.reporter_weight(kid) > 0:
            p.record_marks(author.id, joined, "pocket")
        p.refresh(author.id)
    return v


class BusyNote:
    """The "busy, you're next" message for a kid's check; remembers whether it was shown so the
    result replaces it instead of arriving as a second message."""

    def __init__(self, lang: Lang, show: Callable[[discord.Embed], Awaitable[Any]]) -> None:
        self.lang, self._show, self.shown = lang, show, False

    async def __call__(self, place: int) -> None:
        await self._show(render.notice_embed("ai.busy", self.lang, place=place))
        self.shown = True


def hash_texts(texts: list[str]) -> str:
    return hashlib.blake2b("\x1f".join(texts).encode(), digest_size=8).hexdigest()


def check_person(bot: GuildwardBot, kid: int, lang: Lang, user: discord.User, base: Verdict) -> Verdict:
    if not bot.pocket or user.id == kid:
        return base
    p = bot.pocket
    p.see_account(user.id, user.name, user.global_name, user.avatar.key if user.avatar else None)
    p.record_check(kid, user.id, "person", base.level.value)  # profile-only, never fed by crowd flags
    return with_signals(base, crowd_extra(bot, user.id, lang), base=5, confidence=Confidence.MEDIUM)


def check_server(bot: GuildwardBot, kid: int, lang: Lang, gid: int | None, inviter: int | None,
                 base: Verdict) -> Verdict:
    extra: list[Signal] = []
    if bot.pocket and gid is not None:
        if (n := bot.pocket.server_red_checkers(gid)) >= 3:
            extra.append(Signal("pocket.server_reds", min(30, 10 + 5 * (n - 3)), {"n": n}))
        if (g := guard_grade(bot, gid, lang)) is not None:
            extra.append(Signal("pocket.guard_grade", GRADE_WEIGHT[g], {"grade": g}))
    if bot.pocket and inviter is not None and inviter != kid:
        extra += [s for s in crowd_extra(bot, inviter, lang) if s.weight > 0]
    if bot.pocket and gid is not None:
        bot.pocket.record_server_check(kid, gid, base.level.value)
    return with_signals(base, extra, base=20, confidence=Confidence.MEDIUM if extra else None)


def guard_grade(bot: GuildwardBot, gid: int, lang: Lang) -> str | None:
    guard = getattr(bot, "guard", None)
    if guard is None or bot.store is None:
        return None
    g = bot.store.guild(gid)
    if g is None or g["left_at"] is not None:
        return None
    with contextlib.suppress(Exception):
        return guard.reports.health(gid, lang)[0]["grade"]
    return None


# --- delivery ---------------------------------------------------------------------------------
async def try_dm(bot: GuildwardBot, uid: int, embed: discord.Embed, view: discord.ui.View | None = None) -> bool:
    """Bots can only DM people they share a server with (or who opened a DM); remember what worked."""
    try:
        user = bot.get_user(uid) or await bot.fetch_user(uid)
        kwargs: dict[str, Any] = {"embed": embed}
        if view is not None:
            kwargs["view"] = view
        await user.send(**kwargs)
    except discord.HTTPException:
        if bot.pocket:
            bot.pocket.set_dm(uid, "blocked")
        return False
    if bot.pocket:
        bot.pocket.set_dm(uid, "ok")
    return True


def dm_hint_embed(bot: GuildwardBot, lang: Lang) -> discord.Embed:
    key = "pocket.dm_blocked_home" if bot.settings.home_invite else "pocket.dm_blocked"
    return render.notice_embed(key, lang)


# --- buttons under a result -------------------------------------------------------------------
class ResultView(discord.ui.View):
    def __init__(self, bot: GuildwardBot, *, kid: int, lang: Lang, v: Verdict, account: discord.abc.User | None = None,
                 message: discord.Message | None = None, texts: list[str] | None = None,
                 recheck: Callable[[], Awaitable[tuple[discord.Embed, discord.ui.View]]] | None = None) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.bot, self.kid, self.lang, self.v = bot, kid, lang, v
        self._recheck = recheck
        self.account, self.message, self.texts = account, message, texts or []
        other = account is not None and account.id != kid
        risky = v.level is not Level.GREEN
        if risky:
            self.add_item(discord.ui.Button(label=t("ui.btn_report", lang), url=render.REPORT_URL, row=1))
        if not (bot.pocket and other):
            self.remove_item(self.report)
        if not (other and message is not None):
            self.remove_item(self.evidence)
        if not (self.texts and bot.settings.anthropic_key and bot.web):
            self.remove_item(self.ask_ai)
        if not (risky and bot.pocket and bot.pocket.adult_of(kid)):
            self.remove_item(self.tell_adult)
        if recheck is None or not any(s.code == "ai.unfinished" for s in v.signals):
            self.remove_item(self.check_again)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.kid

    @discord.ui.button(label="Report", style=discord.ButtonStyle.danger)
    async def report(self, interaction: discord.Interaction, _b: discord.ui.Button) -> None:
        assert self.account is not None
        text = self.message.content if self.message is not None else None
        await interaction.response.send_message(**report_picker(self.bot, self.kid, self.account, self.lang, text),
                                                ephemeral=True)

    @discord.ui.button(label="Evidence", style=discord.ButtonStyle.secondary)
    async def evidence(self, interaction: discord.Interaction, _b: discord.ui.Button) -> None:
        assert self.account is not None and self.message is not None
        await interaction.response.defer(ephemeral=True, thinking=True)  # DMs can take longer than Discord's 3 s
        embed = evidence_for(self.account, self.message, self.lang)
        if await try_dm(self.bot, self.kid, embed, AdultShareView(self.bot, self.kid, self.lang, embed)
                        if self.bot.pocket and self.bot.pocket.adult_of(self.kid) else None):
            await interaction.followup.send(t("pocket.evidence_sent", self.lang), ephemeral=True)
        else:
            await interaction.followup.send(embeds=[embed, dm_hint_embed(self.bot, self.lang)], ephemeral=True)

    @discord.ui.button(label="Ask AI", style=discord.ButtonStyle.secondary)
    async def ask_ai(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        texts, self.texts = self.texts, []  # one ask per check (a double tap sends nothing); text leaves memory
        if not texts:
            await interaction.response.send_message(t("pocket.ai_once", self.lang), ephemeral=True)
            return
        button.disabled = True
        await interaction.response.defer(ephemeral=True, thinking=True)
        op = await ai.second_opinion(texts, api_key=self.bot.settings.anthropic_key, session=self.bot.web,
                                     lang=self.lang)
        if op is None:
            await interaction.followup.send(embed=render.notice_embed("pocket.ai_failed", self.lang), ephemeral=True)
            return
        v = with_signals(self.v, ai.opinion_signals(op), base=MESSAGE_BASE)
        if self.bot.pocket:
            self.bot.pocket.store.bump(0, f"pocket.ai.{op.level}")
        await interaction.followup.send(embed=render.verdict_embed(v, self.lang, subject=t("pocket.ai_subject",
                                                                                           self.lang)),
                                        ephemeral=True)

    @discord.ui.button(label="Check again", style=discord.ButtonStyle.primary)
    async def check_again(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        assert self._recheck is not None
        button.disabled = True
        await interaction.response.defer(ephemeral=True, thinking=True)
        embed, view = await self._recheck()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="I need help", style=discord.ButtonStyle.primary)
    async def need_help(self, interaction: discord.Interaction, _b: discord.ui.Button) -> None:
        embed, view = kidhelp.help_menu(self.lang, helplines.region_for(self.bot, interaction.user.id, self.lang))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Tell my trusted adult", style=discord.ButtonStyle.secondary)
    async def tell_adult(self, interaction: discord.Interaction, _b: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        ok = await tell_adult(self.bot, self.kid, interaction.user, self.lang,
                              evidence_for(self.account, self.message, self.lang)
                              if self.account is not None and self.message is not None else None)
        talk = helplines.phrases(helplines.region_for(self.bot, self.kid, self.lang), self.lang)["talk"]
        await interaction.followup.send(t("pocket.adult_told" if ok else "pocket.adult_unreachable", self.lang,
                                          talk=talk), ephemeral=True)


def result_view(bot: GuildwardBot, **kw: Any) -> ResultView:
    view = ResultView(bot, **kw)
    for item in view.children:
        if isinstance(item, discord.ui.Button) and item.url is None:
            key = {view.report: "pocket.btn_report", view.evidence: "pocket.btn_evidence",
                   view.ask_ai: "pocket.btn_ai", view.need_help: "pocket.btn_help",
                   view.tell_adult: "pocket.btn_adult", view.check_again: "pocket.btn_recheck"}.get(item)
            if key:
                item.label = t(key, view.lang)
    return view


def evidence_for(account: discord.abc.User, message: discord.Message, lang: Lang) -> discord.Embed:
    return kidhelp.evidence_embed(lang=lang, sender_name=display_name(account), sender_id=account.id,
                                  sender_created=created_at(account.id), message_url=message.jump_url,
                                  sent_at=message.created_at, excerpt=message.content or None)


def report_picker(bot: GuildwardBot, kid: int, account: discord.abc.User, lang: Lang,
                  text: str | None = None) -> dict[str, Any]:
    view = discord.ui.View(timeout=VIEW_TIMEOUT)
    select = discord.ui.Select(placeholder=t("pocket.report_pick", lang), options=[
        discord.SelectOption(label=t(f"pocket.reason.{r}", lang), value=r) for r in crowd.REPORT_REASONS])

    async def picked(interaction: discord.Interaction) -> None:
        ok = bot.pocket.report(kid, account.id, select.values[0])
        if ok and text and bot.pocket.reporter_weight(kid) > 0:
            bot.pocket.record_marks(account.id, text, "report")  # hashed handles/scripts, credible reports only
        await interaction.response.edit_message(
            content=t("pocket.reported" if ok else "pocket.report_failed", lang), view=None)

    select.callback = picked
    view.add_item(select)
    return {"content": t("pocket.report_intro", lang, name=display_name(account)), "view": view}


class AdultShareView(discord.ui.View):
    def __init__(self, bot: GuildwardBot, kid: int, lang: Lang, evidence: discord.Embed) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.bot, self.kid, self.lang, self.evidence_embed = bot, kid, lang, evidence
        self.send.label = t("pocket.btn_adult", lang)

    @discord.ui.button(label="Tell my trusted adult", style=discord.ButtonStyle.primary)
    async def send(self, interaction: discord.Interaction, _b: discord.ui.Button) -> None:
        await interaction.response.defer(thinking=True)
        ok = await tell_adult(self.bot, self.kid, interaction.user, self.lang, self.evidence_embed)
        await interaction.followup.send(t("pocket.adult_told" if ok else "pocket.adult_unreachable", self.lang))


async def tell_adult(bot: GuildwardBot, kid: int, kid_user: discord.abc.User, lang: Lang,
                     evidence: discord.Embed | None) -> bool:
    adult = bot.pocket.adult_of(kid) if bot.pocket else None
    if adult is None:
        return False
    row = bot.pocket.user(adult)
    alang: Lang = row["lang"] if row and row["lang"] in ("en", "sv") else lang
    embed = discord.Embed(title=t("pocket.adult_alert_title", alang),
                          description=t("pocket.adult_alert", alang, name=display_name(kid_user)), color=0xDA3633,
                          timestamp=datetime.now(UTC))
    ok = await try_dm(bot, adult, embed)
    if ok and evidence is not None:
        with contextlib.suppress(discord.HTTPException):
            user = bot.get_user(adult) or await bot.fetch_user(adult)
            await user.send(embed=evidence)
    bot.pocket.store.bump(0, "pocket.adult_alert")
    return ok


def watch_embed(news: str, name: str, lang: Lang) -> discord.Embed:
    color = 0x57606A if news == "deleted" else 0xDA3633
    return discord.Embed(title=t(f"pocket.watch.{news}.title", lang),
                         description=t(f"pocket.watch.{news}", lang, name=discord.utils.escape_markdown(name)),
                         color=color).set_footer(text=t("pocket.watch_footer", lang))


register({
    "pocket.convo": {
        "en": "Across these messages, the steps groomers use show up in order: {stages}.",
        "sv": "I de här meddelandena syns stegen som groomare använder: {stages}.",
    },
    "pocket.server_reds": {
        "en": "{n} other Guildward users got a red result for this server.",
        "sv": "{n} andra Guildward-användare fick rött resultat för den här servern.",
    },
    "pocket.guard_grade": {
        "en": "This server uses Guildward Guard. Its safety grade is {grade} (A is best).",
        "sv": "Servern använder Guildward Guard. Dess säkerhetsbetyg är {grade} (A är bäst).",
    },
    "pocket.btn_report": {"en": "Report to Guildward", "sv": "Rapportera till Guildward"},
    "pocket.btn_evidence": {"en": "Save evidence", "sv": "Spara bevis"},
    "pocket.btn_ai": {"en": "Ask AI (sends this text to Anthropic)", "sv": "Fråga AI (skickar texten till Anthropic)"},
    "pocket.btn_help": {"en": "I need help", "sv": "Jag behöver hjälp"},
    "pocket.btn_adult": {"en": "Tell my trusted adult", "sv": "Säg till min trygga vuxna"},
    "pocket.btn_recheck": {"en": "Check again", "sv": "Kolla igen"},
    "ai.busy": {
        "en": "Lots of checks right now, so yours is waiting in line: you're number {place}. Kids' checks always go "
              "first, so you're next in priority. Your full result will show up right here.",
        "sv": "Många kollar just nu, så din står i kö: du är nummer {place}. Barns kollar går alltid först, så du är "
              "näst på tur. Hela svaret dyker upp här.",
    },
    "ai.unfinished": {
        "en": "The AI part didn't finish, so this result only uses the word rules. Tap **Check again** in a minute.",
        "sv": "AI-delen blev inte klar, så det här svaret bygger bara på ordreglerna. Tryck **Kolla igen** om en minut.",
    },
    "pocket.ai_once": {"en": "You already asked the AI about this one.", "sv": "Du har redan frågat AI:n om den här."},
    "pocket.ai_subject": {"en": "Second opinion from AI", "sv": "Andra åsikt från AI"},
    "pocket.ai_failed": {
        "en": "The AI check didn't work right now. Trust the result above, and ask an adult if you're unsure.",
        "sv": "AI-kollen fungerade inte just nu. Lita på resultatet ovan och fråga en vuxen om du är osäker.",
    },
    "pocket.evidence_sent": {
        "en": "I sent the evidence to your DMs with Guildward, so it stays saved even if they delete their account.",
        "sv": "Jag skickade bevisen till dina DM med Guildward, så de finns kvar även om hen raderar sitt konto.",
    },
    "pocket.dm_blocked": {
        "en": "I can't send you DMs yet. Send me any message in DMs once, then try again.",
        "sv": "Jag kan inte skicka DM till dig än. Skicka ett meddelande till mig i DM en gång och försök igen.",
    },
    "pocket.dm_blocked_home": {
        "en": "I can't send you DMs yet. Join the Guildward server with /guildward alerts, then try again.",
        "sv": "Jag kan inte skicka DM till dig än. Gå med i Guildward-servern med /guildward alerts och försök igen.",
    },
    "pocket.report_intro": {
        "en": "What did {name} do? Your report is anonymous: they never see it, and other kids only see a count.",
        "sv": "Vad gjorde {name}? Din rapport är anonym: hen ser den aldrig, och andra ser bara ett antal.",
    },
    "pocket.report_pick": {"en": "Pick what happened", "sv": "Välj vad som hände"},
    "pocket.reason.age_pics": {"en": "Asked my age or for pictures", "sv": "Frågade om min ålder eller bilder"},
    "pocket.reason.sexual": {"en": "Sexual messages", "sv": "Sexuella meddelanden"},
    "pocket.reason.threat": {"en": "Threatened me", "sv": "Hotade mig"},
    "pocket.reason.meet": {"en": "Wants to meet me", "sv": "Vill träffa mig"},
    "pocket.reason.scam": {"en": "Scam or wants money", "sv": "Bedrägeri eller vill ha pengar"},
    "pocket.reason.hate": {"en": "Hate or bullying", "sv": "Hat eller mobbning"},
    "pocket.reason.other": {"en": "Something else felt wrong", "sv": "Något annat kändes fel"},
    "pocket.reported": {
        "en": "Thanks. Your report helps warn other kids. If you feel unsafe, block them and tell an adult.",
        "sv": "Tack. Din rapport hjälper till att varna andra. Känner du dig otrygg: blockera och säg till en vuxen.",
    },
    "pocket.report_failed": {"en": "That report didn't go through.", "sv": "Rapporten gick inte igenom."},
    "pocket.adult_told": {
        "en": "I told your trusted adult that you need help.",
        "sv": "Jag har sagt till din trygga vuxna att du behöver hjälp.",
    },
    "pocket.adult_unreachable": {
        "en": "I couldn't reach your trusted adult on Discord. Please tell them in person, or talk to {talk}.",
        "sv": "Jag nådde inte din trygga vuxna på Discord. Säg till hen direkt, eller prata med {talk}.",
    },
    "pocket.adult_alert_title": {"en": "Your kid asked for help", "sv": "Ditt barn bad om hjälp"},
    "pocket.adult_alert": {
        "en": "{name} pressed \"Tell my trusted adult\" in Guildward. Talk to them calmly soon: they did the right "
              "thing by telling you. Any evidence they shared follows below.",
        "sv": "{name} tryckte på \"Säg till min trygga vuxna\" i Guildward. Prata lugnt med hen snart: hen gjorde "
              "rätt som berättade. Eventuella bevis följer nedan.",
    },
    "pocket.watch.flagged.title": {"en": "Heads up about someone you checked", "sv": "Viktigt om någon du kollade"},
    "pocket.watch.flagged": {
        "en": "Other Guildward users have now flagged **{name}**, someone you checked before. If you're still "
              "talking: don't share pictures, your age, school or address, and think about blocking them.",
        "sv": "Andra Guildward-användare har nu flaggat **{name}**, som du kollade tidigare. Om ni fortfarande "
              "pratar: dela inga bilder, ålder, skola eller adress, och fundera på att blockera hen.",
    },
    "pocket.watch.confirmed.title": {"en": "Block this account", "sv": "Blockera det här kontot"},
    "pocket.watch.confirmed": {
        "en": "**{name}**, someone you checked before, has been confirmed as dangerous to kids. Block them now. "
              "If they asked you for anything or threatened you, it's not your fault: tell an adult or press "
              "\"I need help\".",
        "sv": "**{name}**, som du kollade tidigare, är bekräftad som farlig för barn. Blockera hen nu. Om hen bett "
              "dig om något eller hotat dig är det inte ditt fel: säg till en vuxen eller tryck \"Jag behöver hjälp\".",
    },
    "pocket.watch.deleted.title": {"en": "That account is gone", "sv": "Det kontot är borta"},
    "pocket.watch.deleted": {
        "en": "**{name}**, who sent you something worrying, deleted their account. People who do this often come "
              "back with a new one. If someone new writes the same kind of things, it may be them.",
        "sv": "**{name}**, som skickade något oroande, har raderat sitt konto. Sådana personer kommer ofta tillbaka "
              "med ett nytt. Om någon ny skriver likadant kan det vara samma person.",
    },
    "pocket.watch_footer": {
        "en": "You get this because you checked this account. Turn it off: /guildward settings",
        "sv": "Du får detta för att du kollade kontot. Stäng av: /guildward settings",
    },
})
