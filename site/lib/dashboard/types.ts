// Shapes of the Guard dashboard API. Contract: docs/GUARD_API.md.

export type Level = "green" | "yellow" | "red";
export type Severity = "high" | "medium" | "low";
export type Mode = "observe" | "protect";

export type Signal = { code: string; weight: number; severe: boolean; text: string; at: string | null };

export type UserRef = { id: string; name: string; avatar?: string | null; minor?: boolean };

export type MemberStatus = "none" | "watch" | "trusted" | "actioned" | "left";

export type MemberRow = {
  id: string;
  name: string;
  avatar: string | null;
  score: number;
  level: Level;
  status: MemberStatus;
  joined_at: string | null;
  account_age_days: number;
  self_age: number | null;
  minor: boolean;
  flags: string[];
  trend: number;
  last_seen: string | null;
  top_signal: string | null;
};

export type AlertKind = "message" | "member" | "raid" | "report" | "network" | "join";
export type AlertStatus = "open" | "resolved" | "false_positive";

export type Alert = {
  id: number;
  kind: AlertKind;
  level: Level;
  score: number;
  title: string;
  summary: string;
  quote: string | null;
  user: UserRef | null;
  target: UserRef | null;
  signals: Signal[];
  jump_url: string | null;
  status: AlertStatus;
  created_at: string;
  resolved_by: string | null;
  action: string | null;
  /** Moderator who clicked "I'm on it", or null. */
  assigned: UserRef | null;
  /** Note left when the alert was closed (up to 500 characters), or null. */
  note: string | null;
};

/** Dashboard level in one server: view (read only) < act (alerts and members) < admin (settings, fixes, access). */
export type Access = "view" | "act" | "admin";

export type Me = {
  user: { id: string; name: string; avatar: string | null };
  owner: boolean;
  lang?: string;
  guilds: { id: string; name: string; icon: string | null; level: Access }[];
};

export type Series = { days: string[]; [key: string]: string[] | number[] };

export type Kpis = {
  members: number; minors_est: number; at_risk: number; red: number; open_alerts: number;
  flagged_7d: number; messages_7d: number; joins_7d: number; actions_7d: number; median_response_min: number | null;
};

export type GuildInfo = {
  id: string; name: string; icon: string | null; member_count: number; guard_since: string;
  mode: Mode; alert_channel: string | null;
};

export type Overview = {
  guild: GuildInfo;
  health: { score: number; level: Level; grade: string; confidence: string; signals: Signal[] };
  summary: string[];
  recommendations: { severity: Severity; text: string; fix: string | null }[];
  kpis: Kpis;
  series: Series;
  top_risks: MemberRow[];
  recent_alerts: Alert[];
  audit: { id: string; ok: boolean; severity: Severity; label: string; detail: string; fix: string | null }[];
  permissions_missing: string[];
};

export type MemberReport = {
  member: MemberRow & { username?: string; account_created?: string | null; left_at?: string | null; invite_code?: string | null; roles?: string[] };
  verdict: { score: number; level: Level; confidence: string; signals: Signal[] };
  summary: string[];
  prediction: { trajectory: "rising" | "stable" | "falling"; escalation: "none" | "possible" | "likely"; text: string };
  stats: Record<"messages" | "flagged" | "distinct_targets" | "minor_targets" | "reports" | "mod_actions" | "network_flags", number>;
  contacts: { user: UserRef; messages: number; stages: string[]; level: Level; last_at: string | null }[];
  timeline: { at: string; kind: string; text: string; level?: Level | null; jump_url?: string | null }[];
  series: Series;
};

export type Settings = {
  mode: Mode;
  alert_channel_id: string | null;
  alert_min_level: "yellow" | "red";
  ping_role_id: string | null;
  auto_delete: boolean;
  auto_timeout: boolean;
  quarantine_role_id: string | null;
  quarantine_new_accounts: boolean;
  raid_protection: boolean;
  warn_targets: boolean;
  network_share: boolean;
  quote_in_alerts: boolean;
  minor_role_ids: string[];
  retention_days: number;
  lang: "en" | "sv";
  dashboard_roles: Record<string, "view" | "act">;
};

export type SettingsResponse = { settings: Settings; channels: { id: string; name: string }[]; roles: { id: string; name: string }[] };

export type Counts = { green?: number; yellow?: number; red?: number };

export type OwnerOverview = {
  system: {
    uptime_s: number; version: string; rules: string; pocket_online: boolean; guard_online: boolean;
    latency_ms?: { pocket?: number | null; guard?: number | null }; db_bytes: number; events_per_min: number;
    model?: {
      state: "off" | "downloading" | "loading" | "ready" | "failed"; detail?: string; batch_ms_p50?: number | null;
      queue_kids?: number; queue_guard?: number; shed?: number;
    };
  };
  totals: Record<"guilds" | "members" | "alerts_open" | "alerts_7d" | "flagged_7d" | "network_flags" | "pocket_checks_7d", number>;
  crowd?: Record<"users" | "accounts" | "reports_7d" | "review" | "flagged" | "confirmed" | "watch_alerts_7d", number>;
  series: Series;
  pocket: Record<"server" | "person" | "message", Counts>;
  guilds: { id: string; name: string; icon: string | null; members: number; mode: Mode; score: number; level: Level; open_alerts: number; alerts_7d: number; joined_at: string }[];
  signal_quality: { code: string; label: string; fired_30d: number; false_positive: number; fp_rate: number }[];
  network: { user: UserRef; guilds: number; reasons: string[]; first_at: string }[];
};

export type AccountFlag = "none" | "watch" | "flagged" | "confirmed" | "cleared";

export type Account = {
  id: string; name: string; avatar: string | null; created_at: number | null;
  flag: AccountFlag; auto_flag: "none" | "watch" | "flagged"; score: number; level: Level;
  checkers: number; red_checkers: number; reports: number; report_score: number;
  reasons: Record<string, number>; network: number;
  links: { kind: string; other_id: string; other_name: string; other_flag: AccountFlag }[];
  last_seen: number | null; deleted: boolean;
};

export type AccountsResponse = { counts: Record<string, number>; accounts: Account[] };
