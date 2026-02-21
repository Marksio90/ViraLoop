import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",   // wymagane przez Dockerfile (node server.js)
  experimental: {
    reactCompiler: true,
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "oaidalleapiprodscus.blob.core.windows.net",
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL ?? "http://backend:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
