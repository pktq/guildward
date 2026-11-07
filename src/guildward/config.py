"""Settings from environment variables, with an optional .env file (real env vars win)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    dev_guild_id: int | None
    log_level: str

    @classmethod
    def from_env(cls, env_file: Path = Path(".env")) -> Settings:
        load_dotenv(env_file)
        token = os.environ.get("DISCORD_TOKEN", "").strip()
        if not token:
            raise SystemExit("DISCORD_TOKEN is missing. Copy .env.example to .env and paste your bot token.")
        guild = os.environ.get("DEV_GUILD_ID", "").strip()
        if guild and not guild.isdigit():
            raise SystemExit("DEV_GUILD_ID must be a numeric server ID (or empty).")
        return cls(
            token=token,
            dev_guild_id=int(guild) if guild else None,
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )
