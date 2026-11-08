import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0b1220",
      }}
    >
      <svg width="120" height="120" viewBox="0 0 24 24">
        <path d="M12 2l8.5 3.4v6.1c0 5.2-3.5 9.5-8.5 11.3-5-1.8-8.5-6.1-8.5-11.3V5.4L12 2z" fill="#74aee3" />
        <path d="M12 2v20.8c5-1.8 8.5-6.1 8.5-11.3V5.4L12 2z" fill="#2d6aa5" />
      </svg>
    </div>,
    size,
  );
}
