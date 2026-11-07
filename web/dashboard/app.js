/* Guildward Guard dashboard. Vanilla JS, no build step, no external requests.
   Contract: docs/GUARD_API.md. Every API string is escaped by the html`` helper. */
(function () {
  "use strict";

  // ===================================================================== i18n (chrome only)
  var I18N = {
    en: {
      skip: "Skip to content", brandSub: "Guard", nav: "Dashboard", server: "Server",
      overview: "Overview", alerts: "Alerts", members: "Members", settings: "Settings", report: "Report",
      owner: "Bot owner", logout: "Sign out", theme: "Theme", dark: "Dark", light: "Light", language: "Language",
      demo: "Demo", loading: "Loading", retry: "Try again", back: "Back",
      signinTitle: "Sign in to Guard", signinBody: "Run {cmd} in your server to get a private sign-in link. Links expire after a few minutes.",
      signinDemo: "Explore the demo instead", signedOut: "You are signed out.",
      errTitle: "Something went wrong", errNotFound: "This page does not exist.", errForbidden: "You don't have access to this.",
      errNetwork: "Guard didn't answer. Check that the bot is running.", noGuilds: "Guard isn't in any server you manage yet.",
      // levels / misc
      lvl_green: "Low", lvl_yellow: "Elevated", lvl_red: "High", riskScore: "Risk score {n} of 100",
      sev_high: "High", sev_medium: "Medium", sev_low: "Low",
      mode_observe: "Observe", mode_protect: "Protect",
      // overview
      ovMembers: "{n} members", ovMode: "{mode} mode", ovAlertsTo: "Alerts to {ch}", ovSince: "Guard since {d}",
      printable: "Printable report", permTitle: "Guard is missing permissions",
      permBody: "Some protections can't work until Guard's role has: {list}. Update the role in Server Settings → Roles.",
      health: "Server health", grade: "Grade", healthReasons: "What drives the score",
      situation: "Situation", keyFigures: "Key figures", last7: "last 7 days",
      k_members: "Members", k_minors_est: "Under 18 (est.)", k_at_risk: "At risk", k_red: "Red", k_open_alerts: "Open alerts",
      k_flagged_7d: "Flagged messages", k_messages_7d: "Messages", k_joins_7d: "Joins", k_actions_7d: "Mod actions",
      k_median_response_min: "Median response", minutes: "{n} min",
      recs: "Recommendations", fix: "Fix", fixing: "Fixing", noRecs: "No recommendations right now. Guard will add one when something needs attention.",
      audit: "Safety audit", auditOk: "OK", auditFail: "Needs work", auditPassed: "{n} of {m} checks pass",
      activity: "Last 30 days", s_messages: "Messages", s_flagged: "Flagged messages", s_joins: "Joins", s_alerts: "Alerts",
      s_pocket_checks: "Pocket checks", chartTotal: "{n} total", chartPeak: "peak {n}",
      chartAria: "{label}, last 30 days. Total {total}, peak {peak} on {day}. Use the arrow keys to read each day.",
      dataTable: "Show the numbers", day: "Day",
      topRisks: "Highest-risk members", seeAll: "See all", recentAlerts: "Recent alerts", openQueue: "Open queue",
      // alerts
      alertsTitle: "Alert queue", f_open: "Open", f_all: "All", noAlertsOpen: "No open alerts. When Guard flags something it lands here and in your alert channel.",
      noAlerts: "No alerts yet.", jump: "Open in Discord", signalsN: "{n} signals", toTarget: "to", by: "by",
      st_open: "Open", st_resolved: "Resolved", st_false_positive: "False positive",
      resolvedBy: "{status} by {who}", actionWas: "Action: {a}",
      k_message: "Message", k_member: "Member", k_raid: "Raid", k_report: "Report", k_network: "Safety Network", k_join: "Join",
      a_resolve: "Resolve", a_false_positive: "False positive", a_timeout: "Time out", a_kick: "Kick", a_ban: "Ban",
      a_delete: "Delete message", a_watch: "Watch", a_trust: "Trust", a_clear: "Clear flags",
      done: "Done.",
      cKickTitle: "Kick {name}?", cKickBody: "They are removed from the server and can rejoin with an invite.",
      cBanTitle: "Ban {name}?", cBanBody: "They are removed and can't rejoin. If Safety Network sharing is on, other Guard servers are warned.",
      cLeaveTitle: "Leave {name}?", cLeaveBody: "Guard leaves this server and stops protecting it. An admin has to invite it again.",
      cClearTitle: "Clear the network flag for {name}?", cClearBody: "Guard servers will stop being warned about this account.",
      cancel: "Cancel",
      // members
      membersTitle: "Members", mf_all: "All", mf_at_risk: "At risk", mf_minors: "Under 18", mf_watch: "Watch list", mf_new: "New",
      search: "Search members", searchPh: "Name or @handle", sortBy: "Sort", so_risk: "Risk", so_recent: "Recently joined", so_name: "Name",
      col_member: "Member", col_risk: "Risk", col_trend: "7 days", col_age: "Age", col_joined: "Joined", col_seen: "Last seen", col_signal: "Top signal",
      showing: "Showing {n} of {m}", noMembers: "No members match. Try another filter or search.",
      ageYears: "{n} y", acctDays: "account {n} d", trendUp: "Up {n} points this week", trendDown: "Down {n} points this week", trendFlat: "No change this week",
      fl_new_account: "New account", fl_no_avatar: "No avatar", fl_reported: "Reported", fl_network: "Safety Network", fl_watch: "Watched",
      fl_trusted: "Trusted", fl_minor: "Under 18", fl_adult_contacting_minors: "Adult contacting minors", fl_escalating: "Escalating",
      fl_raid: "Raid", fl_quarantined: "Quarantined",
      ms_none: "No status", ms_watch: "Watched", ms_trusted: "Trusted", ms_actioned: "Actioned", ms_left: "Left",
      // person
      verdict: "Verdict", summary: "Summary", prediction: "Prediction", stats: "Activity", contacts: "Contacts", timeline: "Timeline",
      tr_rising: "Rising", tr_stable: "Stable", tr_falling: "Falling", es_none: "No escalation expected", es_possible: "Escalation possible", es_likely: "Escalation likely",
      st_messages: "Messages", st_flagged: "Flagged", st_distinct_targets: "People contacted", st_minor_targets: "Minors contacted",
      st_reports: "Reports", st_mod_actions: "Mod actions", st_network_flags: "Network flags",
      col_messages: "Messages", col_stages: "Grooming stages", col_last: "Last contact", noStages: "None seen",
      noContacts: "No contacts recorded.", noTimeline: "Nothing recorded yet.",
      tk_join: "Joined", tk_leave: "Left", tk_signal: "Signal", tk_report: "Report", tk_action: "Action", tk_alert: "Alert", tk_name_change: "Name change",
      pAccount: "Account created {d}", pJoined: "Joined {d}", pInvite: "Invite {c}", pLeft: "Left {d}", pRoles: "Roles", pSelfAge: "Says age {n}",
      actions: "Actions", memberActions: "Member actions", reassure: "reduces risk",
      // settings
      settingsTitle: "Settings", save: "Save changes", saving: "Saving", reset: "Discard", unsaved: "Unsaved changes", saved: "Settings saved.", noChanges: "No changes to save.",
      g_mode: "Mode", g_alerts: "Alerts", g_auto: "Automatic actions", g_joins: "Joins and raids", g_minors: "Minors", g_network: "Safety Network", g_data: "Data and language",
      mode_observe_d: "Guard only posts alerts. Moderators decide everything.",
      mode_protect_d: "Guard also acts on its own: deletes red messages aimed at minors and times out members who turn red, pending review.",
      set_alert_channel_id: "Alert channel", set_alert_min_level: "Post alerts from", set_ping_role_id: "Role to ping on red alerts",
      set_quote_in_alerts: "Quote the flagged text in alerts", set_quote_in_alerts_d: "Shown in Discord only. Guard never stores message text.",
      set_auto_delete: "Delete red messages aimed at minors", set_auto_timeout: "Time out members who turn red (1 hour, pending review)",
      set_warn_targets: "Send a safety tip to the member who received a red message", set_auto_d: "Only in Protect mode.",
      set_raid_protection: "Detect raids (join bursts)", set_raid_protection_d: "In Protect mode Guard also quarantines or kicks raid accounts.",
      set_quarantine_new_accounts: "Quarantine risky new accounts", set_quarantine_role_id: "Quarantine role",
      set_minor_role_ids: "Roles that mean under 18", set_minor_role_ids_d: "Roles with names like \"under 13\" or \"13-17\" are detected automatically too.",
      set_network_share: "Share child-safety bans with other Guard servers and receive their warnings",
      set_retention_days: "Keep data for", days: "days", set_lang: "Language of alerts in Discord",
      none: "None", lvlFrom_yellow: "Yellow and red", lvlFrom_red: "Red only",
      // report
      reportTitle: "Safety report", reportFor: "Generated {d}", print: "Print or save as PDF", reportBack: "Back to overview",
      // owner
      ownerTitle: "Bot owner", system: "System", online: "Online", offline: "Offline", pocket: "Pocket app", guard: "Guard",
      latency: "{n} ms", uptime: "Uptime", version: "Version", rules: "Rules", database: "Database", events: "Events per minute",
      totals: "Totals", t_guilds: "Servers", t_members: "Members", t_alerts_open: "Open alerts", t_alerts_7d: "Alerts (7 days)",
      t_flagged_7d: "Flagged (7 days)", t_network_flags: "Network flags", t_pocket_checks_7d: "Pocket checks (7 days)",
      pocketBreak: "Pocket checks by result, last 30 days", pk_server: "Server checks", pk_person: "Person checks", pk_message: "Message checks",
      guilds: "Servers", col_server: "Server", col_mode: "Mode", col_open: "Open", col_7d: "Alerts 7 d", col_since: "Added",
      leave: "Leave", left: "Guard left the server.",
      quality: "Signal quality", col_signalq: "Signal", col_fired: "Fired (30 d)", col_fp: "False positives", col_fprate: "FP rate",
      networkTitle: "Safety Network", col_user: "Account", col_guilds: "Servers", col_reasons: "Reasons", col_first: "First flagged",
      clear: "Clear", cleared: "Network flag cleared.", noNetwork: "No accounts are flagged in the Safety Network.",
      sortAsc: "sorted ascending", sortDesc: "sorted descending"
    },
    sv: {
      skip: "Hoppa till innehållet", brandSub: "Guard", nav: "Kontrollpanel", server: "Server",
      overview: "Översikt", alerts: "Larm", members: "Medlemmar", settings: "Inställningar", report: "Rapport",
      owner: "Botägare", logout: "Logga ut", theme: "Tema", dark: "Mörkt", light: "Ljust", language: "Språk",
      demo: "Demo", loading: "Laddar", retry: "Försök igen", back: "Tillbaka",
      signinTitle: "Logga in i Guard", signinBody: "Kör {cmd} i din server för att få en privat inloggningslänk. Länkar slutar gälla efter några minuter.",
      signinDemo: "Utforska demon i stället", signedOut: "Du är utloggad.",
      errTitle: "Något gick fel", errNotFound: "Sidan finns inte.", errForbidden: "Du har inte åtkomst till det här.",
      errNetwork: "Guard svarade inte. Kontrollera att boten körs.", noGuilds: "Guard finns inte i någon server du hanterar ännu.",
      lvl_green: "Låg", lvl_yellow: "Förhöjd", lvl_red: "Hög", riskScore: "Riskpoäng {n} av 100",
      sev_high: "Hög", sev_medium: "Medel", sev_low: "Låg",
      mode_observe: "Observera", mode_protect: "Skydda",
      ovMembers: "{n} medlemmar", ovMode: "Läge: {mode}", ovAlertsTo: "Larm till {ch}", ovSince: "Guard sedan {d}",
      printable: "Utskriftsvänlig rapport", permTitle: "Guard saknar behörigheter",
      permBody: "Vissa skydd fungerar inte förrän Guards roll har: {list}. Ändra rollen under Serverinställningar → Roller.",
      health: "Serverns hälsa", grade: "Betyg", healthReasons: "Det här påverkar poängen",
      situation: "Läget", keyFigures: "Nyckeltal", last7: "senaste 7 dagarna",
      k_members: "Medlemmar", k_minors_est: "Under 18 (uppsk.)", k_at_risk: "I riskzonen", k_red: "Röda", k_open_alerts: "Öppna larm",
      k_flagged_7d: "Flaggade meddelanden", k_messages_7d: "Meddelanden", k_joins_7d: "Nya medlemmar", k_actions_7d: "Moderatoråtgärder",
      k_median_response_min: "Mediansvarstid", minutes: "{n} min",
      recs: "Rekommendationer", fix: "Åtgärda", fixing: "Åtgärdar", noRecs: "Inga rekommendationer just nu. Guard lägger till en när något behöver åtgärdas.",
      audit: "Säkerhetsgranskning", auditOk: "OK", auditFail: "Behöver åtgärdas", auditPassed: "{n} av {m} kontroller godkända",
      activity: "Senaste 30 dagarna", s_messages: "Meddelanden", s_flagged: "Flaggade meddelanden", s_joins: "Nya medlemmar", s_alerts: "Larm",
      s_pocket_checks: "Pocket-kontroller", chartTotal: "{n} totalt", chartPeak: "topp {n}",
      chartAria: "{label}, senaste 30 dagarna. Totalt {total}, topp {peak} den {day}. Använd piltangenterna för att läsa varje dag.",
      dataTable: "Visa siffrorna", day: "Dag",
      topRisks: "Medlemmar med högst risk", seeAll: "Visa alla", recentAlerts: "Senaste larmen", openQueue: "Öppna kön",
      alertsTitle: "Larmkö", f_open: "Öppna", f_all: "Alla", noAlertsOpen: "Inga öppna larm. När Guard flaggar något hamnar det här och i din larmkanal.",
      noAlerts: "Inga larm ännu.", jump: "Öppna i Discord", signalsN: "{n} signaler", toTarget: "till", by: "av",
      st_open: "Öppet", st_resolved: "Löst", st_false_positive: "Falsklarm",
      resolvedBy: "{status} av {who}", actionWas: "Åtgärd: {a}",
      k_message: "Meddelande", k_member: "Medlem", k_raid: "Räd", k_report: "Anmälan", k_network: "Säkerhetsnätverk", k_join: "Anslutning",
      a_resolve: "Markera löst", a_false_positive: "Falsklarm", a_timeout: "Timeout", a_kick: "Sparka ut", a_ban: "Bannlys",
      a_delete: "Radera meddelandet", a_watch: "Bevaka", a_trust: "Lita på", a_clear: "Rensa flaggor",
      done: "Klart.",
      cKickTitle: "Sparka ut {name}?", cKickBody: "Personen tas bort från servern och kan gå med igen via en inbjudan.",
      cBanTitle: "Bannlys {name}?", cBanBody: "Personen tas bort och kan inte gå med igen. Om delning i säkerhetsnätverket är på varnas andra Guard-servrar.",
      cLeaveTitle: "Lämna {name}?", cLeaveBody: "Guard lämnar servern och slutar skydda den. En admin måste bjuda in den igen.",
      cClearTitle: "Rensa nätverksflaggan för {name}?", cClearBody: "Guard-servrar slutar varnas om det här kontot.",
      cancel: "Avbryt",
      membersTitle: "Medlemmar", mf_all: "Alla", mf_at_risk: "I riskzonen", mf_minors: "Under 18", mf_watch: "Bevakade", mf_new: "Nya",
      search: "Sök medlemmar", searchPh: "Namn eller @användare", sortBy: "Sortera", so_risk: "Risk", so_recent: "Senast anslutna", so_name: "Namn",
      col_member: "Medlem", col_risk: "Risk", col_trend: "7 dagar", col_age: "Ålder", col_joined: "Gick med", col_seen: "Senast sedd", col_signal: "Starkaste signal",
      showing: "Visar {n} av {m}", noMembers: "Inga medlemmar matchar. Prova ett annat filter eller en annan sökning.",
      ageYears: "{n} år", acctDays: "konto {n} d", trendUp: "Upp {n} poäng i veckan", trendDown: "Ner {n} poäng i veckan", trendFlat: "Ingen förändring i veckan",
      fl_new_account: "Nytt konto", fl_no_avatar: "Ingen profilbild", fl_reported: "Anmäld", fl_network: "Säkerhetsnätverk", fl_watch: "Bevakad",
      fl_trusted: "Betrodd", fl_minor: "Under 18", fl_adult_contacting_minors: "Vuxen som kontaktar minderåriga", fl_escalating: "Eskalerar",
      fl_raid: "Räd", fl_quarantined: "I karantän",
      ms_none: "Ingen status", ms_watch: "Bevakad", ms_trusted: "Betrodd", ms_actioned: "Åtgärdad", ms_left: "Har lämnat",
      verdict: "Bedömning", summary: "Sammanfattning", prediction: "Prognos", stats: "Aktivitet", contacts: "Kontakter", timeline: "Tidslinje",
      tr_rising: "Stigande", tr_stable: "Stabil", tr_falling: "Sjunkande", es_none: "Ingen eskalering väntas", es_possible: "Eskalering möjlig", es_likely: "Eskalering trolig",
      st_messages: "Meddelanden", st_flagged: "Flaggade", st_distinct_targets: "Kontaktade personer", st_minor_targets: "Kontaktade minderåriga",
      st_reports: "Anmälningar", st_mod_actions: "Moderatoråtgärder", st_network_flags: "Nätverksflaggor",
      col_messages: "Meddelanden", col_stages: "Groomingsteg", col_last: "Senaste kontakt", noStages: "Inga sedda",
      noContacts: "Inga kontakter registrerade.", noTimeline: "Inget registrerat ännu.",
      tk_join: "Gick med", tk_leave: "Lämnade", tk_signal: "Signal", tk_report: "Anmälan", tk_action: "Åtgärd", tk_alert: "Larm", tk_name_change: "Namnbyte",
      pAccount: "Konto skapat {d}", pJoined: "Gick med {d}", pInvite: "Inbjudan {c}", pLeft: "Lämnade {d}", pRoles: "Roller", pSelfAge: "Säger sig vara {n}",
      actions: "Åtgärder", memberActions: "Åtgärder för medlemmen", reassure: "sänker risken",
      settingsTitle: "Inställningar", save: "Spara ändringar", saving: "Sparar", reset: "Ångra", unsaved: "Osparade ändringar", saved: "Inställningarna sparades.", noChanges: "Inga ändringar att spara.",
      g_mode: "Läge", g_alerts: "Larm", g_auto: "Automatiska åtgärder", g_joins: "Anslutningar och räder", g_minors: "Minderåriga", g_network: "Säkerhetsnätverk", g_data: "Data och språk",
      mode_observe_d: "Guard skickar bara larm. Moderatorerna bestämmer allt.",
      mode_protect_d: "Guard agerar även själv: raderar röda meddelanden till minderåriga och ger timeout till medlemmar som blir röda, i väntan på granskning.",
      set_alert_channel_id: "Larmkanal", set_alert_min_level: "Skicka larm från", set_ping_role_id: "Roll att pinga vid röda larm",
      set_quote_in_alerts: "Citera den flaggade texten i larm", set_quote_in_alerts_d: "Visas bara i Discord. Guard sparar aldrig meddelandetext.",
      set_auto_delete: "Radera röda meddelanden till minderåriga", set_auto_timeout: "Ge timeout till medlemmar som blir röda (1 timme, i väntan på granskning)",
      set_warn_targets: "Skicka ett säkerhetstips till den som fick ett rött meddelande", set_auto_d: "Bara i läget Skydda.",
      set_raid_protection: "Upptäck räder (många anslutningar på kort tid)", set_raid_protection_d: "I läget Skydda sätter Guard även rädkonton i karantän eller sparkar ut dem.",
      set_quarantine_new_accounts: "Sätt riskabla nya konton i karantän", set_quarantine_role_id: "Karantänroll",
      set_minor_role_ids: "Roller som betyder under 18", set_minor_role_ids_d: "Roller med namn som \"under 13\" eller \"13-17\" upptäcks också automatiskt.",
      set_network_share: "Dela bannlysningar för barnsäkerhet med andra Guard-servrar och ta emot deras varningar",
      set_retention_days: "Spara data i", days: "dagar", set_lang: "Språk för larm i Discord",
      none: "Ingen", lvlFrom_yellow: "Gul och röd", lvlFrom_red: "Bara röd",
      reportTitle: "Säkerhetsrapport", reportFor: "Skapad {d}", print: "Skriv ut eller spara som PDF", reportBack: "Tillbaka till översikten",
      ownerTitle: "Botägare", system: "System", online: "Online", offline: "Offline", pocket: "Pocket-appen", guard: "Guard",
      latency: "{n} ms", uptime: "Drifttid", version: "Version", rules: "Regler", database: "Databas", events: "Händelser per minut",
      totals: "Totalt", t_guilds: "Servrar", t_members: "Medlemmar", t_alerts_open: "Öppna larm", t_alerts_7d: "Larm (7 dagar)",
      t_flagged_7d: "Flaggade (7 dagar)", t_network_flags: "Nätverksflaggor", t_pocket_checks_7d: "Pocket-kontroller (7 dagar)",
      pocketBreak: "Pocket-kontroller efter resultat, senaste 30 dagarna", pk_server: "Serverkontroller", pk_person: "Personkontroller", pk_message: "Meddelandekontroller",
      guilds: "Servrar", col_server: "Server", col_mode: "Läge", col_open: "Öppna", col_7d: "Larm 7 d", col_since: "Tillagd",
      leave: "Lämna", left: "Guard lämnade servern.",
      quality: "Signalkvalitet", col_signalq: "Signal", col_fired: "Utlöst (30 d)", col_fp: "Falsklarm", col_fprate: "Andel falsklarm",
      networkTitle: "Säkerhetsnätverk", col_user: "Konto", col_guilds: "Servrar", col_reasons: "Skäl", col_first: "Först flaggad",
      clear: "Rensa", cleared: "Nätverksflaggan rensades.", noNetwork: "Inga konton är flaggade i säkerhetsnätverket.",
      sortAsc: "sorterat stigande", sortDesc: "sorterat fallande"
    }
  };

  function store(key, value) {
    try {
      if (value === undefined) return localStorage.getItem(key);
      localStorage.setItem(key, value);
    } catch (e) { return null; }
  }

  var state = {
    me: null,
    lang: store("gw.lang") || ((navigator.language || "en").slice(0, 2) === "sv" ? "sv" : "en"),
    langChosen: !!store("gw.lang"),
    demo: /[?&]demo\b/.test(location.search),
    token: 0,
    guild: null,      // last overview.guild for the sidebar
    openAlerts: {}    // gid -> count, for the nav badge
  };
  if (state.lang !== "sv") state.lang = "en";

  function t(key, vars) {
    var s = (I18N[state.lang] && I18N[state.lang][key]) || I18N.en[key] || key;
    if (vars) s = s.replace(/\{(\w+)\}/g, function (_, k) { return vars[k] != null ? vars[k] : ""; });
    return s;
  }

  // ===================================================================== safe HTML
  function Raw(s) { this.s = s; }
  function raw(s) { return new Raw(s); }
  var ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  function esc(v) { return String(v).replace(/[&<>"']/g, function (c) { return ESC[c]; }); }
  function val(v) {
    if (v == null || v === false) return "";
    if (v instanceof Raw) return v.s;
    if (Array.isArray(v)) return v.map(val).join("");
    return esc(v);
  }
  // Tagged template: interpolations are escaped unless they are Raw (built by html`` itself).
  function html(strings) {
    var out = strings[0];
    for (var i = 1; i < strings.length; i++) out += val(arguments[i]) + strings[i];
    return raw(out);
  }
  // t() with escaped vars, for chrome strings that embed API text.
  function th(key, vars) {
    var safe = {};
    Object.keys(vars || {}).forEach(function (k) { safe[k] = val(vars[k]); });
    return raw(esc(t(key)).replace(/\{(\w+)\}/g, function (_, k) { return safe[k] != null ? safe[k] : ""; }));
  }
  function safeUrl(u) {
    return typeof u === "string" && /^https:\/\/((ptb|canary)\.)?discord(app)?\.com\//.test(u) ? u : null;
  }
  function setHTML(el, h) { el.innerHTML = val(h); }

  // ===================================================================== formatting
  function locale() { return state.lang === "sv" ? "sv-SE" : "en-GB"; }
  function num(n) { return n == null ? "–" : new Intl.NumberFormat(locale()).format(n); }
  function pct(x) { return new Intl.NumberFormat(locale(), { style: "percent", maximumFractionDigits: 0 }).format(x || 0); }
  function date(iso, withTime) {
    if (!iso) return "–";
    var d = new Date(iso);
    var o = { day: "numeric", month: "short", year: "numeric" };
    if (withTime) { o.hour = "2-digit"; o.minute = "2-digit"; }
    return new Intl.DateTimeFormat(locale(), o).format(d);
  }
  function day(isoDay) {
    return new Intl.DateTimeFormat(locale(), { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(isoDay + "T00:00:00Z"));
  }
  function rel(iso) {
    if (!iso) return "–";
    var diff = (new Date(iso).getTime() - Date.now()) / 1000;
    var f = new Intl.RelativeTimeFormat(locale(), { numeric: "auto", style: "short" });
    var a = Math.abs(diff);
    if (a < 60) return f.format(Math.round(diff), "second");
    if (a < 3600) return f.format(Math.round(diff / 60), "minute");
    if (a < 86400) return f.format(Math.round(diff / 3600), "hour");
    if (a < 86400 * 45) return f.format(Math.round(diff / 86400), "day");
    return date(iso);
  }
  function timeEl(iso) { return iso ? html`<time datetime="${iso}" title="${date(iso, true)}">${rel(iso)}</time>` : "–"; }
  function bytes(n) {
    var u = ["B", "KB", "MB", "GB"], i = 0;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return new Intl.NumberFormat(locale(), { maximumFractionDigits: 1 }).format(n) + " " + u[i];
  }
  function duration(s) {
    var d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
    return (d ? d + "d " : "") + (d || h ? h + "h " : "") + m + "m";
  }
  function splitName(name) {
    var m = /^(.*) \((@[^)]+)\)$/.exec(name || "");
    return m ? { display: m[1].trim() || m[2], handle: m[2] } : { display: name || "?", handle: "" };
  }

  // ===================================================================== icons (authored, 24px grid, 1.75 stroke)
  var ICONS = {
    shield: "M12 3l7.5 3v5.5c0 4.6-3.1 8.4-7.5 10-4.4-1.6-7.5-5.4-7.5-10V6L12 3z",
    grid: "M4 4h7v7H4zM13 4h7v4h-7zM13 10h7v10h-7zM4 13h7v7H4z",
    bell: "M6 16.5V11a6 6 0 1 1 12 0v5.5l1.5 1.5h-15L6 16.5zM10 20.5a2 2 0 0 0 4 0",
    users: "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20a6.5 6.5 0 0 1 13 0M16 4.3a3.5 3.5 0 0 1 0 6.4M18.5 14.5A6.5 6.5 0 0 1 21.5 20",
    sliders: "M4 7h9M17 7h3M4 17h3M11 17h9M15 5v4M9 15v4",
    doc: "M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6",
    server: "M4 4.5h16v6H4zM4 13.5h16v6H4zM8 7.5h.01M8 16.5h.01",
    logout: "M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10",
    sun: "M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4",
    moon: "M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z",
    up: "M7 17L17 7M9 7h8v8",
    down: "M7 7l10 10M17 9v8H9",
    flat: "M5 12h14M15 8l4 4-4 4",
    ext: "M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5",
    check: "M5 12.5l4.5 4.5L19 7.5",
    x: "M6 6l12 12M18 6L6 18",
    warn: "M12 4l9 16H3L12 4zM12 10v4M12 17.2h.01",
    print: "M7 9V3h10v6M7 17H4v-7h16v7h-3M7 14h10v7H7z",
    search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4",
    arrowLeft: "M19 12H5M11 6l-6 6 6 6",
    wrench: "M14.5 6.5a4 4 0 0 0 5 5L12 19a2.1 2.1 0 0 1-3-3l7.5-7.5zM14.5 6.5L17 4l3 3-2.5 2.5",
    // level marks: shape carries meaning beside color
    lgreen: "M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM8.5 12.3l2.4 2.4 4.6-4.9",
    lyellow: "M12 4.5l8.5 15h-17l8.5-15zM12 10.5v3.5M12 16.8h.01",
    lred: "M8.7 3.5h6.6l5.2 5.2v6.6l-5.2 5.2H8.7l-5.2-5.2V8.7l5.2-5.2zM9.5 9.5l5 5M14.5 9.5l-5 5"
  };
  function icon(name, cls) {
    return raw('<svg class="ic ' + (cls || "") + '" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="' + ICONS[name] + '"/></svg>');
  }

  // ===================================================================== API
  function ApiError(status, message) { this.status = status; this.message = message; }

  function api(method, path, body) {
    if (state.demo) return demoApi(method, path, body);
    var opts = { method: method, credentials: "same-origin", headers: { Accept: "application/json" } };
    if (method !== "GET") {
      opts.headers["X-Guildward"] = "1";
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body || {});
    }
    return fetch(path, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        if (!r.ok || data.ok === false) throw new ApiError(r.status, data.error || "");
        return data;
      });
    }, function () { throw new ApiError(0, t("errNetwork")); });
  }

  // ---- demo mode: fixtures in demo/*.json, mutations kept in memory for the session
  var demoCache = {};
  function fixture(name) {
    if (!demoCache[name]) {
      demoCache[name] = fetch("demo/" + name + ".json").then(function (r) {
        if (!r.ok) throw new ApiError(404, t("errNotFound"));
        return r.json();
      });
    }
    return demoCache[name];
  }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  function demoApi(method, path, body) {
    var u = new URL(path, location.href), p = u.pathname, q = u.searchParams, m;
    var meName = "morphh";
    var answer = function (promise) {
      // Promise.all attaches to `promise` right away, so an early rejection is never reported as unhandled.
      return Promise.all([promise, new Promise(function (res) { setTimeout(res, 120); })]).then(function (r) { return clone(r[0]); });
    };
    if (/[?&]demo=signin\b/.test(location.search) && p !== "/api/logout") return Promise.reject(new ApiError(401, ""));
    if (p === "/api/me") return answer(fixture("me"));
    if (p === "/api/logout") return answer({ ok: true });
    if ((m = /^\/api\/guilds\/(\w+)\/overview$/.exec(p))) {
      var og = m[1];
      // One overview fixture serves every demo guild; borrow the switched-to guild's name from me.json.
      return answer(Promise.all([fixture("overview"), fixture("me")]).then(function (r) {
        var g = r[1].guilds.filter(function (x) { return x.id === og; })[0];
        if (og === r[0].guild.id || !g) return r[0];
        var o = clone(r[0]);
        o.guild.id = g.id; o.guild.name = g.name;
        return o;
      }));
    }
    if ((m = /^\/api\/guilds\/(\w+)\/fix$/.exec(p))) {
      return answer(fixture("overview").then(function (o) {
        o.audit.forEach(function (a) { if (a.fix === body.fix) { a.ok = true; a.fix = null; } });
        o.recommendations = o.recommendations.filter(function (r) { return r.fix !== body.fix; });
        o.health.score = Math.max(0, o.health.score - 4);
        return { ok: true, text: "Applied: " + body.fix + " (demo)." };
      }));
    }
    if ((m = /^\/api\/guilds\/(\w+)\/alerts$/.exec(p))) {
      return answer(fixture("alerts").then(function (d) {
        var list = d.alerts;
        if (q.get("status") !== "all") list = list.filter(function (a) { return a.status === "open"; });
        return { alerts: list.slice(0, +(q.get("limit") || 50)) };
      }));
    }
    if ((m = /^\/api\/guilds\/(\w+)\/alerts\/(\w+)$/.exec(p))) {
      var id = +m[2];
      return answer(Promise.all([fixture("alerts"), fixture("overview")]).then(function (r) {
        var a = r[0].alerts.filter(function (x) { return x.id === id; })[0];
        if (!a) throw new ApiError(404, t("errNotFound"));
        if (body.action !== "watch") {
          a.status = body.action === "false_positive" ? "false_positive" : "resolved";
          a.resolved_by = meName;
          a.action = body.action;
        }
        r[1].recent_alerts = r[1].recent_alerts.map(function (x) { return x.id === id ? a : x; });
        r[1].kpis.open_alerts = r[0].alerts.filter(function (x) { return x.status === "open"; }).length;
        return { ok: true, alert: a };
      }));
    }
    if ((m = /^\/api\/guilds\/(\w+)\/members$/.exec(p))) {
      return answer(fixture("members").then(function (d) {
        var f = q.get("filter") || "all", s = q.get("sort") || "risk", term = (q.get("q") || "").toLowerCase();
        var rows = d.members.filter(function (r) {
          if (f === "at_risk" && r.level === "green") return false;
          if (f === "minors" && !r.minor) return false;
          if (f === "watch" && r.status !== "watch") return false;
          if (f === "new" && !(r.account_age_days <= 30 || Date.now() - new Date(r.joined_at) < 7 * 864e5)) return false;
          return !term || r.name.toLowerCase().indexOf(term) >= 0;
        });
        rows.sort(s === "name" ? function (a, b) { return a.name.localeCompare(b.name); }
          : s === "recent" ? function (a, b) { return b.joined_at < a.joined_at ? -1 : 1; }
          : function (a, b) { return b.score - a.score; });
        return { members: rows.slice(0, +(q.get("limit") || 100)), total: d.total };
      }));
    }
    if ((m = /^\/api\/guilds\/(\w+)\/members\/(\w+)$/.exec(p))) {
      var uid = m[2];
      if (method === "GET") {
        // Only a few people have a full fixture; the rest get a thin report built from their member row.
        return answer(fixture("member-" + uid).catch(function () {
          delete demoCache["member-" + uid];
          return fixture("members").then(function (d) {
            var row = d.members.filter(function (x) { return x.id === uid; })[0];
            if (!row) throw new ApiError(404, t("errNotFound"));
            return {
              member: Object.assign({ username: splitName(row.name).handle.slice(1), account_created: null, left_at: null, invite_code: null, roles: ["Member"] }, row),
              verdict: { score: row.score, level: row.level, confidence: "Demo: only the member list row exists for this person.",
                signals: row.top_signal ? [{ code: "demo.row", weight: row.score, severe: false, text: row.top_signal, at: null }] : [] },
              summary: [row.top_signal || "Nothing unusual recorded."],
              prediction: { trajectory: row.trend > 0 ? "rising" : row.trend < 0 ? "falling" : "stable", escalation: "none", text: "Not enough history for a prediction." },
              stats: { messages: 0, flagged: 0, distinct_targets: 0, minor_targets: 0, reports: 0, mod_actions: 0, network_flags: 0 },
              contacts: [], timeline: [], series: { days: [], messages: [], flagged: [] }
            };
          });
        }));
      }
      return answer(fixture("members").then(function (d) {
        var row = d.members.filter(function (x) { return x.id === uid; })[0];
        if (!row) throw new ApiError(404, t("errNotFound"));
        row.status = { watch: "watch", trust: "trusted", clear: "none" }[body.action] || "actioned";
        return { ok: true, member: row };
      }));
    }
    if ((m = /^\/api\/guilds\/(\w+)\/settings$/.exec(p))) {
      return answer(fixture("settings").then(function (d) {
        if (method === "PUT") { Object.assign(d.settings, body); return { ok: true, settings: d.settings }; }
        return d;
      }));
    }
    if (p === "/api/owner/overview") return answer(fixture("owner-overview"));
    if ((m = /^\/api\/owner\/(network|guilds)\/(\w+)$/.exec(p))) {
      var key = m[1], target = m[2];
      return answer(fixture("owner-overview").then(function (o) {
        if (key === "network") o.network = o.network.filter(function (n) { return n.user.id !== target; });
        else o.guilds = o.guilds.filter(function (g) { return g.id !== target; });
        return { ok: true };
      }));
    }
    return Promise.reject(new ApiError(404, t("errNotFound")));
  }

  // ===================================================================== small components
  function levelPill(level, score, opts) {
    opts = opts || {};
    var label = t("lvl_" + level);
    return html`<span class="pill pill-${level}" title="${score != null ? t("riskScore", { n: score }) : label}">${icon("l" + level)}${score != null ? html`<b class="num">${score}</b>` : ""}<span class="${opts.short ? "sr" : ""}">${label}</span></span>`;
  }
  function avatar(user) {
    var n = splitName(user && user.name).display;
    var ch = (n.match(/[\p{L}\p{N}]/u) || ["?"])[0].toUpperCase();
    return html`<span class="avatar" aria-hidden="true">${ch}</span>`;
  }
  function who(user, gid, opts) {
    if (!user) return "";
    var n = splitName(user.name);
    var inner = html`${avatar(user)}<span class="who-name"><span class="who-display">${n.display}</span>${n.handle ? html` <span class="who-handle">${n.handle}</span>` : ""}</span>${user.minor ? html` <span class="chip chip-minor">${t("fl_minor")}</span>` : ""}`;
    if (gid && !(opts && opts.nolink)) return html`<a class="who" href="${route("member/" + user.id, gid)}">${inner}</a>`;
    return html`<span class="who">${inner}</span>`;
  }
  function flagChips(flags) {
    return (flags || []).map(function (f) {
      var tone = { reported: "warn", network: "warn", adult_contacting_minors: "bad", escalating: "bad", raid: "warn", quarantined: "warn", trusted: "good" }[f] || "";
      return html`<span class="chip ${tone ? "chip-" + tone : ""}">${t("fl_" + f)}</span>`;
    });
  }
  function trendEl(n) {
    if (!n) return html`<span class="trend trend-flat" title="${t("trendFlat")}">${icon("flat")}<span class="sr">${t("trendFlat")}</span>0</span>`;
    var up = n > 0;
    var label = t(up ? "trendUp" : "trendDown", { n: Math.abs(n) });
    return html`<span class="trend ${up ? "trend-up" : "trend-down"}" title="${label}">${icon(up ? "up" : "down")}<span class="sr">${label}</span>${up ? "+" : "−"}${Math.abs(n)}</span>`;
  }
  function signalList(signals, cls) {
    if (!signals || !signals.length) return "";
    return html`<ul class="signals ${cls || ""}">${signals.map(function (s) {
      var neg = s.weight < 0;
      return html`<li class="${s.severe ? "is-severe" : ""} ${neg ? "is-good" : ""}">
        <span class="sig-w num" title="${neg ? t("reassure") : ""}">${s.weight > 0 ? "+" : s.weight < 0 ? "−" : ""}${Math.abs(s.weight)}</span>
        <span class="sig-text">${s.text}</span>
        ${s.at ? html`<span class="sig-at">${timeEl(s.at)}</span>` : ""}
      </li>`;
    })}</ul>`;
  }
  function sentences(list) {
    return html`<ul class="sentences">${(list || []).map(function (s) { return html`<li>${s}</li>`; })}</ul>`;
  }
  function empty(text) { return html`<p class="empty">${text}</p>`; }
  function panel(title, body, opts) {
    opts = opts || {};
    return html`<section class="panel ${opts.cls || ""}" aria-labelledby="${opts.id}">
      <header class="panel-head"><h2 id="${opts.id}">${title}</h2>${opts.extra || ""}</header>
      ${body}
    </section>`;
  }
  var uid = 0;
  function nextId(p) { return (p || "id") + "-" + (++uid); }

  // ===================================================================== charts (inline SVG)
  var charts = {};
  function chart(label, days, values, opts) {
    opts = opts || {};
    var id = nextId("ch"), n = values.length, W = 300, H = opts.compact ? 56 : 84, pad = 3;
    if (!n) return html`<figure class="chart"><figcaption><span class="chart-title">${label}</span></figcaption><p class="empty">–</p></figure>`;
    var max = Math.max.apply(null, values.concat([1]));
    var total = values.reduce(function (a, b) { return a + b; }, 0);
    var peakI = values.indexOf(max);
    var slot = W / n, y = function (v) { return H - pad - (v / max) * (H - pad * 2); };
    var marks;
    if (opts.type === "area") {
      var pts = values.map(function (v, i) { return [(i + 0.5) * slot, y(v)]; });
      var line = pts.map(function (p, i) { return (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1); }).join("");
      var area = line + "L" + pts[n - 1][0].toFixed(1) + " " + (H - pad) + "L" + pts[0][0].toFixed(1) + " " + (H - pad) + "Z";
      marks = '<path class="ch-area" d="' + area + '"/><path class="ch-line" d="' + line + '"/>' +
        '<circle class="ch-dot" r="3.5" cx="-10" cy="-10"/>';
    } else {
      var bw = slot - 2;
      marks = values.map(function (v, i) {
        var x = i * slot + 1, top = y(v), h = H - pad - top;
        if (v > 0 && h < 2) { h = 2; top = H - pad - 2; }
        var r = Math.min(2, bw / 2, h);
        var d = v > 0 ? "M" + x.toFixed(1) + " " + (H - pad) + "V" + (top + r).toFixed(1) + "q0 -" + r + " " + r + " -" + r +
          "H" + (x + bw - r).toFixed(1) + "q" + r + " 0 " + r + " " + r + "V" + (H - pad) + "Z" : "";
        return '<path class="ch-bar" data-i="' + i + '" d="' + d + '"/>';
      }).join("");
    }
    charts[id] = { label: label, days: days, values: values, type: opts.type || "bar", slot: slot, y: y };
    var aria = t("chartAria", { label: label, total: num(total), peak: num(max), day: days[peakI] ? day(days[peakI]) : "" });
    return html`<figure class="chart ${opts.compact ? "chart-compact" : ""}" data-chart="${id}">
      <figcaption><span class="chart-title">${label}</span><span class="chart-total num">${t("chartTotal", { n: num(total) })}</span></figcaption>
      <div class="chart-plot">
        <span class="chart-max num" aria-hidden="true">${num(max)}</span>
        <svg viewBox="0 0 ${W} ${H}" role="img" tabindex="0" aria-label="${aria}">
          <line class="ch-grid" x1="0" x2="${W}" y1="${pad}" y2="${pad}"/>
          <line class="ch-grid" x1="0" x2="${W}" y1="${(H / 2).toFixed(1)}" y2="${(H / 2).toFixed(1)}"/>
          <line class="ch-base" x1="0" x2="${W}" y1="${H - pad}" y2="${H - pad}"/>
          <line class="ch-cross" x1="-10" x2="-10" y1="0" y2="${H}"/>
          ${raw(marks)}
        </svg>
        <div class="chart-tip" role="status" hidden></div>
      </div>
      <div class="chart-axis" aria-hidden="true"><span>${days[0] ? day(days[0]) : ""}</span><span>${days[n - 1] ? day(days[n - 1]) : ""}</span></div>
    </figure>`;
  }
  function chartTable(days, series) {
    // series: [[label, values]]
    return html`<details class="chart-data"><summary>${t("dataTable")}</summary><div class="table-wrap"><table class="table table-tight">
      <thead><tr><th scope="col">${t("day")}</th>${series.map(function (s) { return html`<th scope="col" class="r">${s[0]}</th>`; })}</tr></thead>
      <tbody>${days.map(function (d, i) {
        return html`<tr><th scope="row">${day(d)}</th>${series.map(function (s) { return html`<td class="r num">${num(s[1][i])}</td>`; })}</tr>`;
      })}</tbody></table></div></details>`;
  }
  function wireCharts(root) {
    root.querySelectorAll("[data-chart]").forEach(function (fig) {
      var c = charts[fig.getAttribute("data-chart")];
      if (!c) return;
      var svg = fig.querySelector("svg"), tip = fig.querySelector(".chart-tip"), plot = fig.querySelector(".chart-plot");
      var cross = svg.querySelector(".ch-cross"), dot = svg.querySelector(".ch-dot"), cur = -1;
      function show(i) {
        cur = Math.max(0, Math.min(c.values.length - 1, i));
        var cx = (cur + 0.5) * c.slot;
        cross.setAttribute("x1", cx); cross.setAttribute("x2", cx);
        if (dot) { dot.setAttribute("cx", cx); dot.setAttribute("cy", c.y(c.values[cur])); }
        svg.querySelectorAll(".ch-bar").forEach(function (b) { b.classList.toggle("is-hot", +b.getAttribute("data-i") === cur); });
        tip.textContent = "";
        var dEl = document.createElement("span"); dEl.textContent = day(c.days[cur]);
        var vEl = document.createElement("b"); vEl.className = "num"; vEl.textContent = num(c.values[cur]);
        tip.appendChild(dEl); tip.appendChild(vEl);
        tip.hidden = false;
        var pw = plot.clientWidth, tw = tip.offsetWidth, x = (cur + 0.5) / c.values.length * pw;
        tip.style.left = Math.max(0, Math.min(pw - tw, x - tw / 2)) + "px";
        fig.classList.add("is-active");
      }
      function hide() { tip.hidden = true; cross.setAttribute("x1", -10); cross.setAttribute("x2", -10); if (dot) dot.setAttribute("cx", -10); fig.classList.remove("is-active"); svg.querySelectorAll(".is-hot").forEach(function (b) { b.classList.remove("is-hot"); }); }
      svg.addEventListener("pointermove", function (e) {
        var r = svg.getBoundingClientRect();
        show(Math.floor((e.clientX - r.left) / r.width * c.values.length));
      });
      svg.addEventListener("pointerleave", hide);
      svg.addEventListener("blur", hide);
      svg.addEventListener("focus", function () { show(cur < 0 ? c.values.length - 1 : cur); });
      svg.addEventListener("keydown", function (e) {
        var k = { ArrowLeft: -1, ArrowRight: 1 }[e.key];
        if (k) { e.preventDefault(); show(cur + k); }
        else if (e.key === "Home") { e.preventDefault(); show(0); }
        else if (e.key === "End") { e.preventDefault(); show(c.values.length - 1); }
      });
    });
  }

  function gauge(score, level, grade) {
    // 180° arc, pathLength 100 so dash values are scores. Zones match core/models.py (35 / 65).
    var arc = "M20 100A80 80 0 0 1 180 100";
    return html`<div class="gauge" role="img" aria-label="${t("grade") + " " + grade + ". " + t("riskScore", { n: score }) + ". " + t("lvl_" + level)}">
      <svg viewBox="0 0 200 112" aria-hidden="true">
        <path class="g-zone g-green" d="${arc}" pathLength="100" stroke-dasharray="34.4 100"/>
        <path class="g-zone g-yellow" d="${arc}" pathLength="100" stroke-dasharray="0 35.3 29.4 100"/>
        <path class="g-zone g-red" d="${arc}" pathLength="100" stroke-dasharray="0 65.3 34.7 100"/>
        <path class="g-value g-${level}" d="${arc}" pathLength="100" stroke-dasharray="${Math.max(0.5, Math.min(100, score))} 200"/>
      </svg>
      <div class="gauge-read"><span class="gauge-grade">${grade}</span><span class="gauge-score num">${score}<small>/100</small></span></div>
    </div>`;
  }

  // ===================================================================== toast + confirm
  function toast(msg, kind) {
    var box = document.getElementById("toasts");
    var el = document.createElement("div");
    el.className = "toast" + (kind === "error" ? " toast-error" : "");
    el.textContent = msg;
    box.appendChild(el);
    setTimeout(function () { el.classList.add("is-out"); setTimeout(function () { el.remove(); }, 250); }, kind === "error" ? 6000 : 3500);
  }
  function confirmDialog(title, body, okLabel) {
    var dlg = document.getElementById("confirm");
    dlg.querySelector("h2").textContent = title;
    dlg.querySelector("p").textContent = body;
    dlg.querySelector("[value=ok]").textContent = okLabel;
    dlg.querySelector("[value=cancel]").textContent = t("cancel");
    dlg.returnValue = "";
    dlg.showModal();
    dlg.querySelector("[value=cancel]").focus();
    return new Promise(function (res) {
      dlg.addEventListener("close", function once() { dlg.removeEventListener("close", once); res(dlg.returnValue === "ok"); });
    });
  }
  function needsConfirm(action, name) {
    if (action === "kick") return confirmDialog(t("cKickTitle", { name: name }), t("cKickBody"), t("a_kick"));
    if (action === "ban") return confirmDialog(t("cBanTitle", { name: name }), t("cBanBody"), t("a_ban"));
    return Promise.resolve(true);
  }
  function busy(btn, on) {
    if (!btn) return;
    btn.disabled = on;
    btn.setAttribute("aria-busy", on ? "true" : "false");
  }
  function fail(e) {
    if (e instanceof ApiError && e.status === 401) { signin(); return; }
    toast((e && e.message) || t("errTitle"), "error");
  }

  // ===================================================================== routing
  function parseHash() {
    var h = location.hash.replace(/^#\/?/, "");
    var qi = h.indexOf("?"), query = new URLSearchParams(qi >= 0 ? h.slice(qi + 1) : "");
    var parts = (qi >= 0 ? h.slice(0, qi) : h).split("/").filter(Boolean);
    return { parts: parts, query: query };
  }
  function route(sub, gid) { return "#/g/" + encodeURIComponent(gid) + (sub ? "/" + sub : ""); }

  var main = document.getElementById("main");

  function render() {
    var token = ++state.token, r = parseHash(), p = r.parts;
    charts = {};
    var view, gid = null, key;
    if (p[0] === "g" && p[1]) {
      gid = p[1];
      key = p[2] || "overview";
      view = { overview: viewOverview, alerts: viewAlerts, members: viewMembers, member: viewMember, settings: viewSettings, report: viewReport }[key];
    } else if (p[0] === "owner") { key = "owner"; view = state.me.owner ? viewOwner : null; }
    else if (!p.length) {
      if (state.me.guilds.length) { location.replace(route("", state.me.guilds[0].id)); return; }
      if (state.me.owner) { location.replace("#/owner"); return; }
      shell(null, null);
      setHTML(main, errorView(t("noGuilds"), false));
      return;
    }
    shell(gid, key);
    document.body.classList.toggle("is-report", key === "report");
    if (!view) { setHTML(main, errorView(t("errNotFound"), false)); return; }
    if (!state.quiet) setHTML(main, skeleton());
    state.quiet = false;
    var ctx = { gid: gid, parts: p, query: r.query, alive: function () { return token === state.token; } };
    Promise.resolve(view(ctx)).then(function (out) {
      if (!ctx.alive() || out === undefined) return;
      setHTML(main, out);
      wireCharts(main);
      if (ctx.after) ctx.after();
      var h1 = main.querySelector("h1");
      if (h1 && state.focusOnRender) { h1.setAttribute("tabindex", "-1"); h1.focus({ preventScroll: true }); }
      state.focusOnRender = true;
    }).catch(function (e) {
      if (!ctx.alive()) return;
      if (e instanceof ApiError && e.status === 401) return signin();
      var msg = e instanceof ApiError ? (e.status === 403 ? t("errForbidden") : e.status === 404 ? t("errNotFound") : e.message || t("errTitle")) : t("errTitle");
      if (!(e instanceof ApiError)) console.error(e);
      setHTML(main, errorView(msg, true));
    });
  }
  function skeleton() {
    return html`<div class="skeleton" aria-busy="true" aria-label="${t("loading")}"><div class="sk sk-h"></div><div class="sk-row"><div class="sk sk-b"></div><div class="sk sk-b"></div></div><div class="sk sk-c"></div></div>`;
  }
  function errorView(msg, retry) {
    return html`<div class="state-box"><h1>${t("errTitle")}</h1><p>${msg}</p>${retry ? html`<button class="btn" type="button" data-act="retry">${t("retry")}</button>` : ""}</div>`;
  }

  // ===================================================================== shell (sidebar)
  function shell(gid, key) {
    document.body.classList.remove("signed-out");
    document.documentElement.lang = state.lang;
    var me = state.me, guilds = me.guilds;
    var g = guilds.filter(function (x) { return x.id === gid; })[0];
    var badge = gid && state.openAlerts[gid] ? html`<span class="badge num" aria-label="${state.openAlerts[gid] + " " + t("f_open")}">${state.openAlerts[gid]}</span>` : "";
    var link = function (sub, k, ic, label, extra) {
      return html`<a href="${route(sub, gid)}" class="nav-link" ${key === k ? raw('aria-current="page"') : ""}>${icon(ic)}<span>${label}</span>${extra || ""}</a>`;
    };
    var switcher = guilds.length > 1
      ? html`<label class="sr" for="guild-switch">${t("server")}</label><select id="guild-switch" class="guild-switch">${guilds.map(function (x) {
          return html`<option value="${x.id}" ${x.id === gid ? raw("selected") : ""}>${x.name}</option>`;
        })}${!g && gid ? html`<option value="${gid}" selected>${gid}</option>` : ""}</select>`
      : html`<div class="guild-name">${g ? g.name : state.guild && state.guild.id === gid ? state.guild.name : ""}</div>`;
    setHTML(document.getElementById("side"), html`
      <div class="brand">${icon("shield", "brand-mark")}<span class="brand-text"><b>Guildward</b> <span>${t("brandSub")}</span></span>${state.demo ? html`<span class="chip chip-demo">${t("demo")}</span>` : ""}</div>
      ${gid ? html`<div class="guild-box">${switcher}</div>
      <nav class="nav" aria-label="${t("nav")}">
        ${link("", "overview", "grid", t("overview"))}
        ${link("alerts", "alerts", "bell", t("alerts"), badge)}
        ${link("members", "members", "users", t("members"))}
        ${link("settings", "settings", "sliders", t("settings"))}
        ${link("report", "report", "doc", t("report"))}
      </nav>` : guilds.length ? html`<nav class="nav" aria-label="${t("nav")}">${guilds.map(function (x) { return html`<a class="nav-link" href="${route("", x.id)}">${icon("grid")}<span>${x.name}</span></a>`; })}</nav>` : ""}
      ${me.owner ? html`<nav class="nav nav-owner" aria-label="${t("owner")}"><a href="#/owner" class="nav-link" ${key === "owner" ? raw('aria-current="page"') : ""}>${icon("server")}<span>${t("owner")}</span></a></nav>` : ""}
      <div class="side-foot">
        <div class="prefs">
          <div class="seg" role="group" aria-label="${t("language")}">
            <button type="button" data-act="lang" data-v="en" aria-pressed="${state.lang === "en"}">EN</button>
            <button type="button" data-act="lang" data-v="sv" aria-pressed="${state.lang === "sv"}">SV</button>
          </div>
          <button type="button" class="icon-btn" data-act="theme" aria-label="${t("theme") + ": " + t(isDark() ? "dark" : "light")}" title="${t("theme")}">${icon(isDark() ? "moon" : "sun")}</button>
        </div>
        <div class="me">${avatar(me.user)}<span class="me-name">${me.user.name}</span>
          <button type="button" class="icon-btn" data-act="logout" aria-label="${t("logout")}" title="${t("logout")}">${icon("logout")}</button></div>
      </div>`);
    var sw = document.getElementById("guild-switch");
    if (sw) sw.addEventListener("change", function () { location.hash = route("", sw.value); });
    document.querySelector(".skip").textContent = t("skip");
  }

  function signin() {
    state.token++;
    document.body.classList.add("signed-out");
    document.body.classList.remove("is-report");
    document.getElementById("side").textContent = "";
    var cmd = html`<code>/guard dashboard</code>`;
    setHTML(main, html`<div class="signin">
      ${icon("shield", "signin-mark")}
      <h1>${t("signinTitle")}</h1>
      <p>${th("signinBody", { cmd: cmd })}</p>
      ${!state.demo ? html`<p class="signin-demo"><a href="?demo#/g/10">${t("signinDemo")}</a></p>` : ""}
      <div class="seg" role="group" aria-label="${t("language")}">
        <button type="button" data-act="lang" data-v="en" aria-pressed="${state.lang === "en"}">EN</button>
        <button type="button" data-act="lang" data-v="sv" aria-pressed="${state.lang === "sv"}">SV</button>
      </div>
    </div>`);
  }

  // ===================================================================== shared renderers
  function memberTable(rows, gid, opts) {
    opts = opts || {};
    if (!rows.length) return empty(t("noMembers"));
    return html`<div class="table-wrap"><table class="table members-table ${opts.compact ? "is-compact" : ""}">
      <thead><tr>
        <th scope="col">${t("col_member")}</th><th scope="col">${t("col_risk")}</th><th scope="col" class="r">${t("col_trend")}</th>
        ${opts.compact ? "" : html`<th scope="col">${t("col_age")}</th><th scope="col">${t("col_joined")}</th><th scope="col">${t("col_seen")}</th>`}
        <th scope="col">${t("col_signal")}</th>
      </tr></thead>
      <tbody>${rows.map(function (m) {
        return html`<tr class="${m.status === "left" ? "is-left" : ""}">
          <td class="cell-member">${who(m, gid)}${opts.compact ? "" : html`<div class="chips">${m.status !== "none" && m.flags.indexOf(m.status) < 0 && m.status !== "trusted" ? html`<span class="chip">${t("ms_" + m.status)}</span>` : ""}${flagChips(m.flags.filter(function (f) { return f !== "minor"; }))}</div>`}</td>
          <td>${levelPill(m.level, m.score)}</td>
          <td class="r">${trendEl(m.trend)}</td>
          ${opts.compact ? "" : html`<td class="nowrap">${m.self_age != null ? t("ageYears", { n: m.self_age }) : "–"}<div class="sub">${t("acctDays", { n: num(m.account_age_days) })}</div></td>
          <td class="nowrap">${timeEl(m.joined_at)}</td><td class="nowrap">${timeEl(m.last_seen)}</td>`}
          <td class="cell-signal">${m.top_signal || html`<span class="muted">–</span>`}</td>
        </tr>`;
      })}</tbody></table></div>`;
  }

  function alertItem(a, gid, opts) {
    opts = opts || {};
    var jump = safeUrl(a.jump_url);
    var closed = a.status !== "open";
    var acts = ["resolve", "false_positive", "watch", "timeout", "delete", "kick", "ban"].filter(function (x) {
      if (x === "delete") return a.kind === "message" && !!a.jump_url;
      if (["timeout", "kick", "ban", "watch"].indexOf(x) >= 0) return !!a.user;
      return true;
    });
    return html`<article class="alert alert-${a.level} ${closed ? "is-closed" : ""}" data-alert="${a.id}" aria-labelledby="al-${a.id}">
      <div class="alert-top">
        ${levelPill(a.level, a.score)}
        <span class="chip">${t("k_" + a.kind)}</span>
        ${closed ? html`<span class="chip chip-good">${icon("check")}${t("st_" + a.status)}</span>` : ""}
        <span class="alert-time">${timeEl(a.created_at)}</span>
      </div>
      <h3 id="al-${a.id}" class="alert-title">${a.title}</h3>
      <p class="alert-summary">${a.summary}</p>
      ${a.quote && !opts.compact ? html`<blockquote class="quote">${a.quote}</blockquote>` : ""}
      ${(a.user || a.target) && !opts.compact ? html`<div class="alert-people">${who(a.user, gid)}${a.user && a.target ? html`<span class="arrow">${t("toTarget")}</span>` : ""}${who(a.target, gid)}</div>` : ""}
      ${!opts.compact && a.signals && a.signals.length ? html`<details class="alert-sigs"><summary>${t("signalsN", { n: a.signals.length })}</summary>${signalList(a.signals)}</details>` : ""}
      ${closed && a.resolved_by ? html`<p class="alert-resolved">${t("resolvedBy", { status: t("st_" + a.status), who: a.resolved_by })}${a.action && a.action !== a.status && a.action !== "resolve" ? " · " + t("actionWas", { a: t("a_" + a.action) }) : ""}</p>` : ""}
      ${!opts.compact ? html`<div class="alert-actions">
        ${!closed ? acts.map(function (x) {
          var cls = x === "resolve" ? "btn btn-primary" : x === "kick" || x === "ban" ? "btn btn-danger" : "btn";
          return html`<button type="button" class="${cls}" data-act="alert" data-id="${a.id}" data-action="${x}" data-name="${a.user ? splitName(a.user.name).display : ""}">${t("a_" + x)}</button>`;
        }) : ""}
        ${jump ? html`<a class="btn btn-ghost" href="${jump}" target="_blank" rel="noopener noreferrer">${icon("ext")}${t("jump")}</a>` : ""}
      </div>` : ""}
    </article>`;
  }

  // ===================================================================== views: overview
  var KPI_LINKS = { at_risk: "members?filter=at_risk", red: "members?filter=at_risk", minors_est: "members?filter=minors", open_alerts: "alerts", joins_7d: "members?filter=new" };

  function viewOverview(ctx) {
    return api("GET", "/api/guilds/" + ctx.gid + "/overview").then(function (o) {
      state.guild = o.guild;
      state.openAlerts[ctx.gid] = o.kpis.open_alerts;
      if (ctx.alive()) shell(ctx.gid, "overview");
      return overviewBody(o, ctx.gid, false);
    });
  }

  function guildMeta(g) {
    return html`<p class="page-meta">
      <span>${t("ovMembers", { n: num(g.member_count) })}</span>
      <span class="mode mode-${g.mode}">${t("ovMode", { mode: t("mode_" + g.mode) })}</span>
      ${g.alert_channel ? html`<span>${t("ovAlertsTo", { ch: g.alert_channel })}</span>` : ""}
      <span>${t("ovSince", { d: date(g.guard_since) })}</span>
    </p>`;
  }

  function kpiStrip(k, gid, linked) {
    var keys = ["members", "minors_est", "at_risk", "red", "open_alerts", "flagged_7d", "messages_7d", "joins_7d", "actions_7d", "median_response_min"];
    return html`<dl class="kpis">${keys.map(function (key) {
      var v = key === "median_response_min" ? (k[key] == null ? "–" : t("minutes", { n: k[key] })) : num(k[key]);
      var tone = (key === "red" && k.red) ? "kpi-bad" : (key === "open_alerts" && k.open_alerts) ? "kpi-warn" : "";
      var label = html`${t("k_" + key)}${/_7d$/.test(key) ? html` <span class="kpi-span">${t("last7")}</span>` : ""}`;
      var value = linked && KPI_LINKS[key] ? html`<a href="${route(KPI_LINKS[key], gid)}">${v}</a>` : v;
      return html`<div class="kpi ${tone}"><dt>${label}</dt><dd class="num">${value}</dd></div>`;
    })}</dl>`;
  }

  function seriesCharts(s, keys) {
    return html`<div class="charts">${keys.map(function (k) {
      return chart(t("s_" + k), s.days, s[k] || [], { type: k === "messages" ? "area" : "bar" });
    })}</div>${chartTable(s.days, keys.map(function (k) { return [t("s_" + k), s[k] || []]; }))}`;
  }

  function overviewBody(o, gid, isReport) {
    var g = o.guild, h = o.health;
    var passed = o.audit.filter(function (a) { return a.ok; }).length;
    var perms = o.permissions_missing && o.permissions_missing.length ? html`<div class="banner banner-warn" role="alert">${icon("warn")}<div><strong>${t("permTitle")}</strong><p>${th("permBody", { list: html`<b>${o.permissions_missing.join(", ")}</b>` })}</p></div></div>` : "";
    var healthPanel = html`<section class="panel panel-health" aria-labelledby="h-health">
      <header class="panel-head"><h2 id="h-health">${t("health")}</h2>${levelPill(h.level, null)}</header>
      <div class="health-top">${gauge(h.score, h.level, h.grade)}<p class="confidence">${h.confidence}</p></div>
      <h3 class="sub-h">${t("healthReasons")}</h3>
      ${signalList(h.signals)}
    </section>`;
    var situation = panel(t("situation"), html`${sentences(o.summary)}<h3 class="sub-h">${t("keyFigures")}</h3>${kpiStrip(o.kpis, gid, !isReport)}`, { id: "h-sit", cls: "panel-situation" });
    var recs = panel(t("recs"), o.recommendations.length ? html`<ul class="recs">${o.recommendations.map(function (r) {
      return html`<li class="rec"><span class="sev sev-${r.severity}">${t("sev_" + r.severity)}</span><span class="rec-text">${r.text}</span>${r.fix && !isReport ? html`<button type="button" class="btn btn-sm" data-act="fix" data-fix="${r.fix}">${icon("wrench")}${t("fix")}</button>` : ""}</li>`;
    })}</ul>` : empty(t("noRecs")), { id: "h-recs" });
    var audit = panel(t("audit"), html`<ul class="audit">${o.audit.map(function (a) {
      return html`<li class="${a.ok ? "is-ok" : "is-fail"}">
        <span class="audit-mark">${icon(a.ok ? "check" : "x")}<span class="sr">${a.ok ? t("auditOk") : t("auditFail")}</span></span>
        <div class="audit-body"><b>${a.label}</b> ${!a.ok ? html`<span class="sev sev-${a.severity}">${t("sev_" + a.severity)}</span>` : ""}<p>${a.detail}</p></div>
        ${!a.ok && a.fix && !isReport ? html`<button type="button" class="btn btn-sm" data-act="fix" data-fix="${a.fix}">${t("fix")}</button>` : ""}
      </li>`;
    })}</ul>`, { id: "h-audit", extra: html`<span class="panel-note num">${t("auditPassed", { n: passed, m: o.audit.length })}</span>` });
    var activity = panel(t("activity"), seriesCharts(o.series, ["messages", "flagged", "joins", "alerts"]), { id: "h-act", cls: "panel-wide" });
    var risks = panel(t("topRisks"), memberTable(o.top_risks, isReport ? null : gid, { compact: true }), { id: "h-risk", extra: isReport ? "" : html`<a class="panel-link" href="${route("members?filter=at_risk", gid)}">${t("seeAll")}</a>` });
    var recent = panel(t("recentAlerts"), o.recent_alerts.length ? html`<div class="alert-list is-compact">${o.recent_alerts.map(function (a) { return alertItem(a, gid, { compact: true }); })}</div>` : empty(t("noAlerts")), { id: "h-recent", extra: isReport ? "" : html`<a class="panel-link" href="${route("alerts", gid)}">${t("openQueue")}</a>` });

    if (isReport) {
      return html`<article class="report-doc">
        <header class="report-head">
          <div class="report-brand">${icon("shield", "brand-mark")}<span>Guildward Guard · ${t("reportTitle")}</span></div>
          <h1>${g.name}</h1>${guildMeta(g)}
          <p class="report-date">${t("reportFor", { d: date(new Date().toISOString(), true) })}</p>
          <div class="report-tools no-print"><button type="button" class="btn btn-primary" data-act="print">${icon("print")}${t("print")}</button><a class="btn btn-ghost" href="${route("", gid)}">${icon("arrowLeft")}${t("reportBack")}</a></div>
        </header>
        ${perms}
        <div class="report-grid">${healthPanel}${situation}</div>
        ${recs}${audit}${activity}${risks}${recent}
      </article>`;
    }
    return html`<header class="page-head"><div><h1>${g.name}</h1>${guildMeta(g)}</div>
        <a class="btn btn-ghost" href="${route("report", gid)}">${icon("print")}${t("printable")}</a></header>
      ${perms}
      <div class="grid grid-ov">${healthPanel}${situation}${recs}${audit}${activity}${risks}${recent}</div>`;
  }

  // ===================================================================== views: alerts
  function viewAlerts(ctx) {
    var status = ctx.query.get("status") === "all" ? "all" : "open";
    return api("GET", "/api/guilds/" + ctx.gid + "/alerts?status=" + status + "&limit=50").then(function (d) {
      if (status === "open") { state.openAlerts[ctx.gid] = d.alerts.length; if (ctx.alive()) shell(ctx.gid, "alerts"); }
      var tabs = ["open", "all"].map(function (s) {
        return html`<a class="tab" href="${route("alerts" + (s === "all" ? "?status=all" : ""), ctx.gid)}" ${s === status ? raw('aria-current="page"') : ""}>${t("f_" + s)}</a>`;
      });
      return html`<header class="page-head"><div><h1>${t("alertsTitle")}</h1></div></header>
        <nav class="tabs" aria-label="${t("alertsTitle")}">${tabs}</nav>
        ${d.alerts.length ? html`<div class="alert-list">${d.alerts.map(function (a) { return alertItem(a, ctx.gid); })}</div>`
          : empty(status === "open" ? t("noAlertsOpen") : t("noAlerts"))}`;
    });
  }

  // ===================================================================== views: members
  var FILTERS = ["all", "at_risk", "minors", "watch", "new"], SORTS = ["risk", "recent", "name"];

  function viewMembers(ctx) {
    var q = { filter: ctx.query.get("filter"), sort: ctx.query.get("sort"), q: ctx.query.get("q") || "" };
    if (FILTERS.indexOf(q.filter) < 0) q.filter = "all";
    if (SORTS.indexOf(q.sort) < 0) q.sort = "risk";
    var gid = ctx.gid;
    function href(over) {
      var o = Object.assign({}, q, over), s = new URLSearchParams();
      if (o.filter !== "all") s.set("filter", o.filter);
      if (o.sort !== "risk") s.set("sort", o.sort);
      if (o.q) s.set("q", o.q);
      var qs = s.toString();
      return route("members" + (qs ? "?" + qs : ""), gid);
    }
    function load() {
      var url = "/api/guilds/" + gid + "/members?filter=" + q.filter + "&sort=" + q.sort + "&q=" + encodeURIComponent(q.q) + "&limit=100";
      return api("GET", url);
    }
    ctx.after = function () {
      var input = document.getElementById("m-search"), sort = document.getElementById("m-sort"), timer;
      function refresh() {
        history.replaceState(null, "", href({}));
        var box = document.getElementById("m-table");
        box.setAttribute("aria-busy", "true");
        load().then(function (d) {
          if (!ctx.alive()) return;
          setHTML(box, membersResult(d));
          box.removeAttribute("aria-busy");
          document.querySelectorAll(".tabs .tab").forEach(function (a, i) { a.href = href({ filter: FILTERS[i] }); });
        }).catch(fail);
      }
      input.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(function () { q.q = input.value.trim(); refresh(); }, 250); });
      sort.addEventListener("change", function () { q.sort = sort.value; refresh(); });
    };
    function membersResult(d) {
      return html`<p class="result-count" role="status">${t("showing", { n: num(d.members.length), m: num(d.total) })}</p>${memberTable(d.members, gid)}`;
    }
    return load().then(function (d) {
      return html`<header class="page-head"><div><h1>${t("membersTitle")}</h1></div></header>
        <div class="toolbar">
          <nav class="tabs" aria-label="${t("membersTitle")}">${FILTERS.map(function (f) {
            return html`<a class="tab" href="${href({ filter: f })}" ${f === q.filter ? raw('aria-current="page"') : ""}>${t("mf_" + f)}</a>`;
          })}</nav>
          <div class="toolbar-right">
            <label class="search">${icon("search")}<span class="sr">${t("search")}</span><input id="m-search" type="search" value="${q.q}" placeholder="${t("searchPh")}" autocomplete="off"></label>
            <label class="select-label"><span>${t("sortBy")}</span><select id="m-sort">${SORTS.map(function (s) { return html`<option value="${s}" ${s === q.sort ? raw("selected") : ""}>${t("so_" + s)}</option>`; })}</select></label>
          </div>
        </div>
        <div id="m-table">${membersResult(d)}</div>`;
    });
  }

  // ===================================================================== views: person report
  var current = { report: null };

  function viewMember(ctx) {
    var uidv = ctx.parts[3];
    return api("GET", "/api/guilds/" + ctx.gid + "/members/" + encodeURIComponent(uidv)).then(function (r) {
      current.report = r;
      return memberBody(r, ctx.gid);
    });
  }

  function memberBody(r, gid) {
    var m = r.member, v = r.verdict, pr = r.prediction, n = splitName(m.name);
    var meta = [
      m.self_age != null ? t("pSelfAge", { n: m.self_age }) : null,
      m.account_created ? t("pAccount", { d: date(m.account_created) }) : t("acctDays", { n: m.account_age_days }),
      m.joined_at ? t("pJoined", { d: date(m.joined_at) }) : null,
      m.invite_code ? t("pInvite", { c: m.invite_code }) : null,
      m.left_at ? t("pLeft", { d: date(m.left_at) }) : null
    ].filter(Boolean);
    var actions = ["watch", "trust", "clear", "timeout", "kick", "ban"];
    var trIcon = { rising: "up", falling: "down", stable: "flat" }[pr.trajectory] || "flat";
    var statKeys = ["messages", "flagged", "distinct_targets", "minor_targets", "reports", "mod_actions", "network_flags"];
    return html`<a class="back" href="${route("members", gid)}">${icon("arrowLeft")}${t("members")}</a>
      <header class="person-head">
        <div class="person-id">
          <span class="avatar avatar-lg" aria-hidden="true">${(n.display.match(/[\p{L}\p{N}]/u) || ["?"])[0].toUpperCase()}</span>
          <div>
            <h1>${n.display} ${n.handle ? html`<span class="who-handle">${n.handle}</span>` : ""}</h1>
            <p class="page-meta">${meta.map(function (x) { return html`<span>${x}</span>`; })}</p>
            <div class="chips">${m.status !== "none" ? html`<span class="chip chip-status">${t("ms_" + m.status)}</span>` : ""}${m.minor ? html`<span class="chip chip-minor">${t("fl_minor")}</span>` : ""}${flagChips(m.flags.filter(function (f) { return f !== "minor" && f !== m.status; }))}
              ${(m.roles || []).length ? html`<span class="roles"><span class="sr">${t("pRoles")}: </span>${m.roles.map(function (x) { return html`<span class="role">${x}</span>`; })}</span>` : ""}</div>
          </div>
        </div>
        <div class="person-actions" role="group" aria-label="${t("memberActions")}">${actions.map(function (a) {
          var cls = a === "kick" || a === "ban" ? "btn btn-danger" : a === "watch" ? "btn btn-primary" : "btn";
          var on = (a === "watch" && m.status === "watch") || (a === "trust" && m.status === "trusted");
          return html`<button type="button" class="${cls}" data-act="member" data-uid="${m.id}" data-action="${a}" data-name="${n.display}" ${on ? raw('aria-pressed="true"') : ""}>${t("a_" + a)}</button>`;
        })}</div>
      </header>
      <div class="grid grid-person">
        <section class="panel panel-verdict" aria-labelledby="p-verdict">
          <header class="panel-head"><h2 id="p-verdict">${t("verdict")}</h2></header>
          <div class="verdict-top"><span class="verdict-score num score-${v.level}">${v.score}</span>${levelPill(v.level, null)}${trendEl(m.trend)}</div>
          <p class="confidence">${v.confidence}</p>
          ${signalList(v.signals)}
        </section>
        <div class="stack">
          ${panel(t("summary"), sentences(r.summary), { id: "p-sum" })}
          <section class="panel panel-predict pred-${pr.escalation}" aria-labelledby="p-pred">
            <header class="panel-head"><h2 id="p-pred">${t("prediction")}</h2></header>
            <div class="pred-tags"><span class="pred-tag">${icon(trIcon)}${t("tr_" + pr.trajectory)}</span><span class="pred-tag pred-esc">${icon(pr.escalation === "none" ? "check" : "warn")}${t("es_" + pr.escalation)}</span></div>
            <p class="pred-text">${pr.text}</p>
          </section>
        </div>
        ${panel(t("stats"), html`<dl class="stats">${statKeys.map(function (k) {
          var warn = (k === "minor_targets" || k === "reports" || k === "network_flags" || k === "flagged") && r.stats[k] > 0;
          return html`<div class="${warn ? "is-warn" : ""}"><dt>${t("st_" + k)}</dt><dd class="num">${num(r.stats[k])}</dd></div>`;
        })}</dl><div class="charts charts-2">${chart(t("s_messages"), r.series.days, r.series.messages, { type: "area", compact: true })}${chart(t("s_flagged"), r.series.days, r.series.flagged, { compact: true })}</div>`, { id: "p-stats" })}
        ${panel(t("contacts"), r.contacts.length ? html`<div class="table-wrap"><table class="table">
          <thead><tr><th scope="col">${t("col_member")}</th><th scope="col">${t("col_risk")}</th><th scope="col" class="r">${t("col_messages")}</th><th scope="col">${t("col_stages")}</th><th scope="col">${t("col_last")}</th></tr></thead>
          <tbody>${r.contacts.map(function (c) {
            return html`<tr><td>${who(c.user, gid)}</td><td>${levelPill(c.level, null, { short: false })}</td><td class="r num">${num(c.messages)}</td>
              <td>${c.stages.length ? html`<ol class="stages">${c.stages.map(function (s) { return html`<li>${s}</li>`; })}</ol>` : html`<span class="muted">${t("noStages")}</span>`}</td>
              <td class="nowrap">${timeEl(c.last_at)}</td></tr>`;
          })}</tbody></table></div>` : empty(t("noContacts")), { id: "p-contacts", cls: "panel-wide" })}
        ${panel(t("timeline"), r.timeline.length ? html`<ol class="timeline">${r.timeline.map(function (e) {
          var j = safeUrl(e.jump_url);
          return html`<li class="tl-${e.level || "none"}">
            <span class="tl-dot" aria-hidden="true"></span>
            <div class="tl-meta"><span class="tl-kind">${t("tk_" + e.kind)}</span>${timeEl(e.at)}${e.level ? html`<span class="sr">${t("lvl_" + e.level)}</span>` : ""}</div>
            <p class="tl-text">${e.text}${j ? html` <a href="${j}" target="_blank" rel="noopener noreferrer" class="tl-jump">${icon("ext")}<span class="sr">${t("jump")}</span></a>` : ""}</p>
          </li>`;
        })}</ol>` : empty(t("noTimeline")), { id: "p-tl", cls: "panel-wide" })}
      </div>`;
  }

  // ===================================================================== views: settings
  var BOOLS = ["quote_in_alerts", "auto_delete", "auto_timeout", "warn_targets", "raid_protection", "quarantine_new_accounts", "network_share"];

  function viewSettings(ctx) {
    return api("GET", "/api/guilds/" + ctx.gid + "/settings").then(function (d) {
      var s = d.settings, orig = clone(s);
      ctx.after = function () { wireSettings(ctx.gid, orig); };
      function opt(list, sel, allowNone) {
        return html`${allowNone ? html`<option value="" ${sel == null ? raw("selected") : ""}>${t("none")}</option>` : ""}${list.map(function (x) {
          return html`<option value="${x.id}" ${x.id === sel ? raw("selected") : ""}>${x.name}</option>`;
        })}`;
      }
      function chan(list, sel) { return html`<option value="" ${sel == null ? raw("selected") : ""}>${t("none")}</option>${list.map(function (x) { return html`<option value="${x.id}" ${x.id === sel ? raw("selected") : ""}>#${x.name}</option>`; })}`; }
      function toggle(key, help) {
        return html`<div class="field field-toggle"><input type="checkbox" class="switch" id="s-${key}" name="${key}" ${s[key] ? raw("checked") : ""} ${help ? raw('aria-describedby="d-' + key + '"') : ""}>
          <label for="s-${key}">${t("set_" + key)}</label>${help ? html`<p class="help" id="d-${key}">${help}</p>` : ""}</div>`;
      }
      function select(key, inner) {
        return html`<div class="field"><label for="s-${key}">${t("set_" + key)}</label><select id="s-${key}" name="${key}">${inner}</select></div>`;
      }
      return html`<header class="page-head"><div><h1>${t("settingsTitle")}</h1></div></header>
        <form id="settings" class="settings" novalidate>
          <fieldset class="panel"><legend>${t("g_mode")}</legend>
            <div class="mode-pick">${["observe", "protect"].map(function (mo) {
              return html`<label class="mode-opt"><input type="radio" name="mode" value="${mo}" ${s.mode === mo ? raw("checked") : ""}><span class="mode-body"><b>${t("mode_" + mo)}</b><span>${t("mode_" + mo + "_d")}</span></span></label>`;
            })}</div>
          </fieldset>
          <fieldset class="panel"><legend>${t("g_alerts")}</legend>
            ${select("alert_channel_id", chan(d.channels, s.alert_channel_id))}
            <div class="field"><span class="label" id="l-minlvl">${t("set_alert_min_level")}</span>
              <div class="seg seg-field" role="radiogroup" aria-labelledby="l-minlvl">${["yellow", "red"].map(function (l) {
                return html`<label><input type="radio" name="alert_min_level" value="${l}" ${s.alert_min_level === l ? raw("checked") : ""}><span>${t("lvlFrom_" + l)}</span></label>`;
              })}</div></div>
            ${select("ping_role_id", opt(d.roles, s.ping_role_id, true))}
            ${toggle("quote_in_alerts", t("set_quote_in_alerts_d"))}
          </fieldset>
          <fieldset class="panel"><legend>${t("g_auto")}</legend>
            <p class="help help-top">${t("set_auto_d")}</p>
            ${toggle("auto_delete")}${toggle("auto_timeout")}${toggle("warn_targets")}
          </fieldset>
          <fieldset class="panel"><legend>${t("g_joins")}</legend>
            ${toggle("raid_protection", t("set_raid_protection_d"))}
            ${toggle("quarantine_new_accounts")}
            ${select("quarantine_role_id", opt(d.roles, s.quarantine_role_id, true))}
          </fieldset>
          <fieldset class="panel"><legend>${t("g_minors")}</legend>
            <div class="field"><span class="label" id="l-minor">${t("set_minor_role_ids")}</span>
              <div class="checks" role="group" aria-labelledby="l-minor" aria-describedby="d-minor">${d.roles.map(function (x) {
                return html`<label class="check"><input type="checkbox" name="minor_role_ids" value="${x.id}" ${s.minor_role_ids.indexOf(x.id) >= 0 ? raw("checked") : ""}><span>${x.name}</span></label>`;
              })}</div><p class="help" id="d-minor">${t("set_minor_role_ids_d")}</p></div>
          </fieldset>
          <fieldset class="panel"><legend>${t("g_network")}</legend>${toggle("network_share")}</fieldset>
          <fieldset class="panel"><legend>${t("g_data")}</legend>
            <div class="field"><label for="s-retention_days">${t("set_retention_days")}</label><div class="input-unit"><input type="number" id="s-retention_days" name="retention_days" min="1" step="1" inputmode="numeric" value="${s.retention_days}"><span>${t("days")}</span></div></div>
            ${select("lang", html`<option value="en" ${s.lang === "en" ? raw("selected") : ""}>English</option><option value="sv" ${s.lang === "sv" ? raw("selected") : ""}>Svenska</option>`)}
          </fieldset>
          <div class="savebar" id="savebar" data-dirty="false">
            <span class="savebar-msg" role="status"></span>
            <button type="button" class="btn" data-act="settings-reset">${t("reset")}</button>
            <button type="submit" class="btn btn-primary">${t("save")}</button>
          </div>
        </form>`;
    });
  }

  function wireSettings(gid, orig) {
    var form = document.getElementById("settings"), bar = document.getElementById("savebar"), msg = bar.querySelector(".savebar-msg");
    function read() {
      var f = new FormData(form), out = {};
      out.mode = f.get("mode");
      out.alert_min_level = f.get("alert_min_level");
      ["alert_channel_id", "ping_role_id", "quarantine_role_id"].forEach(function (k) { out[k] = f.get(k) || null; });
      BOOLS.forEach(function (k) { out[k] = form.elements[k].checked; });
      out.minor_role_ids = f.getAll("minor_role_ids");
      out.retention_days = parseInt(f.get("retention_days"), 10);
      out.lang = f.get("lang");
      return out;
    }
    function diff() {
      var cur = read(), d = {};
      Object.keys(cur).forEach(function (k) { if (JSON.stringify(cur[k]) !== JSON.stringify(orig[k])) d[k] = cur[k]; });
      if (d.minor_role_ids && JSON.stringify(cur.minor_role_ids.slice().sort()) === JSON.stringify((orig.minor_role_ids || []).slice().sort())) delete d.minor_role_ids;
      return d;
    }
    function update() {
      var dirty = Object.keys(diff()).length > 0;
      bar.setAttribute("data-dirty", dirty);
      msg.textContent = dirty ? t("unsaved") : "";
    }
    form.addEventListener("input", update);
    form.addEventListener("change", update);
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var d = diff();
      if (d.retention_days !== undefined && !(d.retention_days > 0)) { form.elements.retention_days.focus(); return; }
      if (!Object.keys(d).length) { toast(t("noChanges")); return; }
      var btn = form.querySelector("[type=submit]");
      busy(btn, true); btn.textContent = t("saving");
      api("PUT", "/api/guilds/" + gid + "/settings", d).then(function (res) {
        Object.assign(orig, res.settings || d);
        toast(t("saved"));
        update();
      }).catch(fail).then(function () { busy(btn, false); btn.textContent = t("save"); });
    });
    form.querySelector("[data-act=settings-reset]").addEventListener("click", function () {
      state.focusOnRender = false; state.quiet = true;
      render();
    });
  }

  // ===================================================================== views: report
  function viewReport(ctx) {
    return api("GET", "/api/guilds/" + ctx.gid + "/overview").then(function (o) {
      state.guild = o.guild;
      document.title = t("reportTitle") + " · " + o.guild.name;
      return overviewBody(o, ctx.gid, true);
    });
  }

  // ===================================================================== views: owner
  var ownerSort = { key: "fp_rate", dir: -1 };

  function viewOwner() {
    return api("GET", "/api/owner/overview").then(function (o) {
      current.owner = o;
      return ownerBody(o);
    });
  }

  function ownerBody(o) {
    var s = o.system;
    var tiles = [
      [t("pocket"), s.pocket_online, s.latency_ms && s.latency_ms.pocket],
      [t("guard"), s.guard_online, s.latency_ms && s.latency_ms.guard]
    ];
    var sys = html`<div class="sys">
      ${tiles.map(function (x) {
        return html`<div class="sys-tile ${x[1] ? "is-up" : "is-down"}"><span class="sys-label">${x[0]}</span><span class="sys-state">${icon(x[1] ? "lgreen" : "lred")}${x[1] ? t("online") : t("offline")}</span>${x[2] != null ? html`<span class="sys-sub num">${t("latency", { n: x[2] })}</span>` : ""}</div>`;
      })}
      <dl class="sys-facts">
        <div><dt>${t("uptime")}</dt><dd class="num">${duration(s.uptime_s)}</dd></div>
        <div><dt>${t("version")}</dt><dd class="num">${s.version}</dd></div>
        <div><dt>${t("rules")}</dt><dd>${s.rules}</dd></div>
        <div><dt>${t("database")}</dt><dd class="num">${bytes(s.db_bytes)}</dd></div>
        <div><dt>${t("events")}</dt><dd class="num">${num(s.events_per_min)}</dd></div>
      </dl></div>`;
    var tk = ["guilds", "members", "alerts_open", "alerts_7d", "flagged_7d", "network_flags", "pocket_checks_7d"];
    var totals = html`<dl class="kpis kpis-owner">${tk.map(function (k) { return html`<div class="kpi ${k === "alerts_open" && o.totals[k] ? "kpi-warn" : ""}"><dt>${t("t_" + k)}</dt><dd class="num">${num(o.totals[k])}</dd></div>`; })}</dl>`;
    var pocket = html`<div class="pocket">${["server", "person", "message"].map(function (k) {
      var c = o.pocket[k] || {}, tot = (c.green || 0) + (c.yellow || 0) + (c.red || 0);
      return html`<div class="pocket-row"><span class="pocket-label">${t("pk_" + k)}</span>
        <div class="stack-bar" role="img" aria-label="${t("pk_" + k) + ": " + ["green", "yellow", "red"].map(function (l) { return t("lvl_" + l) + " " + (c[l] || 0); }).join(", ")}">${["green", "yellow", "red"].map(function (l) {
          return c[l] ? html`<span class="seg-${l}" data-w="${tot ? (c[l] / tot * 100).toFixed(2) : 0}"></span>` : "";
        })}</div>
        <span class="pocket-nums num">${["green", "yellow", "red"].map(function (l) { return html`<span class="pn pn-${l}" title="${t("lvl_" + l)}">${icon("l" + l)}${num(c[l] || 0)}</span>`; })}</span></div>`;
    })}</div>`;
    var guilds = o.guilds.length ? html`<div class="table-wrap"><table class="table">
      <thead><tr><th scope="col">${t("col_server")}</th><th scope="col" class="r">${t("t_members")}</th><th scope="col">${t("col_mode")}</th><th scope="col">${t("col_risk")}</th><th scope="col" class="r">${t("col_open")}</th><th scope="col" class="r">${t("col_7d")}</th><th scope="col">${t("col_since")}</th><th scope="col"><span class="sr">${t("actions")}</span></th></tr></thead>
      <tbody>${o.guilds.map(function (g) {
        return html`<tr><td><a href="${route("", g.id)}">${g.name}</a></td><td class="r num">${num(g.members)}</td><td><span class="mode mode-${g.mode}">${t("mode_" + g.mode)}</span></td>
          <td>${levelPill(g.level, g.score)}</td><td class="r num">${num(g.open_alerts)}</td><td class="r num">${num(g.alerts_7d)}</td><td class="nowrap">${date(g.joined_at)}</td>
          <td class="r"><button type="button" class="btn btn-sm btn-danger" data-act="leave" data-gid="${g.id}" data-name="${g.name}">${t("leave")}</button></td></tr>`;
      })}</tbody></table></div>` : empty("–");
    var sq = o.signal_quality.slice().sort(function (a, b) { return (a[ownerSort.key] - b[ownerSort.key]) * ownerSort.dir; });
    function sortTh(key, label) {
      var on = ownerSort.key === key;
      return html`<th scope="col" class="r" aria-sort="${on ? (ownerSort.dir > 0 ? "ascending" : "descending") : "none"}"><button type="button" class="th-sort" data-act="sq-sort" data-key="${key}">${label}${on ? icon(ownerSort.dir > 0 ? "up" : "down", "ic-sort") : ""}</button></th>`;
    }
    var quality = html`<div class="table-wrap"><table class="table">
      <thead><tr><th scope="col">${t("col_signalq")}</th>${sortTh("fired_30d", t("col_fired"))}${sortTh("false_positive", t("col_fp"))}${sortTh("fp_rate", t("col_fprate"))}</tr></thead>
      <tbody>${sq.map(function (x) {
        var tone = x.fp_rate >= 0.3 ? "red" : x.fp_rate >= 0.15 ? "yellow" : "green";
        return html`<tr><td><b>${x.label}</b><div class="sub mono">${x.code}</div></td><td class="r num">${num(x.fired_30d)}</td><td class="r num">${num(x.false_positive)}</td>
          <td class="r"><span class="fp"><span class="fp-bar"><span class="fp-fill fp-${tone}" data-w="${Math.min(100, x.fp_rate * 100).toFixed(1)}"></span></span><span class="num">${pct(x.fp_rate)}</span></span></td></tr>`;
      })}</tbody></table></div>`;
    var network = o.network.length ? html`<div class="table-wrap"><table class="table">
      <thead><tr><th scope="col">${t("col_user")}</th><th scope="col" class="r">${t("col_guilds")}</th><th scope="col">${t("col_reasons")}</th><th scope="col">${t("col_first")}</th><th scope="col"><span class="sr">${t("actions")}</span></th></tr></thead>
      <tbody>${o.network.map(function (x) {
        return html`<tr><td>${who(x.user, null)}<div class="sub mono">${x.user.id}</div></td><td class="r num">${num(x.guilds)}</td><td>${x.reasons.map(function (r) { return html`<span class="chip chip-warn">${r}</span>`; })}</td>
          <td class="nowrap">${timeEl(x.first_at)}</td><td class="r"><button type="button" class="btn btn-sm" data-act="net-clear" data-uid="${x.user.id}" data-name="${splitName(x.user.name).display}">${t("clear")}</button></td></tr>`;
      })}</tbody></table></div>` : empty(t("noNetwork"));
    var sk = ["pocket_checks", "alerts", "flagged", "messages"];
    return html`<header class="page-head"><div><h1>${t("ownerTitle")}</h1><p class="page-meta"><span>Guildward ${s.version}</span></p></div></header>
      <div class="grid grid-owner">
        ${panel(t("system"), sys, { id: "o-sys" })}
        ${panel(t("totals"), totals, { id: "o-tot" })}
        ${panel(t("activity"), html`<div class="charts">${sk.map(function (k) { return chart(t("s_" + k), o.series.days, o.series[k] || [], { type: k === "messages" ? "area" : "bar" }); })}</div>${chartTable(o.series.days, sk.map(function (k) { return [t("s_" + k), o.series[k] || []]; }))}`, { id: "o-act", cls: "panel-wide" })}
        ${panel(t("pocketBreak"), pocket, { id: "o-pocket", cls: "panel-wide" })}
        ${panel(t("guilds"), guilds, { id: "o-guilds", cls: "panel-wide" })}
        ${panel(t("quality"), quality, { id: "o-sq" })}
        ${panel(t("networkTitle"), network, { id: "o-net" })}
      </div>`;
  }

  // Widths from data-w (CSSOM writes are allowed under a strict style CSP).
  function applyWidths(root) {
    root.querySelectorAll("[data-w]").forEach(function (el) { el.style.width = el.getAttribute("data-w") + "%"; });
  }
  new MutationObserver(function () { applyWidths(main); }).observe(main, { childList: true, subtree: true });

  // ===================================================================== actions (delegated)
  function currentGid() { var p = parseHash().parts; return p[0] === "g" ? p[1] : null; }

  var ACTIONS = {
    retry: function () { render(); },
    print: function () { window.print(); },
    lang: function (btn) {
      state.lang = btn.getAttribute("data-v");
      store("gw.lang", state.lang);
      if (document.body.classList.contains("signed-out")) signin(); else { state.focusOnRender = false; state.quiet = true; render(); }
    },
    theme: function () {
      var next = isDark() ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      store("gw.theme", next);
      shell(currentGid(), currentKey());
    },
    logout: function () {
      api("POST", "/api/logout", {}).catch(function () {}).then(function () { signin(); toast(t("signedOut")); });
    },
    fix: function (btn) {
      busy(btn, true);
      api("POST", "/api/guilds/" + currentGid() + "/fix", { fix: btn.getAttribute("data-fix") }).then(function (r) {
        toast(r.text || t("done"));
        state.focusOnRender = false; state.quiet = true;
        render();
      }).catch(function (e) { busy(btn, false); fail(e); });
    },
    alert: function (btn) {
      var action = btn.getAttribute("data-action"), id = btn.getAttribute("data-id"), gid = currentGid();
      needsConfirm(action, btn.getAttribute("data-name")).then(function (ok) {
        if (!ok) return;
        var card = btn.closest(".alert");
        card.querySelectorAll("button").forEach(function (b) { busy(b, true); });
        api("POST", "/api/guilds/" + gid + "/alerts/" + id, { action: action }).then(function (r) {
          toast(t("done"));
          var tmp = document.createElement("div");
          setHTML(tmp, alertItem(r.alert, gid));
          card.replaceWith(tmp.firstElementChild);
          if (r.alert.status !== "open" && state.openAlerts[gid]) { state.openAlerts[gid]--; shell(gid, "alerts"); }
          var next = document.querySelector('[data-alert="' + id + '"] .alert-title');
          if (next) { next.setAttribute("tabindex", "-1"); next.focus(); }
        }).catch(function (e) { card.querySelectorAll("button").forEach(function (b) { busy(b, false); }); fail(e); });
      });
    },
    member: function (btn) {
      var action = btn.getAttribute("data-action"), uidv = btn.getAttribute("data-uid"), gid = currentGid();
      needsConfirm(action, btn.getAttribute("data-name")).then(function (ok) {
        if (!ok) return;
        busy(btn, true);
        api("POST", "/api/guilds/" + gid + "/members/" + uidv, { action: action }).then(function (r) {
          toast(t("done"));
          if (current.report && r.member) {
            Object.assign(current.report.member, r.member);
            setHTML(main, memberBody(current.report, gid));
            wireCharts(main);
            var b = main.querySelector('[data-act=member][data-action="' + action + '"]');
            if (b) b.focus();
          }
        }).catch(function (e) { busy(btn, false); fail(e); });
      });
    },
    leave: function (btn) {
      var name = btn.getAttribute("data-name");
      confirmDialog(t("cLeaveTitle", { name: name }), t("cLeaveBody"), t("leave")).then(function (ok) {
        if (!ok) return;
        busy(btn, true);
        api("POST", "/api/owner/guilds/" + btn.getAttribute("data-gid"), { action: "leave" }).then(function () {
          toast(t("left")); state.focusOnRender = false; state.quiet = true; render();
        }).catch(function (e) { busy(btn, false); fail(e); });
      });
    },
    "net-clear": function (btn) {
      var name = btn.getAttribute("data-name");
      confirmDialog(t("cClearTitle", { name: name }), t("cClearBody"), t("clear")).then(function (ok) {
        if (!ok) return;
        busy(btn, true);
        api("POST", "/api/owner/network/" + btn.getAttribute("data-uid"), { action: "clear" }).then(function () {
          toast(t("cleared")); state.focusOnRender = false; state.quiet = true; render();
        }).catch(function (e) { busy(btn, false); fail(e); });
      });
    },
    "sq-sort": function (btn) {
      var k = btn.getAttribute("data-key");
      ownerSort = ownerSort.key === k ? { key: k, dir: -ownerSort.dir } : { key: k, dir: -1 };
      if (current.owner) {
        setHTML(main, ownerBody(current.owner)); wireCharts(main);
        var b = main.querySelector('[data-act=sq-sort][data-key="' + k + '"]');
        if (b) b.focus();
      }
    }
  };
  function currentKey() { var p = parseHash().parts; return p[0] === "owner" ? "owner" : p[2] || "overview"; }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-act]");
    if (!btn || btn.disabled) return;
    var fn = ACTIONS[btn.getAttribute("data-act")];
    if (fn) { e.preventDefault(); fn(btn); }
  });

  // ===================================================================== theme
  function isDark() {
    var a = document.documentElement.getAttribute("data-theme");
    if (a) return a === "dark";
    return !(window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches);
  }
  var savedTheme = store("gw.theme");
  if (savedTheme === "light" || savedTheme === "dark") document.documentElement.setAttribute("data-theme", savedTheme);

  // ===================================================================== boot
  window.addEventListener("hashchange", function () { document.title = "Guildward Guard"; render(); });
  api("GET", "/api/me").then(function (me) {
    state.me = me;
    if (!state.langChosen && (me.lang === "en" || me.lang === "sv")) state.lang = me.lang;
    state.focusOnRender = false;
    render();
  }).catch(function (e) {
    if (e instanceof ApiError && e.status === 401) return signin();
    document.body.classList.add("signed-out");
    setHTML(main, errorView(e && e.message ? e.message : t("errNetwork"), true));
    ACTIONS.retry = function () { location.reload(); };
  });
})();
