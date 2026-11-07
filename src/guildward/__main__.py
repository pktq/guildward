"""Run Guildward.

    uv run guildward                 pocket app + Guard + dashboard (whichever tokens are set)
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

from guildward.config import Settings


def _store(settings: Settings):
    from guildward.guard.store import Store

    return Store(settings.database)


async def _run(settings: Settings, *, sync: bool, bots: bool) -> None:
    from guildward.guard.engine import Engine
    from guildward.guard.reports import Reports
    from guildward.guard.web import Dashboard

    store = _store(settings)
    tasks, clients = [], []
    pocket = guard = None
    if bots and settings.token:
        from guildward.bot.app import GuildwardBot

        pocket = GuildwardBot(settings, sync=sync)
        pocket.store = store  # aggregate check counts only (kind + level per day), never IDs or content
        clients.append(pocket)
        tasks.append(pocket.start(settings.token))
    if bots and settings.guard_token:
        from guildward.guard.bot import GuardBot

        guard = GuardBot(store, dashboard_url=settings.dashboard_url, dev_guild_id=settings.dev_guild_id, sync=sync)
        clients.append(guard)
        tasks.append(guard.start(settings.guard_token))
    reports = guard.reports if guard else Reports(Engine(store))
    dash = None
    if guard or not bots:
        dash = Dashboard(store, reports, base_url=settings.dashboard_url, host=settings.dashboard_host,
                         port=settings.dashboard_port, owner_ids=settings.owner_ids, guard=guard, pocket=pocket)
        await dash.start()
        if not bots:
            print("owner sign-in:", _owner_link(dash), flush=True)
            tasks.append(asyncio.Event().wait())
    try:
        await asyncio.gather(*tasks)
    finally:
        for c in clients:
            with contextlib.suppress(Exception):
                await c.close()
        if dash:
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
