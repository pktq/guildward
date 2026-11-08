# Guard dashboard API (v1)

Served by the Guard process (aiohttp, same event loop as the bots) at `DASHBOARD_URL` (default `http://localhost:8080`).
The dashboard SPA is `web/dashboard/` served at `/`. Hash routes:

- `#/g/<gid>` overview · `#/g/<gid>/alerts` · `#/g/<gid>/members` · `#/g/<gid>/member/<uid>` · `#/g/<gid>/settings` · `#/g/<gid>/report` (printable)
- `#/owner` bot-owner dashboard (only when `/api/me` says `owner: true`)

## Conventions

- All Discord IDs are **strings** (JS can't hold 64-bit ints).
- Times are ISO-8601 UTC strings (`2026-11-07T12:34:56Z`), or `null`.
- `level` is `"green" | "yellow" | "red"`. `score` is 0–100 risk (higher = worse).
- All human text (`text`, `title`, `summary`, `label`, …) is already translated server-side into the session language (`en` / `sv`). The frontend translates only its own chrome.
- Auth: cookie `gw_session` (HttpOnly, SameSite=Strict). Any 401 → show the sign-in screen: "Run `/guard dashboard` in your server to get a sign-in link."
- Every POST/PUT must send header `X-Guildward: 1` and a JSON body. Errors: `{"ok": false, "error": "<translated text>"}` with 4xx.
- Sign-in: `GET /auth?t=<token>` sets the cookie and redirects to `/#/g/<gid>` (or `/#/owner`). `POST /api/logout` clears it.

## Shared shapes

```jsonc
// Signal: one observed fact behind a score
{"code": "member.age_probe_many", "weight": 30, "severe": false, "text": "Asked 4 different people their age", "at": "2026-11-06T18:00:00Z"}

// UserRef
{"id": "123", "name": "Some Name (@handle)", "avatar": "https://cdn.discordapp.com/..." , "minor": false}

// MemberRow
{
  "id": "123", "name": "Display (@handle)", "avatar": null,
  "score": 72, "level": "red",
  "status": "none",            // none | watch | trusted | actioned | left
  "joined_at": "...", "account_age_days": 3, "self_age": 14,   // self_age: age they disclosed, or null
  "minor": true,               // disclosed or role says under 18
  "flags": ["new_account", "reported", "network"],  // short machine tags, see below
  "trend": 18,                 // score change over last 7 days (+ = worse)
  "last_seen": "...",
  "top_signal": "Tried to move 3 people to Snapchat"   // translated, or null
}
// flags vocabulary: new_account, no_avatar, reported, network, watch, trusted, minor, adult_contacting_minors, escalating, raid, quarantined

// Alert
{
  "id": 42, "kind": "message",   // message | member | raid | report | network | join
  "level": "red", "score": 81,
  "title": "Possible grooming: photo request to a minor",
  "summary": "Display (@handle) asked a 13-year-old member for photos in #general.",
  "quote": "optional excerpt or null",   // only if the guild allows quotes; never stored, may be null
  "user": UserRef, "target": UserRef,     // either may be null
  "signals": [Signal],
  "jump_url": "https://discord.com/channels/g/c/m" ,  // or null
  "status": "open",              // open | resolved | false_positive
  "created_at": "...", "resolved_by": "ModName" , "action": "timeout"   // last two null while open
}
```

## Server admin endpoints

`GET /api/me`
```json
{"user": {"id": "1", "name": "morphh", "avatar": null}, "owner": true, "lang": "en",
 "guilds": [{"id": "10", "name": "Minecraft Kids SE", "icon": null}]}
```

`GET /api/guilds/{gid}/overview`
```jsonc
{
  "guild": {"id": "10", "name": "…", "icon": null, "member_count": 812, "guard_since": "…",
            "mode": "protect", "alert_channel": "#mod-alerts"},
  "health": {"score": 41, "level": "yellow", "grade": "C", "confidence": "Based on a full safety audit, including moderation and chat patterns.",
             "signals": [Signal]},             // server-level reasons, strongest first
  "summary": ["812 members, an estimated 230 are under 18.", "…"],   // synthesized report sentences
  "recommendations": [{"severity": "high", "text": "Turn on the explicit media filter for all members.", "fix": "content_filter"}],
  // fix: id of a one-click fix the backend can apply via POST /api/guilds/{gid}/fix, or null
  "kpis": {"members": 812, "minors_est": 230, "at_risk": 14, "red": 3, "open_alerts": 5,
           "flagged_7d": 22, "messages_7d": 9120, "joins_7d": 61, "actions_7d": 4, "median_response_min": 12},
  "series": {"days": ["2026-10-09", "… 30 days …"], "messages": [], "flagged": [], "joins": [], "alerts": []},
  "top_risks": [MemberRow],        // up to 8, highest score first
  "recent_alerts": [Alert],        // up to 8, newest first
  "audit": [{"id": "verification", "ok": false, "severity": "high", "label": "Verification level", "detail": "Low: anyone with a verified email can talk.", "fix": "verification"}],
  "permissions_missing": ["Moderate Members"]   // Discord permissions Guard needs but lacks (translated names)
}
```

`POST /api/guilds/{gid}/fix` `{"fix": "verification"}` → `{"ok": true, "text": "Verification raised to Medium."}`
Fix ids: `verification`, `content_filter`, `automod_presets`, `automod_spam`, `automod_mentions`, `everyone_mentions`.

`GET /api/guilds/{gid}/alerts?status=open|all&limit=50` → `{"alerts": [Alert]}`

`POST /api/guilds/{gid}/alerts/{id}` `{"action": "resolve|false_positive|timeout|kick|ban|delete|watch"}` → `{"ok": true, "alert": Alert}`

`GET /api/guilds/{gid}/members?filter=all|at_risk|minors|watch|new&sort=risk|recent|name&q=&limit=100`
→ `{"members": [MemberRow], "total": 812}`

`GET /api/guilds/{gid}/members/{uid}` → person report
```jsonc
{
  "member": MemberRow /* plus */ , // "username": "handle", "account_created": "…", "left_at": null, "invite_code": "abc", "roles": ["Member"]
  "verdict": {"score": 72, "level": "red", "confidence": "…", "signals": [Signal]},
  "summary": ["Account is 3 days old and joined through invite abc.", "Asked 4 different members their age, 3 of them under 18.", "…"],
  "prediction": {"trajectory": "rising", "escalation": "likely", "text": "Contact with one minor moved through 3 grooming stages in 2 days."},
  // trajectory: rising | stable | falling ; escalation: none | possible | likely
  "stats": {"messages": 140, "flagged": 9, "distinct_targets": 11, "minor_targets": 4, "reports": 2, "mod_actions": 1, "network_flags": 0},
  "contacts": [{"user": UserRef, "messages": 31, "stages": ["Trust building", "Risk check", "Isolation"], "level": "red", "last_at": "…"}],
  "timeline": [{"at": "…", "kind": "signal", "text": "Asked for photos (to a member under 18)", "level": "red", "jump_url": "…"}],
  // timeline kind: join | leave | signal | report | action | alert | name_change
  "series": {"days": ["… 30 …"], "messages": [], "flagged": []}
}
```

`POST /api/guilds/{gid}/members/{uid}` `{"action": "watch|trust|clear|timeout|kick|ban"}` → `{"ok": true, "member": MemberRow}`

`GET /api/guilds/{gid}/settings` → `{"settings": Settings, "channels": [{"id": "1", "name": "mod-alerts"}], "roles": [{"id": "2", "name": "Mods"}]}`
`PUT /api/guilds/{gid}/settings` `{partial Settings}` → `{"ok": true, "settings": Settings}`

```jsonc
// Settings
{
  "mode": "observe",              // observe (alerts only) | protect (automatic actions on)
  "alert_channel_id": "1" ,       // or null
  "alert_min_level": "yellow",    // yellow | red
  "ping_role_id": null,           // role pinged on red alerts
  "auto_delete": true,            // protect: delete red messages aimed at minors
  "auto_timeout": true,           // protect: 1h timeout when a member turns red, pending review
  "quarantine_role_id": null,     // role given to risky new joins
  "quarantine_new_accounts": false,
  "raid_protection": true,        // detect join bursts; in protect mode also quarantine/kick raid accounts
  "warn_targets": true,           // DM a member a kid-friendly safety tip when someone sends them a red message
  "network_share": true,          // share child-safety bans with other Guard servers and get their alerts
  "quote_in_alerts": true,        // include the flagged text in the alert (Discord only; never stored by Guard)
  "minor_role_ids": [],           // roles that mean "under 18" (auto-detected by name too)
  "retention_days": 90,
  "lang": "en"                    // en | sv: language of alerts posted in Discord
}
```

## Owner endpoints (403 unless owner)

`GET /api/owner/overview`
```jsonc
{
  "system": {"uptime_s": 5231, "version": "0.2.0", "rules": "private", "pocket_online": true, "guard_online": true,
             "latency_ms": {"pocket": 41, "guard": 39}, "db_bytes": 1830400, "events_per_min": 120,
             // local message model: state off | downloading | loading | ready | failed (detail says why)
             "model": {"state": "ready", "detail": "", "model": "Xenova/multilingual-e5-small", "head": "guildward-private",
                       "workers": 2, "texts": 48210, "shed": 0, "errors": 0, "busy_notes": 0, "queue_kids": 0,
                       "queue_guard": 1, "batch_ms_p50": 9.4}},
  "totals": {"guilds": 3, "members": 2200, "alerts_open": 9, "alerts_7d": 31, "flagged_7d": 50, "network_flags": 4, "pocket_checks_7d": 210},
  "series": {"days": ["… 30 …"], "pocket_checks": [], "alerts": [], "flagged": [], "messages": []},
  "pocket": {"server": {"green": 10, "yellow": 4, "red": 1}, "person": {"…": 0}, "message": {"…": 0}},   // last 30 days
  "guilds": [{"id": "10", "name": "…", "icon": null, "members": 812, "mode": "protect", "score": 41, "level": "yellow",
              "open_alerts": 5, "alerts_7d": 12, "joined_at": "…"}],
  "signal_quality": [{"code": "msg.age_probe", "label": "Age question", "fired_30d": 40, "false_positive": 6, "fp_rate": 0.15}],
  "network": [{"user": UserRef, "guilds": 2, "reasons": ["Banned for child safety"], "first_at": "…"}]
}
```

`POST /api/owner/network/{uid}` `{"action": "clear"}` → `{"ok": true}`
`POST /api/owner/guilds/{gid}` `{"action": "leave"}` → `{"ok": true}`

`GET /api/owner/overview` also carries `"crowd": {"users": 812, "accounts": 3400, "reports_7d": 41, "review": 3, "flagged": 2, "confirmed": 1, "watch_alerts_7d": 17}` (shared flags from the pocket app).

`GET /api/owner/accounts?status=review|flagged|confirmed|cleared|all` → shared flags for review. "review" = the automatic flag is watch/flagged and the owner hasn't decided.
```jsonc
{"counts": {"review": 3, "flagged": 2, "confirmed": 1, "cleared": 4},
 "accounts": [{"id": "123", "name": "chill_gamer_19", "avatar": "https://cdn.discordapp.com/…" | null, "created_at": 1700000000,
   "flag": "none|watch|flagged|confirmed|cleared",   // the owner's decision ("none" = automatic)
   "auto_flag": "none|watch|flagged", "score": 72, "level": "red",
   "checkers": 9, "red_checkers": 4, "reports": 5, "report_score": 3.4, "reasons": {"age_pics": 3, "threat": 1},
   "network": 1,                                     // Guard servers that banned it for child safety
   "links": [{"kind": "handle|payment|script|avatar|name", "other_id": "456", "other_name": "chill_gamer_20", "other_flag": "confirmed"}],
   "last_seen": 1700500000, "deleted": false}]}
```
Reporter identities never leave the store (they are keyed hashes).

`POST /api/owner/accounts/{uid}` `{"action": "confirm" | "clear" | "watch" | "reset"}` → `{"ok": true}`. `reset` removes the owner's decision so the automatic flag applies again. Confirm shows a strong warning to every kid who checks the account.

## Pocket OAuth (server scan)

`GET /pocket/callback?code=…&state=…`: Discord redirects here after a kid allows `/guildward scan` (scopes `identify guilds`). The state is a signed, single-use token naming the kid; the callback checks the Discord account matches, stores the refresh token, scans and DMs the result, and shows a short HTML page. Add `<DASHBOARD_URL>/pocket/callback` as a redirect in the Developer Portal.
