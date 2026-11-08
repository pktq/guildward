"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useDash } from "./context";
import { ErrorView, Skeleton } from "./ui";

/** /dashboard has no guild in the URL: send the viewer to their first guild, or the owner view. */
export function HomeView() {
  const { me, href, t } = useDash();
  const router = useRouter();
  const target = !me ? null : me.guilds.length ? `/dashboard/g/${encodeURIComponent(me.guilds[0].id)}` : me.owner ? "/dashboard/owner" : null;
  useEffect(() => {
    if (target) router.replace(href(target));
  }, [target, href, router]);
  if (me && !target) return <ErrorView msg={t("noGuilds")} />;
  return <Skeleton />;
}

export function NotFoundView() {
  const { t } = useDash();
  return <ErrorView msg={t("errNotFound")} />;
}
