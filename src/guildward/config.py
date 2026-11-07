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


def _id(name: str) -> int | None:
    raw = os.environ.get(name, "").strip()
    if raw and not raw.isdigit():
        raise SystemExit(f"{name} must be a numeric Discord ID (or empty).")
    return int(raw) if raw else None


@dataclass(frozen=True, slots=True)
class Settings:
    token: str  # pocket app (kid-facing, user-install, no intents); may be empty if only Guard runs
    dev_guild_id: int | None
    log_level: str
    guard_token: str = ""  # Guard (server-admin bot); empty = Guard off
    database: str = "data/guildward.db"
    dashboard_url: str = "http://localhost:8080"
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8080
    owner_ids: frozenset[int] = frozenset()

    @classmethod
    def from_env(cls, env_file: Path = Path(".env"), *, need_token: bool = True) -> Settings:
        load_dotenv(env_file)
        token = os.environ.get("DISCORD_TOKEN", "").strip()
        guard = os.environ.get("GUARD_TOKEN", "").strip()
        if need_token and not (token or guard):
            raise SystemExit("DISCORD_TOKEN (and/or GUARD_TOKEN) is missing. Copy .env.example to .env and paste "
                             "your bot token(s).")
        owners = os.environ.get("OWNER_IDS", "").replace(" ", "")
        if owners and not all(p.isdigit() for p in owners.split(",")):
            raise SystemExit("OWNER_IDS must be comma-separated numeric Discord user IDs.")
        port = os.environ.get("DASHBOARD_PORT", "8080").strip()
        if not port.isdigit():
            raise SystemExit("DASHBOARD_PORT must be a number.")
        return cls(
            token=token,
            dev_guild_id=_id("DEV_GUILD_ID"),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            guard_token=guard,
            database=os.environ.get("DATABASE_PATH", "").strip() or "data/guildward.db",
            dashboard_url=(os.environ.get("DASHBOARD_URL", "").strip() or f"http://localhost:{port}").rstrip("/"),
            dashboard_host=os.environ.get("DASHBOARD_HOST", "").strip() or "127.0.0.1",
            dashboard_port=int(port),
            owner_ids=frozenset(int(p) for p in owners.split(",") if p),
        )
