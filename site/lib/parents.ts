// Setup steps for /parents. Discord steps and help links come from the original lockdown wizard
// (web/wizard), checked against Discord's help pages; menu names follow Discord's English client.

export type Step = {
  id: string;
  title: string;
  why: string;
  desktop?: string[];
  mobile?: string[];
  same?: string[];
  list?: string[];
  see?: { canTitle: string; can: string[]; cannotTitle: string; cannot: string[] };
  install?: "kid" | "guard";
  code?: string; // a command to show as a copyable line
  note?: string;
  tip?: string;
  src?: [string, string][];
};

export const STEPS: Step[] = [
  {
    "id": "agegroup",
    "title": "Check Discord's age group",
    "why": "Discord estimates who is a teen (13 to 17) and then switches on extra protection automatically. If the account is put in the wrong group, none of that protection applies, so check it first.",
    "desktop": [
      "Click the cogwheel at the bottom left (User Settings).",
      "Click Account Status.",
      "Look at the age group. A teen account should say teen. If it says unconfirmed, the strict defaults still apply. That is fine."
    ],
    "mobile": [
      "Tap your profile picture at the bottom right.",
      "Tap the cogwheel at the top right.",
      "Tap Account Status and look at the age group."
    ],
    "note": "Only an adult should confirm their own age here. Never pick a wrong age to unlock things; it removes the protection.",
    "tip": "Discord's rules can vary a little by country, so a screen may look slightly different from this guide.",
    "src": [
      [
        "What Protections Do You Get in the Teen Age Group?",
        "https://support.discord.com/hc/en-us/articles/42178056096663-What-Protections-Do-You-Get-in-the-Teen-Age-Group"
      ]
    ]
  },
  {
    "id": "dms",
    "title": "Turn off DMs from people in servers",
    "why": "By default, anyone who shares a server with you can send you a private message. Most unwanted contact starts exactly like that, in a big server, then a DM. Switch it off, and people need to be your friend first.",
    "desktop": [
      "Click the cogwheel at the bottom left.",
      "Click Content & Social.",
      "Find the Social permissions section.",
      "Switch off Direct messages.",
      "Discord asks if you want to apply it to all your existing servers. Choose yes."
    ],
    "mobile": [
      "Tap your profile picture at the bottom right, then the cogwheel at the top right.",
      "Tap Content & Social.",
      "Scroll to Server Settings and switch off Direct messages."
    ],
    "note": "You can still DM your friends. You can also allow DMs for one small server you trust, from the same screen, if you really need to.",
    "tip": "",
    "src": [
      [
        "Blocking & Privacy Settings",
        "https://support.discord.com/hc/en-us/articles/217916488-Blocking-Privacy-Settings"
      ]
    ]
  },
  {
    "id": "friends",
    "title": "Limit who can send friend requests",
    "why": "A friend request is the door to everything else. If strangers can't send one, they have a much harder time getting close. 'Friends of friends' still lets real classmates and gaming friends find you.",
    "desktop": [
      "Click the cogwheel at the bottom left.",
      "Click Content & Social.",
      "Click Friend Requests.",
      "Turn off Everyone and Server Members. Leave Friends of Friends on."
    ],
    "mobile": [
      "Tap your profile picture at the bottom right, then the cogwheel at the top right.",
      "Tap Content & Social, then Friend Requests.",
      "Turn off Everyone and Server Members. Leave Friends of Friends on."
    ],
    "note": "If you turn off all three, nobody can send you a request at all. That is the safest, and you can still send requests yourself.",
    "tip": "Even with this on, Discord shows an alert before you accept a request from someone you share no friends or small servers with. Read it.",
    "src": [
      [
        "Blocking & Privacy Settings",
        "https://support.discord.com/hc/en-us/articles/217916488-Blocking-Privacy-Settings"
      ]
    ]
  },
  {
    "id": "requests",
    "title": "Check that Message Requests is on",
    "why": "Message requests put DMs from people who aren't your friends in a separate inbox, where you can look at them first. Images and links are hidden until you accept. Nothing lands in your normal chats from a stranger.",
    "desktop": [
      "Click the cogwheel at the bottom left.",
      "Click Content & Social (in some versions this part is called Messaging Permissions).",
      "Find Message Requests. It should be on.",
      "To see your inbox later: Home, then the Message Requests folder (it only shows when something is waiting)."
    ],
    "mobile": [
      "Tap your profile picture at the bottom right, then the cogwheel at the top right.",
      "Tap Content & Social (or Messaging Permissions) and check that Message Requests is on.",
      "To see the inbox later: open Direct Messages and look for the Message Requests tab."
    ],
    "note": "For teens it is on automatically and can't be turned off. This step is just a check, and a chance to explain: you don't have to accept anyone.",
    "tip": "Decline anything that feels off. You can also tap Block or Report from there.",
    "src": [
      [
        "Message Requests",
        "https://support.discord.com/hc/en-us/articles/7924992471191-Message-Requests"
      ]
    ]
  },
  {
    "id": "media",
    "title": "Blur or block sensitive pictures",
    "why": "Discord can spot pictures that may be sexual or violent and hide them before you see them. For teens this is on already: pictures from friends are blurred, from strangers blocked, in servers blurred. Nobody has to look at something that can't be unseen.",
    "desktop": [
      "Click the cogwheel at the bottom left.",
      "Click Content & Social.",
      "Find Sensitive content filters (Mature Sexual Media and Graphic Media).",
      "For Direct messages from friends, Direct messages from others and Messages in server channels, check that they say Blur or Block. For others' DMs choose Block."
    ],
    "mobile": [
      "Tap your profile picture at the bottom right, then the cogwheel at the top right.",
      "Tap Content & Social.",
      "Under Sensitive content filters, check the same three settings."
    ],
    "note": "No filter is perfect. If something slips through, don't forward it: take a screenshot only if a grown-up says to, then tap Report Message and block the sender.",
    "tip": "Teens can't choose Show. Only a confirmed adult can.",
    "src": [
      [
        "Discord Sensitive Content Filters",
        "https://support.discord.com/hc/en-us/articles/18210995019671-Discord-Sensitive-Content-Filters"
      ]
    ]
  },
  {
    "id": "teendefaults",
    "title": "What Discord already does for teens",
    "why": "Since 2025 Discord switches on a set of protections for accounts it thinks are teens. Knowing what they are means you can trust them without being blind to what they don't cover.",
    "list": [
      "Pictures flagged as sensitive are blurred or blocked (step 5).",
      "Servers and channels marked 18+ are closed. Only a confirmed adult can open them.",
      "Message requests are on (step 4), and spam filtering applies to all DMs.",
      "Discord shows a warning before you accept a friend request from someone you share no friends or small servers with.",
      "Discord can show a safety alert on a first DM, with an easy way to block the sender.",
      "Your profile and activity are only visible to friends and members of small servers (under 200 members).",
      "Speaking on Stage channels needs a confirmed adult. Listening is fine."
    ],
    "desktop": [
      "Open User Settings and look for Profile Privacy and Where I Share Activity. The safe choices are Friends & Small Servers Only, and Share in servers with 200 or fewer members."
    ],
    "mobile": [
      "Same settings, same names. Open Settings (profile picture, then cogwheel) and look for them there."
    ],
    "note": "These protections are a safety net, not a guarantee. The most important protection is still that you can tell a grown-up anything (see the last step).",
    "tip": "",
    "src": [
      [
        "What Protections Do You Get in the Teen Age Group?",
        "https://support.discord.com/hc/en-us/articles/42178056096663-What-Protections-Do-You-Get-in-the-Teen-Age-Group"
      ],
      [
        "Message Requests",
        "https://support.discord.com/hc/en-us/articles/7924992471191-Message-Requests"
      ]
    ]
  },
  {
    "id": "family",
    "title": "Link a parent in Family Center",
    "why": "Family Center is Discord's own tool. It lets a parent see who the young person talks to and which servers they join, and it lets the parent manage a few settings. It never shows what the messages say. Both of you can see the same list.",
    "desktop": [
      "Young person: click the cogwheel at the bottom left, then Account, then Family Center.",
      "Click My Family, then Show Code (a QR code) or Copy Link.",
      "Parent: scan the QR code with a phone, or open the link on a computer. No app is needed, the web works.",
      "Young person: accept the connection request that pops up. Done."
    ],
    "mobile": [
      "Young person: tap your profile picture at the bottom right, then the cogwheel, then Family Center, then My Family, then Show Code or Copy Link.",
      "Parent (in the Discord app): tap your profile picture, then Settings, then Family Center, then My Family, and scan the code.",
      "Young person: accept the request."
    ],
    "see": {
      "canTitle": "What the parent can see (last 7 days)",
      "can": [
        "New friends",
        "Who the young person messaged or called (names and pictures)",
        "Total call minutes",
        "Top five people and servers",
        "New servers and active servers",
        "Purchases and gifts received"
      ],
      "cannotTitle": "What the parent cannot see",
      "cannot": [
        "What any message says, in servers or DMs",
        "Anything from before you linked",
        "Which channels, or what is said in calls"
      ]
    },
    "note": "After you link, the settings in steps 2, 3, 4 and 5 are managed by the parent and the young person can no longer change them alone. Up to three parents or guardians can link. The parent also needs to be in Discord's adult age group to change the message request setting.",
    "tip": "Agree today what the parent will do with what they see: ask, not accuse.",
    "src": [
      [
        "Family Center for Teens",
        "https://support.discord.com/hc/en-us/articles/14155060633623-Family-Center-for-Teens"
      ],
      [
        "Family Center for Parents and Guardians",
        "https://support.discord.com/hc/en-us/articles/14155043715735-Family-Center-for-Parents-and-Guardians"
      ]
    ]
  },
  {
    "id": "guildward",
    "title": "Add Guildward to your kid's account",
    "why": "Guildward goes on your kid's own Discord account, not on a server, so it works in DMs, group chats and every server they're in. It gives them three quick checks they run themselves, and every answer is visible only to them. Guildward never stores message text.",
    "install": "kid",
    "desktop": [
      "On your kid's computer, press the button above and choose Add to My Apps (an account install, not a server).",
      "Check an invite link: in any chat type /check and paste the invite link.",
      "Check a person: right-click their name, then Apps, then Safety check.",
      "Check a message: right-click the message, then Apps, then Is this sketchy?"
    ],
    "mobile": [
      "On your kid's phone, press the button above and choose Add to My Apps.",
      "Check an invite link: type /check and paste the link.",
      "Check a person: tap and hold their profile, or open it, then Apps, then Safety check.",
      "Check a message: long-press the message, then Apps, then Is this sketchy?"
    ],
    "note": "Guildward gives a signal, not a verdict. A green result doesn't mean safe, and a red one doesn't mean guilty. If something feels wrong, it's always worth talking about.",
    "tip": "Your kid sees every answer. Guildward never reports anything to a parent behind their back."
  },
  {
    "id": "adult",
    "title": "Become their trusted adult",
    "why": "Under a worrying result, Guildward shows your kid a Tell my trusted adult button. If they press it, Guildward sends you a DM: “Your kid asked for help”, plus any evidence they chose to share. That is the only thing you ever receive. You never see their messages or their checks.",
    "install": "kid",
    "same": [
      "You: add Guildward to your own Discord account too, with the button above.",
      "Your kid: in any chat, type /guildward adult. Guildward shows them a code that works for 30 minutes.",
      "You: type /guildward adult and paste the code into the code box.",
      "Your kid gets a message that you are now their trusted adult. Done."
    ],
    "note": "Guildward can only reach you if Discord lets it DM you. Run /guildward alerts on your account to check.",
    "tip": "Tell your kid why you're doing this: not to watch them, but so asking for help is one button away."
  }
];

