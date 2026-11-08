"""Play scripted chat through a Discord webhook so one person can test Guard in their own test server.

Guard treats plain webhook messages as members only in DEV_GUILD_ID. Setup:
  1. DEV_GUILD_ID in .env = your test server; start the bot; run /guard setup there.
  2. Say your (test) age in the server, e.g. "hi im 13", so Guard knows you are a kid;
     personas then talk to you and you get Guard's warning DM. No age roles needed.
  3. Server Settings > Integrations > Webhooks > New Webhook > Copy Webhook URL.

  uv run python tools/testdrive.py <webhook url> --kid <your user id> [--scene grooming] [--gap 4]

Each webhook name is one persona. Personas look like brand-new accounts.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

SCENES: dict[str, list[tuple[str, str]]] = {
    "benign": [  # should raise nothing
        ("Sam", "anyone up for ranked tonight?"),
        ("Mia", "me! after homework, im only 13 so i have to be off by 9"),
        ("Sam", "gg everyone, that last round was wild"),
        ("Mia", "lol {kid} you carried us"),
    ],
    "kids": [  # kid to kid: damped; at most yellow, because personas are brand-new accounts
        ("Leo", "{kid} how old are u? im 14"),
        ("Leo", "{kid} add me on snap its leo.plays"),
    ],
    "grooming": [  # should build up stages and alert the mods, then DM you a warning
        ("skyler.vibes", "{kid} ur actually so good at this game"),
        ("skyler.vibes", "{kid} how old are u btw?"),
        ("skyler.vibes", "{kid} u seem really mature for ur age"),
        ("skyler.vibes", "{kid} this server is so laggy, do u have snap? add me its skyler.vb"),
        ("skyler.vibes", "{kid} dont tell ur parents we talk ok, they wouldnt get it"),
        ("skyler.vibes", "{kid} send me a pic of u, just for me"),
    ],
    "sextortion": [  # threat stage: top-priority alert; payment tag for linking
        ("ghost.kayla", "{kid} i have ur pics and ur followers list"),
        ("ghost.kayla", "{kid} pay $200 in steam gift cards or i send them to everyone"),
        ("ghost.kayla", "{kid} u have 1 hour. cashapp $kaylaxo"),
    ],
}


def post(url: str, name: str, text: str, kid: int) -> None:
    body = json.dumps({"username": name, "content": text, "allowed_mentions": {"users": [kid]}}).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json", "User-Agent": "guildward-testdrive"})
    for _ in range(3):
        try:
            urllib.request.urlopen(req, timeout=15).close()
            return
        except urllib.error.HTTPError as e:
            if e.code != 429:
                sys.exit(f"webhook answered {e.code}: {e.read()[:200]!r}")
            time.sleep(float(json.loads(e.read() or b"{}").get("retry_after", 2)))
    sys.exit("still rate limited, try a bigger --gap")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("webhook", help="https://discord.com/api/webhooks/<id>/<token>")
    ap.add_argument("--kid", type=int, required=True, help="your Discord user id (the account personas talk to)")
    ap.add_argument("--scene", choices=[*SCENES, "all"], default="all")
    ap.add_argument("--gap", type=float, default=4.0, help="seconds between messages")
    a = ap.parse_args()
    if not (a.webhook.startswith("https://") and "/api/webhooks/" in a.webhook):
        sys.exit("that is not a Discord webhook URL")
    scenes = list(SCENES) if a.scene == "all" else [a.scene]
    for scene in scenes:
        print(f"-- {scene}")
        for name, text in SCENES[scene]:
            line = text.format(kid=f"<@{a.kid}>")
            print(f"{name}: {line}")
            post(a.webhook, name, line, a.kid)
            time.sleep(a.gap)


if __name__ == "__main__":
    main()
