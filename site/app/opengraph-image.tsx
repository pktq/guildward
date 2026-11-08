import { ImageResponse } from "next/og";

export const alt = "Guildward: a Discord safety app. Is this sketchy? Ask first.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const SHIELD = "M12 2l8.5 3.4v6.1c0 5.2-3.5 9.5-8.5 11.3-5-1.8-8.5-6.1-8.5-11.3V5.4L12 2z";
const HALF = "M12 2v20.8c5-1.8 8.5-6.1 8.5-11.3V5.4L12 2z";

export default function Image() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: "#0b1220",
        color: "#ffffff",
        padding: "72px 80px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 20, fontSize: 44, fontWeight: 700 }}>
        <svg width="64" height="64" viewBox="0 0 24 24">
          <path d={SHIELD} fill="#74aee3" />
          <path d={HALF} fill="#2d6aa5" />
        </svg>
        guildward
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
        <div style={{ fontSize: 120, fontWeight: 700, letterSpacing: -4, lineHeight: 1 }}>Is this sketchy?</div>
        <div style={{ fontSize: 36, color: "#b9c3d6", maxWidth: 900, lineHeight: 1.3 }}>
          Kids check a server, a person, a message or a link on Discord and get a plain answer: why, and what to do.
        </div>
      </div>
      <div style={{ display: "flex", gap: 14 }}>
        {["#2ea043", "#d29922", "#da3633"].map((c) => (
          <div key={c} style={{ width: 28, height: 28, borderRadius: 14, background: c }} />
        ))}
      </div>
    </div>,
    size,
  );
}
