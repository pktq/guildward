import type { NextConfig } from "next";

// The Guard process (aiohttp) serves the dashboard API. The site proxies it so the session cookie
// stays first-party on the site's own domain.
const GUARD_API_URL = (process.env.GUARD_API_URL || "http://localhost:8091").replace(/\/$/, "");

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${GUARD_API_URL}/api/:path*` },
      { source: "/pocket/:path*", destination: `${GUARD_API_URL}/pocket/:path*` },
    ];
  },
};

export default nextConfig;
