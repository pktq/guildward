"""Settings from environment variables, with an optional .env file (real env vars win)."""

from __future__ import annotations

import base64
import binascii
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
    token: str  # the one Guildward bot (kids' app + Guard)
    dev_guild_id: int | None
    log_level: str
    database: str = "data/guildward.db"
    dashboard_url: str = "http://localhost:8080"
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8080
    owner_ids: frozenset[int] = frozenset()
    client_secret: str = ""  # app OAuth: server scan + dashboard "Sign in with Discord"; empty = both off
    home_invite: str = ""  # Guildward community server invite, so the bot can DM kids who share no server with it
    anthropic_key: str = ""  # opt-in AI second opinion; empty = button hidden
    safe_browsing_key: str = ""  # Google Safe Browsing for link checks; optional
    model: bool = True  # local message model (intel/semantic.py); GUILDWARD_MODEL=off = rules only

    @property
    def app_id(self) -> int | None:
        """The bot's application ID from the token's first part (base64 of the bot user ID), so Discord
        sign-in on the dashboard works while the bot itself is offline."""
        head = self.token.split(".", 1)[0]
        try:
            raw = base64.b64decode(head + "=" * (-len(head) % 4), validate=True).decode()
        except (binascii.Error, UnicodeDecodeError):
            return None
        return int(raw) if raw.isdigit() else None

    @classmethod
    def from_env(cls, env_file: Path = Path(".env"), *, need_token: bool = True) -> Settings:
        load_dotenv(env_file)
        # GUARD_TOKEN is from when Guard was a second app; accepted so older .env files keep working.
        token = os.environ.get("DISCORD_TOKEN", "").strip() or os.environ.get("GUARD_TOKEN", "").strip()
        if need_token and not token:
            raise SystemExit("DISCORD_TOKEN is missing. Copy .env.example to .env and paste your bot token.")
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
            database=os.environ.get("DATABASE_PATH", "").strip() or "data/guildward.db",
            dashboard_url=(os.environ.get("DASHBOARD_URL", "").strip() or f"http://localhost:{port}").rstrip("/"),
            dashboard_host=os.environ.get("DASHBOARD_HOST", "").strip() or "127.0.0.1",
            dashboard_port=int(port),
            owner_ids=frozenset(int(p) for p in owners.split(",") if p),
            client_secret=os.environ.get("DISCORD_CLIENT_SECRET", "").strip(),
            home_invite=os.environ.get("HOME_INVITE", "").strip(),
            anthropic_key=os.environ.get("ANTHROPIC_API_KEY", "").strip(),
            safe_browsing_key=os.environ.get("SAFE_BROWSING_KEY", "").strip(),
            model=os.environ.get("GUILDWARD_MODEL", "").strip().lower() not in ("off", "0", "false", "no"),
        )
