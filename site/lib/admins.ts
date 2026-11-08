// Guard setup for /admins. Commands, permissions and limits match src/guildward/guard (commands.py, bot.py, store.py).

import type { Step } from "./parents";

export const GUARD_STEPS: Step[] = [
  {
    id: "channel",
    title: "Make a private channel for alerts",
    why: "Alerts name members, say who a message was aimed at and can quote it. Guard refuses a channel that @everyone can see, so make one only your moderators can read.",
    same: [
      "Create a text channel, for example #mod-alerts.",
      "In its permissions, turn off View Channel for @everyone.",
      "Turn on View Channel for your moderator role.",
    ],
    tip: "Add a ping role later in the dashboard settings if you want red alerts to notify someone.",
  },
  {
    id: "add",
    title: "Add Guard to the server",
    why: "Guard is the same Guildward bot, added to the server with the permissions its actions use: view channels, send messages, embed links, read message history, manage messages, timeout, kick and ban members, manage roles, manage server and view the audit log. It never asks for Administrator.",
    install: "guard",
    same: [
      "Press the button above and pick your server. You need Manage Server there.",
      "Check the permission list Discord shows, then press Authorize.",
      "Give Guildward's role a place above the roles it should be able to time out or kick.",
    ],
    note: "Only want members to be able to run Guildward's checks in the server, without Guard reading anything? Pick “checks only” in the install dialog on the home page instead.",
  },
  {
    id: "setup",
    title: "Run /guard setup",
    why: "This points Guard at the alert channel and picks the mode. Start in observe mode: Guard only alerts, and your moderators decide everything.",
    code: "/guard setup channel:#mod-alerts mode:observe",
    same: [
      "Run it in any channel. Only people with Manage Server can use /guard.",
      "Optional: language:Svenska for alerts in Swedish.",
      "Guard replies with a first safety report and a button to apply the recommended settings.",
    ],
  },
  {
    id: "scan",
    title: "Let Guard learn from recent history",
    why: "A scan reads back up to 30 days of messages so members who already crossed lines get a score straight away. It doesn't post alerts for old messages.",
    code: "/guard scan days:14",
    same: ["Run it once after setup. Guard tells you how many messages and members it looked at."],
  },
  {
    id: "audit",
    title: "Fix what the audit finds",
    why: "The audit grades the server from A to F on structure: verification level, the explicit media filter, AutoMod, who can ping @everyone, 2FA for moderators, NSFW channels next to kids, moderator coverage and Guard's own permissions.",
    code: "/guard audit",
    same: [
      "Press Apply recommended settings to fix verification, the media filter, AutoMod and @everyone pings in one go.",
      "Anything Guard can't change itself is listed with what to do.",
    ],
  },
  {
    id: "minors",
    title: "Tell Guard which roles mean under 18",
    why: "Guard weighs a message much more heavily when it's aimed at a minor. It picks up ages members state themselves and age roles by name, and you can mark your own roles so nothing is missed.",
    same: [
      "Open the dashboard and press Sign in with Discord. (Or run /guard dashboard for a one-time sign-in link.)",
      "Open Settings and tick the roles that mean a member is under 18.",
      "While you're there: alert level, ping role, quarantine role and how long data is kept (7 to 365 days, 90 by default).",
    ],
  },
  {
    id: "team",
    title: "Give your moderators dashboard access",
    why: "Admins (the owner and anyone with Manage Server) always get in. Everyone else gets in through a role you pick. Access is checked against their current roles on every page, so taking the role away takes access away at once.",
    same: [
      "In the dashboard, open Settings, then Dashboard access.",
      "Pick a role and choose View (alerts, members and reports) or Act (also resolve alerts and time out, kick or ban, within that person's own Discord permissions).",
      "Your moderators sign in with Discord on the dashboard. Settings and the one-click fixes stay with admins.",
    ],
    tip: "On an alert, I'm on it shows the team who is handling it, and a short note when closing it keeps the case history readable.",
  },
  {
    id: "members",
    title: "Tell your members how to report",
    why: "Members often see things moderators don't. Anyone can report a message to your moderators, and it lands in the same alert channel with the context Guard already has.",
    same: [
      "Right-click a message (or long-press on a phone), then Apps, then Report to mods.",
      "Moderators can right-click a member, then Apps, then Guard report, for that person's full report.",
    ],
    tip: "A short pinned message in your rules channel is enough.",
  },
  {
    id: "protect",
    title: "Switch to protect mode when you trust it",
    why: "In protect mode Guard also acts on its own: it deletes the worst messages aimed at minors, times out members who turn red until a moderator looks, and quarantines raid accounts. Everything it does shows up in the alert, for a moderator to review.",
    code: "/guard setup channel:#mod-alerts mode:protect",
    same: [
      "Give it a week or two in observe mode first, and mark false alarms as False alarm so you can see how well it fits your server.",
      "Make sure Guildward's role is above the roles of the members it should be able to time out.",
    ],
  },
];
