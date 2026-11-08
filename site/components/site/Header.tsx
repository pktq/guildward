"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldMark } from "./ShieldMark";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/parents", label: "Parents" },
  { href: "/admins", label: "Servers" },
  { href: "/stats", label: "Stats" },
  { href: "/dashboard", label: "Dashboard" },
] as const;

export function Header() {
  const path = usePathname();
  return (
    <header className="gw-header">
      <Link href="/" className="gw-brand" aria-label="Guildward home">
        <ShieldMark size={30} />
        <span>guildward</span>
      </Link>
      <nav aria-label="Main" className="gw-nav">
        {LINKS.map((l) => (
          <Link key={l.href} href={l.href} className="gw-navlink" aria-current={path === l.href ? "page" : undefined}>
            {l.label}
          </Link>
        ))}
      </nav>
      <Link href="/#install" className="gw-btn gw-btn-accent gw-header-cta">
        Add to Discord
      </Link>
    </header>
  );
}
