"""Run Guildward.

    uv run guildward                 the bot (kids' app + Guard) and the dashboard
    uv run guildward --sync          same, and push slash/context commands to Discord first
    uv run guildward owner-link      print a one-time sign-in link to the owner dashboard
    uv run guildward simulate        fill the database with a simulated server (to try the dashboard)
    uv run guildward dashboard       run only the dashboard (no Discord connection)
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging

import discord

from guildward.config import Settings


def _store(settings: Settings):
    from guildward.guard.store import Store

    return Store(settings.database)


async def _run(settings: Settings, *, sync: bool, bots: bool) -> None:
    from guildward.guard.engine import Engine
    from guildward.guard.reports import Reports
    from guildward.guard.web import Dashboard
    from guildward.pocket import Pocket

    store = _store(settings)
    bot = None
    if bots:
        from guildward.bot.app import GuildwardBot

        bot = GuildwardBot(settings, store, sync=sync)
    crowd = bot.pocket if bot else Pocket(store)
    reports = bot.reports if bot else Reports(Engine(store))
    dash = Dashboard(store, reports, base_url=settings.dashboard_url, host=settings.dashboard_host,
                     port=settings.dashboard_port, owner_ids=settings.owner_ids, guard=bot, pocket=bot, crowd=crowd,
                     client_secret=settings.client_secret, client_id=settings.app_id)
    await dash.start()
    try:
        if bot is not None:
            try:
                await bot.start(settings.token)
            except discord.PrivilegedIntentsRequired:
                raise SystemExit(
                    "Discord refused the login: turn on SERVER MEMBERS INTENT and MESSAGE CONTENT INTENT at "
                    f"https://discord.com/developers/applications/{bot.application_id or ''}/bot , save, and run "
                    "again. (Guard needs them; they only deliver data from servers that add the full bot.)") from None
        else:
            print("owner sign-in:", _owner_link(dash), flush=True)
            await asyncio.Event().wait()
    finally:
        if bot is not None:
            with contextlib.suppress(Exception):
                await bot.close()
        await dash.stop()
        store.close()


def _owner_link(dash) -> str:
    owner = min(dash.owner_ids, default=0)
    return dash.link(user_id=owner, name="Owner", avatar=None, guild_id=None, owner=True, lang="en")


def main() -> None:
    parser = argparse.ArgumentParser(prog="guildward")
    parser.add_argument("command", nargs="?", default="run", choices=["run", "owner-link", "simulate", "dashboard"])
    parser.add_argument("--sync", action="store_true",
                        help="push slash/context commands to Discord (run once after changing them)")
    args = parser.parse_args()

    settings = Settings.from_env(need_token=args.command == "run")
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    if args.command == "owner-link":
        from guildward.guard.engine import Engine
        from guildward.guard.reports import Reports
        from guildward.guard.web import Dashboard

        store = _store(settings)
        dash = Dashboard(store, Reports(Engine(store)), base_url=settings.dashboard_url, host="", port=0,
                         owner_ids=settings.owner_ids)
        print(_owner_link(dash))
        print("Works once, for 10 minutes, while the dashboard is running.")
        return
    if args.command == "simulate":
        from guildward.guard.simulate import simulate

        store = _store(settings)
        print(simulate(store))
        store.close()
        return
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_run(settings, sync=args.sync, bots=args.command == "run"))


if __name__ == "__main__":
    main()
