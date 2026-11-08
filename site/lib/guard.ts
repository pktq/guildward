import { cacheLife } from "next/cache";
import sample from "@/public/demo/stats.json";

export const GUARD_API_URL = (process.env.GUARD_API_URL || "http://localhost:8091").replace(/\/$/, "");

type Levels = { green: number; yellow: number; red: number };

/** GET /api/public/stats: deployment-wide counts only (see docs/GUARD_API.md). */
export type PublicStats = {
  generated_at: string;
  since: string | null;
  servers: number;
  members: number;
  guard: {
    messages: number; flagged: number; alerts: number; red_alerts: number; resolved: number;
    actions: number; raids: number; reports: number; kids_warned: number; network_flags: number;
  };
  pocket: {
    users: number; checks: number; by_kind: { server: Levels; person: Levels; message: Levels };
    scans: number; watch_alerts: number; reports: number; flagged_accounts: number;
  };
  signals: { code: string; label: string; n: number }[];
  series: { days: string[]; messages: number[]; flagged: number[]; alerts: number[]; pocket_checks: number[] };
};

/** Live stats from the Guard API, or the bundled sample (from `guildward simulate`) when it's unreachable. */
export async function getPublicStats(): Promise<{ stats: PublicStats; live: boolean }> {
  "use cache";
  cacheLife("minutes");
  try {
    const r = await fetch(`${GUARD_API_URL}/api/public/stats`, { signal: AbortSignal.timeout(3000) });
    if (r.ok) return { stats: (await r.json()) as PublicStats, live: true };
  } catch {
    // fall through to the sample
  }
  return { stats: sample as PublicStats, live: false };
}
