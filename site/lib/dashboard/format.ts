import type { Lang } from "./i18n";

const loc = (lang: Lang) => (lang === "sv" ? "sv-SE" : "en-GB");

export function num(lang: Lang, n: number | null | undefined) {
  return n == null ? "–" : new Intl.NumberFormat(loc(lang)).format(n);
}
export function pct(lang: Lang, x: number) {
  return new Intl.NumberFormat(loc(lang), { style: "percent", maximumFractionDigits: 0 }).format(x || 0);
}
export function date(lang: Lang, iso: string | null | undefined, withTime = false) {
  if (!iso) return "–";
  const o: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" };
  if (withTime) { o.hour = "2-digit"; o.minute = "2-digit"; }
  return new Intl.DateTimeFormat(loc(lang), o).format(new Date(iso));
}
export function day(lang: Lang, isoDay: string) {
  return new Intl.DateTimeFormat(loc(lang), { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(isoDay + "T00:00:00Z"));
}
export function rel(lang: Lang, iso: string | null | undefined) {
  if (!iso) return "–";
  const diff = (new Date(iso).getTime() - Date.now()) / 1000;
  const f = new Intl.RelativeTimeFormat(loc(lang), { numeric: "auto", style: "short" });
  const a = Math.abs(diff);
  if (a < 60) return f.format(Math.round(diff), "second");
  if (a < 3600) return f.format(Math.round(diff / 60), "minute");
  if (a < 86400) return f.format(Math.round(diff / 3600), "hour");
  if (a < 86400 * 45) return f.format(Math.round(diff / 86400), "day");
  return date(lang, iso);
}
export function bytes(lang: Lang, n: number) {
  const u = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return new Intl.NumberFormat(loc(lang), { maximumFractionDigits: 1 }).format(n) + " " + u[i];
}
export function duration(s: number) {
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return (d ? d + "d " : "") + (d || h ? h + "h " : "") + m + "m";
}
export const unixIso = (sec: number | null | undefined) => (sec ? new Date(sec * 1000).toISOString() : null);

// jump_url is rendered as a link only when it points at Discord over https (same allowlist as the legacy SPA).
export function safeUrl(u: unknown): string | null {
  return typeof u === "string" && /^https:\/\/((ptb|canary)\.)?discord(app)?\.com\//.test(u) ? u : null;
}

export { splitName } from "./api";
