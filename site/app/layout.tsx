import type { Metadata, Viewport } from "next";
import { Figtree, League_Spartan } from "next/font/google";
import "./globals.css";

// Fonts are exposed as CSS variables only; the marketing pages opt in under .gw-site, the dashboard keeps its own.
const display = League_Spartan({ variable: "--gw-font-display", subsets: ["latin"], weight: "700" });
const text = Figtree({ variable: "--gw-font-text", subsets: ["latin"], weight: ["400", "600"] });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.SITE_URL || "http://localhost:3000"),
  title: { default: "Guildward: Discord safety for kids", template: "%s · Guildward" },
  description:
    "A Discord app that lets kids check a server, a person, a message or a link in two clicks, and helps server admins spot grooming and scams. Message text is never stored.",
  applicationName: "Guildward",
  openGraph: { siteName: "Guildward", type: "website" },
};

export const viewport: Viewport = { themeColor: "#0b1220" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${display.variable} ${text.variable} antialiased`}>
      <body>{children}</body>
    </html>
  );
}
