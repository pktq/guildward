/* Guildward lockdown wizard. No dependencies, no network requests, no cookies.
   Stored locally only (try/catch): language ("gw-lang") and ticked steps ("gw-done"). */
(function () {
  "use strict";

  var HC = "https://support.discord.com/hc/en-us/articles/";

  var UI = {
    en: {
      skip: "Skip to content",
      tagline: "Lockdown wizard",
      langLabel: "Language",
      progress: function (n, t) { return "Step " + n + " of " + t; },
      stepsNav: "Steps",
      back: "Back",
      next: "Next",
      start: "Let's start",
      finish: "Finish",
      restart: "Start over",
      desktop: "On a computer or in the browser",
      mobile: "On a phone (iOS and Android)",
      why: "Why this matters",
      done: "We did this one together",
      source: "Discord's own help page for this step",
      noscript: "This wizard needs JavaScript to show one step at a time. Nothing is sent anywhere; it all runs on your device.",
      footer: "Guildward is free and open source. This page stores nothing about you. It has no trackers and no cookies. Your language choice and ticked steps stay in your own browser only. Discord menus change now and then; if a name looks a little different, look for the closest match.",
      privacy: "Privacy policy",
      ticked: function (n, t) { return n + " of " + t + " steps ticked"; }
    },
    sv: {
      skip: "Hoppa till innehållet",
      tagline: "Låsningsguide",
      langLabel: "Språk",
      progress: function (n, t) { return "Steg " + n + " av " + t; },
      stepsNav: "Steg",
      back: "Tillbaka",
      next: "Nästa",
      start: "Nu kör vi",
      finish: "Klar",
      restart: "Börja om",
      desktop: "På dator eller i webbläsaren",
      mobile: "I mobilen (iOS och Android)",
      why: "Varför det här spelar roll",
      done: "Vi har gjort det här tillsammans",
      source: "Discords egen hjälpsida för det här steget",
      noscript: "Guiden behöver JavaScript för att visa ett steg i taget. Inget skickas någonstans; allt körs på din enhet.",
      footer: "Guildward är gratis och öppen källkod. Den här sidan sparar ingenting om dig, har inga spårare och inga cookies. Ditt språkval och dina bockade steg stannar i din egen webbläsare. Discords menyer ändras ibland; om ett namn ser lite annorlunda ut, leta efter det som liknar mest.",
      privacy: "Integritetspolicy",
      ticked: function (n, t) { return n + " av " + t + " steg avbockade"; }
    }
  };

  /* Each step: kind "intro" | "step" | "talk". Menu names stay in English because that is how Discord's
     English client shows them; the Swedish text says so once in the intro. */
  var STEPS = [
    {
      id: "welcome", kind: "intro",
      en: {
        title: "Let's make Discord safer, together",
        lead: "This takes about 15 minutes. One of you holds the phone or laptop, the other reads along. There is one rule: you do it together, and the young person sees everything that gets changed. Nothing here is secret.",
        points: [
          "You will change a few settings on Discord, one at a time. We say exactly where to tap.",
          "Do the settings first. After you link a parent in Family Center, some of them can only be changed from the parent's side (step 7).",
          "You can stop at any time and come back. Ticked steps are remembered on this device only.",
          "Menu names are in English, as in Discord's English version. If your Discord is in Swedish, look for the closest match, or switch Discord to English for now."
        ],
        who: "You will need the young person's Discord logged in, and the parent's own Discord account for step 7."
      },
      sv: {
        title: "Gör Discord tryggare, tillsammans",
        lead: "Det tar ungefär 15 minuter. En av er håller i telefonen eller datorn, den andra läser med. Det finns en regel: ni gör det tillsammans, och den unga ser allt som ändras. Inget här är hemligt.",
        points: [
          "Ni ändrar några inställningar i Discord, en i taget. Vi visar exakt var ni ska trycka.",
          "Gör inställningarna först. När en förälder kopplas i Family Center kan en del av dem bara ändras från förälderns sida (steg 7).",
          "Ni kan sluta när som helst och fortsätta senare. Avbockade steg sparas bara på den här enheten.",
          "Menynamnen är på engelska, som i Discords engelska version. Har du Discord på svenska: leta efter det som liknar mest, eller byt Discord till engelska ett tag."
        ],
        who: "Ni behöver den unga personens Discord inloggat, och förälderns eget Discord-konto till steg 7."
      }
    },
    {
      id: "agegroup", kind: "step",
      src: [["What Protections Do You Get in the Teen Age Group?", HC + "42178056096663-What-Protections-Do-You-Get-in-the-Teen-Age-Group"]],
      // https://support.discord.com/hc/en-us/articles/42178056096663 (updated Oct 2026)
      en: {
        title: "Check Discord's age group",
        why: "Discord estimates who is a teen (13 to 17) and then switches on extra protection automatically. If the account is put in the wrong group, none of that protection applies, so check it first.",
        desktop: ["Click the cogwheel at the bottom left (User Settings).", "Click Account Status.", "Look at the age group. A teen account should say teen. If it says unconfirmed, the strict defaults still apply. That is fine."],
        mobile: ["Tap your profile picture at the bottom right.", "Tap the cogwheel at the top right.", "Tap Account Status and look at the age group."],
        note: "Only an adult should confirm their own age here. Never pick a wrong age to unlock things; it removes the protection.",
        tip: "Discord's rules can vary a little by country, so a screen may look slightly different from this guide."
      },
      sv: {
        title: "Kolla Discords åldersgrupp",
        why: "Discord uppskattar vem som är tonåring (13 till 17 år) och slår då på extra skydd automatiskt. Om kontot hamnar i fel grupp gäller inte skyddet, så kolla det först.",
        desktop: ["Klicka på kugghjulet längst ned till vänster (User Settings).", "Klicka på Account Status.", "Titta på åldersgruppen. Ett tonårskonto ska visa teen. Står det unconfirmed gäller ändå de stränga grundinställningarna. Det är okej."],
        mobile: ["Tryck på din profilbild längst ned till höger.", "Tryck på kugghjulet uppe till höger.", "Tryck på Account Status och titta på åldersgruppen."],
        note: "Bara en vuxen ska bekräfta sin egen ålder här. Välj aldrig fel ålder för att låsa upp saker; då försvinner skyddet.",
        tip: "Discords regler kan skilja lite mellan länder, så en skärm kan se något annorlunda ut än i den här guiden."
      }
    },
    {
      id: "dms", kind: "step",
      src: [["Blocking & Privacy Settings", HC + "217916488-Blocking-Privacy-Settings"]],
      // https://support.discord.com/hc/en-us/articles/217916488 (desktop and mobile paths, "Direct messages" toggle)
      en: {
        title: "Turn off DMs from people in servers",
        why: "By default, anyone who shares a server with you can send you a private message. Most unwanted contact starts exactly like that, in a big server, then a DM. Switch it off, and people need to be your friend first.",
        desktop: ["Click the cogwheel at the bottom left.", "Click Content & Social.", "Find the Social permissions section.", "Switch off Direct messages.", "Discord asks if you want to apply it to all your existing servers. Choose yes."],
        mobile: ["Tap your profile picture at the bottom right, then the cogwheel at the top right.", "Tap Content & Social.", "Scroll to Server Settings and switch off Direct messages."],
        note: "You can still DM your friends. You can also allow DMs for one small server you trust, from the same screen, if you really need to.",
        tip: ""
      },
      sv: {
        title: "Stäng av DM från personer i servrar",
        why: "Som standard kan alla som är med i samma server som du skicka privata meddelanden till dig. Det är så det mesta oönskade kontaktandet börjar: i en stor server, sedan ett DM. Stänger du av det måste folk vara vänner med dig först.",
        desktop: ["Klicka på kugghjulet längst ned till vänster.", "Klicka på Content & Social.", "Hitta avsnittet Social permissions.", "Stäng av Direct messages.", "Discord frågar om du vill använda det på alla dina servrar. Välj ja."],
        mobile: ["Tryck på din profilbild längst ned till höger och sedan på kugghjulet uppe till höger.", "Tryck på Content & Social.", "Scrolla till Server Settings och stäng av Direct messages."],
        note: "Du kan fortfarande skriva DM till dina vänner. Du kan också tillåta DM för en liten server du litar på, från samma skärm, om du verkligen behöver det.",
        tip: ""
      }
    },
    {
      id: "friends", kind: "step",
      src: [["Blocking & Privacy Settings", HC + "217916488-Blocking-Privacy-Settings"]],
      // https://support.discord.com/hc/en-us/articles/217916488 section "On Friend Requests": Everyone / Friends of Friends / Server Members
      en: {
        title: "Limit who can send friend requests",
        why: "A friend request is the door to everything else. If strangers can't send one, they have a much harder time getting close. 'Friends of friends' still lets real classmates and gaming friends find you.",
        desktop: ["Click the cogwheel at the bottom left.", "Click Content & Social.", "Click Friend Requests.", "Turn off Everyone and Server Members. Leave Friends of Friends on."],
        mobile: ["Tap your profile picture at the bottom right, then the cogwheel at the top right.", "Tap Content & Social, then Friend Requests.", "Turn off Everyone and Server Members. Leave Friends of Friends on."],
        note: "If you turn off all three, nobody can send you a request at all. That is the safest, and you can still send requests yourself.",
        tip: "Even with this on, Discord shows an alert before you accept a request from someone you share no friends or small servers with. Read it."
      },
      sv: {
        title: "Begränsa vem som kan skicka vänförfrågningar",
        why: "En vänförfrågan är dörren till allt annat. Kan främlingar inte skicka en, får de det mycket svårare att komma nära. 'Friends of friends' låter ändå riktiga klasskompisar och spelkompisar hitta dig.",
        desktop: ["Klicka på kugghjulet längst ned till vänster.", "Klicka på Content & Social.", "Klicka på Friend Requests.", "Stäng av Everyone och Server Members. Låt Friends of Friends vara på."],
        mobile: ["Tryck på din profilbild längst ned till höger och sedan på kugghjulet uppe till höger.", "Tryck på Content & Social och sedan Friend Requests.", "Stäng av Everyone och Server Members. Låt Friends of Friends vara på."],
        note: "Stänger du av alla tre kan ingen skicka en förfrågan till dig alls. Det är säkrast, och du kan fortfarande skicka förfrågningar själv.",
        tip: "Även med det här på visar Discord en varning innan du accepterar en förfrågan från någon du inte har några gemensamma vänner eller små servrar med. Läs den."
      }
    },
    {
      id: "requests", kind: "step",
      src: [["Message Requests", HC + "7924992471191-Message-Requests"]],
      // https://support.discord.com/hc/en-us/articles/7924992471191 : on for teens/unconfirmed, only adults can turn off. Exact settings label differs between Discord articles ("Content & Social" vs "Messaging Permissions").
      en: {
        title: "Check that Message Requests is on",
        why: "Message requests put DMs from people who aren't your friends in a separate inbox, where you can look at them first. Images and links are hidden until you accept. Nothing lands in your normal chats from a stranger.",
        desktop: ["Click the cogwheel at the bottom left.", "Click Content & Social (in some versions this part is called Messaging Permissions).", "Find Message Requests. It should be on.", "To see your inbox later: Home, then the Message Requests folder (it only shows when something is waiting)."],
        mobile: ["Tap your profile picture at the bottom right, then the cogwheel at the top right.", "Tap Content & Social (or Messaging Permissions) and check that Message Requests is on.", "To see the inbox later: open Direct Messages and look for the Message Requests tab."],
        note: "For teens it is on automatically and can't be turned off. This step is just a check, and a chance to explain: you don't have to accept anyone.",
        tip: "Decline anything that feels off. You can also tap Block or Report from there."
      },
      sv: {
        title: "Kolla att Message Requests är på",
        why: "Message requests lägger DM från personer som inte är dina vänner i en separat inkorg, där du kan titta först. Bilder och länkar är dolda tills du accepterar. Inget från en främling hamnar bland dina vanliga chattar.",
        desktop: ["Klicka på kugghjulet längst ned till vänster.", "Klicka på Content & Social (i vissa versioner heter den här delen Messaging Permissions).", "Hitta Message Requests. Det ska vara på.", "För att se inkorgen senare: Home, sedan mappen Message Requests (den syns bara när något väntar)."],
        mobile: ["Tryck på din profilbild längst ned till höger och sedan på kugghjulet uppe till höger.", "Tryck på Content & Social (eller Messaging Permissions) och kolla att Message Requests är på.", "För att se inkorgen senare: öppna Direct Messages och leta efter fliken Message Requests."],
        note: "För tonåringar är det på automatiskt och går inte att stänga av. Det här steget är bara en koll, och en chans att förklara: du behöver inte acceptera någon.",
        tip: "Neka allt som känns konstigt. Du kan också trycka på Block eller Report därifrån."
      }
    },
    {
      id: "media", kind: "step",
      src: [["Discord Sensitive Content Filters", HC + "18210995019671-Discord-Sensitive-Content-Filters"]],
      // https://support.discord.com/hc/en-us/articles/18210995019671 (teen defaults: friends DMs blur, others' DMs block, servers blur; only an adult can set Show)
      en: {
        title: "Blur or block sensitive pictures",
        why: "Discord can spot pictures that may be sexual or violent and hide them before you see them. For teens this is on already: pictures from friends are blurred, from strangers blocked, in servers blurred. Nobody has to look at something that can't be unseen.",
        desktop: ["Click the cogwheel at the bottom left.", "Click Content & Social.", "Find Sensitive content filters (Mature Sexual Media and Graphic Media).", "For Direct messages from friends, Direct messages from others and Messages in server channels, check that they say Blur or Block. For others' DMs choose Block."],
        mobile: ["Tap your profile picture at the bottom right, then the cogwheel at the top right.", "Tap Content & Social.", "Under Sensitive content filters, check the same three settings."],
        note: "No filter is perfect. If something slips through, don't forward it: take a screenshot only if a grown-up says to, then tap Report Message and block the sender.",
        tip: "Teens can't choose Show. Only a confirmed adult can."
      },
      sv: {
        title: "Sudda eller blockera känsliga bilder",
        why: "Discord kan känna igen bilder som kan vara sexuella eller våldsamma och gömma dem innan du ser dem. För tonåringar är det redan på: bilder från vänner suddas, från främlingar blockeras, i servrar suddas de. Ingen ska behöva se något som inte går att glömma.",
        desktop: ["Klicka på kugghjulet längst ned till vänster.", "Klicka på Content & Social.", "Hitta Sensitive content filters (Mature Sexual Media och Graphic Media).", "För Direct messages from friends, Direct messages from others och Messages in server channels: kolla att det står Blur eller Block. För andras DM, välj Block."],
        mobile: ["Tryck på din profilbild längst ned till höger och sedan på kugghjulet uppe till höger.", "Tryck på Content & Social.", "Under Sensitive content filters: kolla samma tre inställningar."],
        note: "Inget filter är perfekt. Om något slinker igenom, skicka det inte vidare: ta skärmdump bara om en vuxen säger det, tryck sedan på Report Message och blockera avsändaren.",
        tip: "Tonåringar kan inte välja Show. Det kan bara en bekräftad vuxen."
      }
    },
    {
      id: "teendefaults", kind: "step",
      src: [["What Protections Do You Get in the Teen Age Group?", HC + "42178056096663-What-Protections-Do-You-Get-in-the-Teen-Age-Group"], ["Message Requests", HC + "7924992471191-Message-Requests"]],
      // https://support.discord.com/hc/en-us/articles/42178056096663 ; safety alert on first DM: .../7924992471191
      en: {
        title: "What Discord already does for teens",
        why: "Since 2025 Discord switches on a set of protections for accounts it thinks are teens. Knowing what they are means you can trust them without being blind to what they don't cover.",
        list: [
          "Pictures flagged as sensitive are blurred or blocked (step 5).",
          "Servers and channels marked 18+ are closed. Only a confirmed adult can open them.",
          "Message requests are on (step 4), and spam filtering applies to all DMs.",
          "Discord shows a warning before you accept a friend request from someone you share no friends or small servers with.",
          "Discord can show a safety alert on a first DM, with an easy way to block the sender.",
          "Your profile and activity are only visible to friends and members of small servers (under 200 members).",
          "Speaking on Stage channels needs a confirmed adult. Listening is fine."
        ],
        desktop: ["Open User Settings and look for Profile Privacy and Where I Share Activity. The safe choices are Friends & Small Servers Only, and Share in servers with 200 or fewer members."],
        mobile: ["Same settings, same names. Open Settings (profile picture, then cogwheel) and look for them there."],
        note: "These protections are a safety net, not a guarantee. The most important protection is still that you can tell a grown-up anything (see the last step).",
        tip: ""
      },
      sv: {
        title: "Vad Discord redan gör för tonåringar",
        why: "Sedan 2025 slår Discord på en uppsättning skydd för konton som bedöms vara tonåringar. Vet ni vad de är kan ni lita på dem utan att missa vad de inte täcker.",
        list: [
          "Bilder som flaggas som känsliga suddas eller blockeras (steg 5).",
          "Servrar och kanaler märkta 18+ är stängda. Bara en bekräftad vuxen kan öppna dem.",
          "Message requests är på (steg 4), och skräppostfiltret gäller alla DM.",
          "Discord visar en varning innan du accepterar en vänförfrågan från någon du inte har gemensamma vänner eller små servrar med.",
          "Discord kan visa en säkerhetsvarning vid ett första DM, med ett enkelt sätt att blockera avsändaren.",
          "Din profil och aktivitet syns bara för vänner och medlemmar i små servrar (under 200 medlemmar).",
          "Att tala på Stage-kanaler kräver en bekräftad vuxen. Att lyssna går bra."
        ],
        desktop: ["Öppna User Settings och leta efter Profile Privacy och Where I Share Activity. De säkra valen är Friends & Small Servers Only och Share in servers with 200 or fewer members."],
        mobile: ["Samma inställningar, samma namn. Öppna Settings (profilbild, sedan kugghjul) och leta efter dem där."],
        note: "De här skydden är ett nät, inte en garanti. Det viktigaste skyddet är fortfarande att du kan berätta vad som helst för en vuxen (se sista steget).",
        tip: ""
      }
    },
    {
      id: "family", kind: "step",
      src: [["Family Center for Teens", HC + "14155060633623-Family-Center-for-Teens"], ["Family Center for Parents and Guardians", HC + "14155043715735-Family-Center-for-Parents-and-Guardians"]],
      // https://support.discord.com/hc/en-us/articles/14155060633623 and .../14155043715735 (QR/link flow, activity list, no message content, up to three guardians)
      en: {
        title: "Link a parent in Family Center",
        why: "Family Center is Discord's own tool. It lets a parent see who the young person talks to and which servers they join, and it lets the parent manage a few settings. It never shows what the messages say. Both of you can see the same list.",
        desktop: [
          "Young person: click the cogwheel at the bottom left, then Account, then Family Center.",
          "Click My Family, then Show Code (a QR code) or Copy Link.",
          "Parent: scan the QR code with a phone, or open the link on a computer. No app is needed, the web works.",
          "Young person: accept the connection request that pops up. Done."
        ],
        mobile: [
          "Young person: tap your profile picture at the bottom right, then the cogwheel, then Family Center, then My Family, then Show Code or Copy Link.",
          "Parent (in the Discord app): tap your profile picture, then Settings, then Family Center, then My Family, and scan the code.",
          "Young person: accept the request."
        ],
        see: {
          canTitle: "What the parent can see (last 7 days)",
          can: ["New friends", "Who the young person messaged or called (names and pictures)", "Total call minutes", "Top five people and servers", "New servers and active servers", "Purchases and gifts received"],
          cannotTitle: "What the parent cannot see",
          cannot: ["What any message says, in servers or DMs", "Anything from before you linked", "Which channels, or what is said in calls"]
        },
        note: "After you link, the settings in steps 2, 3, 4 and 5 are managed by the parent and the young person can no longer change them alone. Up to three parents or guardians can link. The parent also needs to be in Discord's adult age group to change the message request setting.",
        tip: "Agree today what the parent will do with what they see: ask, not accuse."
      },
      sv: {
        title: "Koppla en förälder i Family Center",
        why: "Family Center är Discords eget verktyg. Det låter en förälder se vem den unga pratar med och vilka servrar hen går med i, och låter föräldern hantera några inställningar. Det visar aldrig vad meddelandena säger. Ni kan båda se samma lista.",
        desktop: [
          "Den unga: klicka på kugghjulet längst ned till vänster, sedan Account, sedan Family Center.",
          "Klicka på My Family, sedan Show Code (en QR-kod) eller Copy Link.",
          "Föräldern: skanna QR-koden med en telefon, eller öppna länken på en dator. Ingen app behövs, webben fungerar.",
          "Den unga: acceptera förfrågan som dyker upp. Klart."
        ],
        mobile: [
          "Den unga: tryck på din profilbild längst ned till höger, sedan kugghjulet, sedan Family Center, My Family och Show Code eller Copy Link.",
          "Föräldern (i Discord-appen): tryck på din profilbild, sedan Settings, Family Center, My Family och skanna koden.",
          "Den unga: acceptera förfrågan."
        ],
        see: {
          canTitle: "Det här kan föräldern se (senaste 7 dagarna)",
          can: ["Nya vänner", "Vem den unga skickat meddelande till eller ringt (namn och bilder)", "Totala samtalsminuter", "De fem vanligaste personerna och servrarna", "Nya och aktiva servrar", "Köp och mottagna gåvor"],
          cannotTitle: "Det här kan föräldern inte se",
          cannot: ["Vad något meddelande säger, i servrar eller DM", "Något från tiden före kopplingen", "Vilka kanaler, eller vad som sägs i samtal"]
        },
        note: "Efter kopplingen sköts inställningarna i steg 2, 3, 4 och 5 av föräldern, och den unga kan inte längre ändra dem själv. Upp till tre föräldrar eller vårdnadshavare kan kopplas. Föräldern behöver också vara i Discords vuxengrupp för att kunna ändra inställningen för message requests.",
        tip: "Bestäm redan idag vad föräldern ska göra med det hen ser: fråga, inte anklaga."
      }
    },
    {
      id: "guildward", kind: "step",
      en: {
        title: "Add the Guildward app",
        why: "Guildward is a free app you add to your own Discord account, not to a server. It gives the young person three quick checks they run themselves. All answers are private to whoever asked. Guildward stores no messages, no invites and no results.",
        install: "Add Guildward to your Discord account",
        desktop: [
          "Tap the button above and choose Add to My Apps (a user install, not a server).",
          "Check an invite link: in any chat type /check and paste the invite link.",
          "Check a person: right-click their name, then Apps, then Safety check.",
          "Check a message: right-click the message, then Apps, then Is this sketchy?"
        ],
        mobile: [
          "Tap the button above and choose Add to My Apps.",
          "Check an invite link: type /check and paste the link.",
          "Check a person: tap and hold their profile, or open it, then Apps, then Safety check.",
          "Check a message: long-press the message, then Apps, then Is this sketchy?"
        ],
        note: "Guildward gives a signal, not a verdict. A green result does not mean safe, and a red one does not mean guilty. If something feels wrong, talk to a grown-up.",
        tip: "The young person sees every answer. Guildward never reports anything to a parent behind their back."
      },
      sv: {
        title: "Lägg till Guildward-appen",
        why: "Guildward är en gratisapp du lägger till på ditt eget Discord-konto, inte på en server. Den ger den unga tre snabba kontroller som hen kör själv. Alla svar är privata för den som frågade. Guildward sparar inga meddelanden, inga inbjudningar och inga resultat.",
        install: "Lägg till Guildward på ditt Discord-konto",
        desktop: [
          "Tryck på knappen ovan och välj Add to My Apps (en användarinstallation, inte en server).",
          "Kolla en inbjudningslänk: skriv /check i valfri chatt och klistra in länken.",
          "Kolla en person: högerklicka på namnet, sedan Apps, sedan Safety check.",
          "Kolla ett meddelande: högerklicka på meddelandet, sedan Apps, sedan Is this sketchy?"
        ],
        mobile: [
          "Tryck på knappen ovan och välj Add to My Apps.",
          "Kolla en inbjudningslänk: skriv /check och klistra in länken.",
          "Kolla en person: tryck och håll på profilen, eller öppna den, sedan Apps, sedan Safety check.",
          "Kolla ett meddelande: håll in på meddelandet, sedan Apps, sedan Is this sketchy?"
        ],
        note: "Guildward ger en signal, inte en dom. Grönt betyder inte säkert och rött betyder inte skyldig. Känns något fel: prata med en vuxen.",
        tip: "Den unga ser varje svar. Guildward rapporterar aldrig något till en förälder bakom ryggen."
      }
    },
    {
      id: "talk", kind: "talk",
      en: {
        title: "Talk about it",
        lead: "Settings help, but the strongest protection is a kid who knows they can say anything without getting in trouble. Use these as starting points, not a script.",
        tipsTitle: "Things a parent can say",
        tips: [
          "\"If anyone online ever makes you feel weird, you can tell me. You will never get in trouble for telling me.\"",
          "\"Anyone can pretend to be 14. How would you know if someone was older?\"",
          "\"A real friend doesn't ask you to keep secrets from your family.\"",
          "\"If someone asks you to move to another app, show me first.\"",
          "\"You don't owe anyone a picture, ever, even if they say they'll be sad or angry.\"",
          "\"If you have already done something you regret, it's still okay to tell me. It's never your fault.\""
        ],
        kidTitle: "Things a kid can do",
        kid: [
          "Say no and block. You don't need a reason.",
          "Tell a grown-up you trust, even if you feel embarrassed.",
          "Use the three Guildward checks when something feels off."
        ],
        groomTitle: "What grooming can look like",
        groomLead: "It usually goes step by step, over days or weeks. Any single step can be harmless; the pattern is what matters.",
        stages: [
          ["Trust", "Lots of compliments and attention. They seem to understand you better than anyone."],
          ["Questions about age and family", "How old are you? Are your parents home? Do you have a boyfriend or girlfriend?"],
          ["Moving to another app", "Let's talk on Snapchat or another place instead, where it's harder for others to see."],
          ["Secrets", "Don't tell anyone about us. Your parents won't understand."],
          ["Photos and pressure", "Asking for pictures, then using them: 'if you don't, I'll show everyone'."],
          ["Meeting", "Wanting to meet in real life, often alone."]
        ],
        helpTitle: "Where to get help in Sweden",
        help: [
          ["Bris (children and teens)", "Call or text 116 111, every day including nights, free, and you don't have to say who you are. Chat on bris.se.", "https://www.bris.se/", "bris.se"],
          ["ECPAT Hotline", "Report child sexual abuse material or exploitation of children, anonymously if you want.", "https://ecpat.se/hotline/", "ecpat.se/hotline"],
          ["Polisen", "114 14 for the police in general. 112 in an emergency or if a crime is happening now.", "https://polisen.se/", "polisen.se"],
          ["Report to Discord", "Press and hold (or right-click) the message, choose Report Message. Parents can use Discord's form to report a message link.", HC + "360000291932-How-to-Contact-Discord-Safety-for-Parents-and-Guardians", "Discord's report guide"]
        ],
        closing: "You did something good today. Come back and check in every few months; Discord changes, and so do kids."
      },
      sv: {
        title: "Prata om det",
        lead: "Inställningar hjälper, men det starkaste skyddet är ett barn som vet att hen kan säga vad som helst utan att få skäll. Använd det här som utgångspunkter, inte som manus.",
        tipsTitle: "Saker en förälder kan säga",
        tips: [
          "\"Om någon online någonsin får dig att känna dig konstig kan du berätta för mig. Du får aldrig skäll för att du berättar.\"",
          "\"Vem som helst kan låtsas vara 14. Hur skulle du veta om någon var äldre?\"",
          "\"En riktig kompis ber dig inte hålla hemligheter för din familj.\"",
          "\"Om någon ber dig flytta till en annan app, visa mig först.\"",
          "\"Du är aldrig skyldig någon en bild, även om hen säger sig bli ledsen eller arg.\"",
          "\"Har du redan gjort något du ångrar går det ändå bra att berätta. Det är aldrig ditt fel.\""
        ],
        kidTitle: "Saker du som ung kan göra",
        kid: [
          "Säg nej och blockera. Du behöver ingen anledning.",
          "Berätta för en vuxen du litar på, även om det känns pinsamt.",
          "Använd Guildwards tre kontroller när något känns fel."
        ],
        groomTitle: "Så kan grooming se ut",
        groomLead: "Det går oftast stegvis, under dagar eller veckor. Ett enskilt steg kan vara oskyldigt; det är mönstret som räknas.",
        stages: [
          ["Förtroende", "Många komplimanger och mycket uppmärksamhet. Personen verkar förstå dig bättre än någon annan."],
          ["Frågor om ålder och familj", "Hur gammal är du? Är dina föräldrar hemma? Har du pojk- eller flickvän?"],
          ["Flytt till en annan app", "Vi kan prata på Snapchat eller någon annan plats i stället, där det är svårare för andra att se."],
          ["Hemligheter", "Berätta inte för någon om oss. Dina föräldrar skulle inte förstå."],
          ["Bilder och press", "Ber om bilder och använder dem sedan: 'om du inte gör det visar jag alla'."],
          ["Träff", "Vill ses i verkliga livet, ofta ensamma."]
        ],
        helpTitle: "Var du får hjälp i Sverige",
        help: [
          ["Bris (barn och unga)", "Ring eller sms:a 116 111, varje dag även på natten, gratis, och du behöver inte säga vem du är. Chatta på bris.se.", "https://www.bris.se/", "bris.se"],
          ["ECPAT Hotline", "Anmäl sexuella övergrepp mot barn eller sexuell exploatering av barn, anonymt om du vill.", "https://ecpat.se/hotline/", "ecpat.se/hotline"],
          ["Polisen", "114 14 till polisen i allmänhet. 112 vid nödläge eller om ett brott pågår just nu.", "https://polisen.se/", "polisen.se"],
          ["Anmäl till Discord", "Håll in på (eller högerklicka på) meddelandet och välj Report Message. Föräldrar kan använda Discords formulär med en meddelandelänk.", HC + "360000291932-How-to-Contact-Discord-Safety-for-Parents-and-Guardians", "Discords rapportguide"]
        ],
        closing: "Ni gjorde något bra idag. Kom tillbaka och kolla var tredje månad ungefär; Discord ändras, och det gör barn också."
      }
    }
  ];

  var INSTALL_HREF = "https://discord.com/oauth2/authorize?client_id=1568659844003668059&integration_type=1&scope=applications.commands";
  var app = document.getElementById("app");
  var lang = "en", idx = 0, done = {};

  function store(get, k, v) {
    try { return get ? window.localStorage.getItem(k) : window.localStorage.setItem(k, v); } catch (e) { return null; }
  }
  function initLang() {
    var saved = store(true, "gw-lang");
    if (saved === "sv" || saved === "en") return saved;
    var nav = (navigator.language || "en").toLowerCase();
    return nav.indexOf("sv") === 0 ? "sv" : "en";
  }
  function loadDone() {
    try { done = JSON.parse(store(true, "gw-done") || "{}") || {}; } catch (e) { done = {}; }
  }

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function ol(items) { return '<ol class="how">' + items.map(function (i) { return "<li>" + esc(i) + "</li>"; }).join("") + "</ol>"; }
  function ul(items, cls) { return '<ul class="' + (cls || "plain") + '">' + items.map(function (i) { return "<li>" + esc(i) + "</li>"; }).join("") + "</ul>"; }

  function renderNav() {
    var t = UI[lang], total = STEPS.length - 1; // welcome has no number
    var html = '<ol class="dots">';
    STEPS.forEach(function (s, i) {
      var label = i === 0 ? (lang === "sv" ? "Start" : "Start") : String(i);
      var cur = i === idx ? ' aria-current="step"' : "";
      var isDone = done[s.id] ? " is-done" : "";
      html += '<li><button type="button" class="dot' + isDone + '" data-go="' + i + '"' + cur +
        ' aria-label="' + esc(s[lang].title) + (done[s.id] ? " (" + (lang === "sv" ? "klar" : "done") + ")" : "") + '">' + label + "</button></li>";
    });
    html += "</ol>";
    var n = Math.min(idx, total);
    var pct = Math.round((idx / (STEPS.length - 1)) * 100);
    return '<div class="progress"><p class="progress-text" id="ptext">' + (idx === 0 ? t.ticked(countDone(), total) : t.progress(n, total)) + '</p>' +
      '<div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + pct + '" aria-labelledby="ptext"><span data-w="' + pct + '"></span></div>' +
      '<nav aria-label="' + esc(t.stepsNav) + '">' + html + "</nav></div>";
  }
  function countDone() { return STEPS.filter(function (s) { return s.kind === "step" && done[s.id]; }).length; }

  function renderStep() {
    var s = STEPS[idx], c = s[lang], t = UI[lang], h = "";
    h += renderNav();
    h += '<article class="card" aria-labelledby="stitle">';
    h += '<h2 id="stitle" tabindex="-1">' + (s.kind === "step" ? '<span class="num" aria-hidden="true">' + idx + "</span>" : "") + esc(c.title) + "</h2>";

    if (s.kind === "intro") {
      h += '<p class="lead">' + esc(c.lead) + "</p>" + ul(c.points, "ticks") + '<p class="muted">' + esc(c.who) + "</p>";
    } else if (s.kind === "talk") {
      h += '<p class="lead">' + esc(c.lead) + "</p>";
      h += "<h3>" + esc(c.tipsTitle) + "</h3>" + ul(c.tips, "quotes");
      h += "<h3>" + esc(c.kidTitle) + "</h3>" + ul(c.kid, "ticks");
      h += "<h3>" + esc(c.groomTitle) + "</h3><p>" + esc(c.groomLead) + '</p><ol class="stages">' +
        c.stages.map(function (x) { return "<li><strong>" + esc(x[0]) + "</strong><span>" + esc(x[1]) + "</span></li>"; }).join("") + "</ol>";
      h += "<h3>" + esc(c.helpTitle) + '</h3><ul class="help">' +
        c.help.map(function (x) { return "<li><strong>" + esc(x[0]) + '</strong><span>' + esc(x[1]) + '</span> <a href="' + esc(x[2]) + '" target="_blank" rel="noopener noreferrer">' + esc(x[3]) + "</a></li>"; }).join("") + "</ul>";
      h += '<p class="closing">' + esc(c.closing) + "</p>";
    } else {
      h += '<p class="why"><span class="tag">' + esc(t.why) + "</span> " + esc(c.why) + "</p>";
      if (c.list) h += ul(c.list, "ticks");
      if (c.install) h += '<p><a class="btn primary" href="' + INSTALL_HREF + '" id="install">' + esc(c.install) + "</a></p>";
      h += '<div class="paths"><section><h3>' + esc(t.desktop) + "</h3>" + ol(c.desktop) + "</section><section><h3>" + esc(t.mobile) + "</h3>" + ol(c.mobile) + "</section></div>";
      if (c.see) {
        h += '<div class="see"><section><h3>' + esc(c.see.canTitle) + "</h3>" + ul(c.see.can, "ticks") + "</section><section><h3>" + esc(c.see.cannotTitle) + "</h3>" + ul(c.see.cannot, "crosses") + "</section></div>";
      }
      if (c.note) h += '<p class="note">' + esc(c.note) + "</p>";
      if (c.tip) h += '<p class="muted">' + esc(c.tip) + "</p>";
      h += '<label class="check"><input type="checkbox" id="donebox"' + (done[s.id] ? " checked" : "") + "><span>" + esc(t.done) + "</span></label>";
      if (s.src) {
        h += '<p class="src">' + esc(t.source) + ": " + s.src.map(function (x) { return '<a href="' + esc(x[1]) + '" target="_blank" rel="noopener noreferrer">' + esc(x[0]) + "</a>"; }).join(" · ") + "</p>";
      }
    }
    h += "</article>";

    var last = idx === STEPS.length - 1;
    h += '<div class="actions">';
    h += idx > 0 ? '<button type="button" class="btn" id="back">' + esc(t.back) + "</button>" : "<span></span>";
    h += last ? '<button type="button" class="btn" id="restart">' + esc(t.restart) + "</button>"
      : '<button type="button" class="btn primary" id="next">' + esc(idx === 0 ? t.start : t.next) + "</button>";
    h += "</div>";
    app.innerHTML = h;
    var bar = app.querySelector(".bar span");
    if (bar) bar.style.width = bar.getAttribute("data-w") + "%";
  }

  function show(i, focus) {
    idx = Math.max(0, Math.min(STEPS.length - 1, i));
    renderStep();
    if (focus) {
      var h = document.getElementById("stitle");
      if (h) h.focus({ preventScroll: true });
      window.scrollTo(0, 0);
    }
  }

  function applyLang(l, rerender) {
    lang = l;
    document.documentElement.lang = l;
    var t = UI[l];
    document.querySelectorAll("[data-t]").forEach(function (el) { el.textContent = t[el.getAttribute("data-t")]; });
    document.querySelectorAll("[data-lang]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-lang") === l)); });
    document.title = "Guildward: " + (l === "sv" ? "låsningsguide för Discord" : "Discord lockdown wizard");
    if (rerender) renderStep();
  }

  document.addEventListener("click", function (e) {
    var el = e.target.closest("button, a");
    if (!el) return;
    if (el.id === "next") show(idx + 1, true);
    else if (el.id === "back") show(idx - 1, true);
    else if (el.id === "restart") show(0, true);
    else if (el.hasAttribute("data-go")) show(parseInt(el.getAttribute("data-go"), 10), true);
    else if (el.hasAttribute("data-lang")) { store(false, "gw-lang", el.getAttribute("data-lang")); applyLang(el.getAttribute("data-lang"), true); }
  });
  document.addEventListener("change", function (e) {
    if (e.target.id !== "donebox") return;
    done[STEPS[idx].id] = e.target.checked;
    store(false, "gw-done", JSON.stringify(done));
    var dot = document.querySelector('.dot[data-go="' + idx + '"]');
    if (dot) dot.classList.toggle("is-done", e.target.checked);
  });

  loadDone();
  applyLang(initLang(), false);
  show(0, false);
})();
