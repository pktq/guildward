"""Discord snowflake IDs encode their creation time: free, instant account/server age."""

from __future__ import annotations

from datetime import UTC, datetime

DISCORD_EPOCH_MS = 1_420_070_400_000


def created_at(snowflake: int) -> datetime:
    return datetime.fromtimestamp(((snowflake >> 22) + DISCORD_EPOCH_MS) / 1000, tz=UTC)


def age_days(snowflake: int, now: datetime | None = None) -> float:
    now = now or datetime.now(UTC)
    return (now - created_at(snowflake)).total_seconds() / 86_400
