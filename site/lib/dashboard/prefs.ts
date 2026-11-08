// Per-viewer preferences (language, theme) kept in localStorage, exposed as external stores for
// useSyncExternalStore. Storage can throw (private windows), so an in-memory copy backs it up.

function makeStore(key: string) {
  const subs = new Set<() => void>();
  let mem: string | null | undefined;
  return {
    get(): string | null {
      if (mem !== undefined) return mem;
      try { return localStorage.getItem(key); } catch { return null; }
    },
    set(v: string) {
      mem = v;
      try { localStorage.setItem(key, v); } catch { /* storage unavailable */ }
      subs.forEach((f) => f());
    },
    subscribe(f: () => void) {
      subs.add(f);
      return () => { subs.delete(f); };
    },
  };
}

export const langStore = makeStore("gw.lang");
export const themeStore = makeStore("gw.theme");

export const noopSubscribe = () => () => {};

export function subscribeLight(cb: () => void) {
  const mq = window.matchMedia("(prefers-color-scheme: light)");
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
}
export const prefersLight = () => window.matchMedia("(prefers-color-scheme: light)").matches;
export const navLang = () => (navigator.language || "en").slice(0, 2) === "sv" ? "sv" : "en";
