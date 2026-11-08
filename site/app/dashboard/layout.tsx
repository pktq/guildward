import type { Metadata } from "next";
import { Suspense } from "react";
import { DashShell } from "@/components/dashboard/shell";
import "./dashboard.css";

export const metadata: Metadata = {
  title: "Guildward Guard",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

// The shell reads search params and every view loads client-side, so navigations here are not instant by design.
export const instant = false;

// All data loads client-side (the session cookie is HttpOnly + SameSite=Strict), so the shell is the only
// thing prerendered. useSearchParams/useParams in the shell and views need this Suspense boundary.
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="gw-dash"><div className="app"><aside className="side" /><main className="main"><div className="skeleton" aria-busy="true"><div className="sk sk-h" /></div></main></div></div>}>
      <DashShell>{children}</DashShell>
    </Suspense>
  );
}
