"""Run the bot: `uv run guildward` (add --sync after changing commands)."""

from __future__ import annotations

import argparse
import logging

from guildward.bot.app import GuildwardBot
from guildward.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="guildward")
    parser.add_argument("--sync", action="store_true",
                        help="push slash/context commands to Discord (run once after changing them)")
    args = parser.parse_args()

    settings = Settings.from_env()
    logging.basicConfig(level=settings.log_level,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    GuildwardBot(settings, sync=args.sync).run(settings.token, log_handler=None)


if __name__ == "__main__":
    main()
