import type { NextConfig } from "next";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:8000";
const isStaticExport = process.env.NEXT_OUTPUT_EXPORT === "true";

const nextConfig: NextConfig = {
  basePath,
  ...(isStaticExport ? { output: "export" as const } : {}),
  async rewrites() {
    if (isStaticExport) return [];
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/ws/:path*",
        destination: `${backendUrl}/ws/:path*`,
      },
    ];
  },
  allowedDevOrigins: ['192.168.5.52'],
};

export default nextConfig;
