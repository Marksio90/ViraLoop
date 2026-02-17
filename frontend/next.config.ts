/**
 * ViraLoop – Konfiguracja Next.js 16
 *
 * Najważniejsze zmiany w Next.js 16 (LTS, październik 2025):
 * - Dyrektywa "use cache" zamiast niejawnego cachowania
 * - Turbopack jako domyślny bundler (dev: 603ms vs 1083ms, prod: 5.7s vs 24.5s)
 * - React Compiler stable (wbudowane auto-memoizowanie)
 * - React 19.2: <Activity>, View Transitions
 *
 * UWAGA BEZPIECZEŃSTWA: CVE-2025-66478 (CVSS 10.0 RCE) – utrzymuj framework aktualny!
 */

import type { NextConfig } from "next";

const nextKonfiguracja: NextConfig = {
  // Eksperymentalne funkcje Next.js 16
  experimental: {
    // React Compiler – automatyczne memoizowanie (stable w Next.js 16)
    reactCompiler: true,
    // Dynamiczny import po stronie serwera
    serverActions: {
      bodySizeLimit: "10mb",
    },
    // Optymalizacja pakietów
    optimizePackageImports: [
      "@tremor/react",
      "recharts",
      "framer-motion",
      "lucide-react",
    ],
  },

  // Turbopack (domyślny w Next.js 16 – 2x szybszy dev startup)
  // Włączony automatycznie przez npm run dev --turbopack

  // Konfiguracja obrazów
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "cdn.viraloop.pl",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "storage.viraloop.pl",
        pathname: "/**",
      },
      // Dopuszczone zewnętrzne źródła miniatur
      {
        protocol: "https",
        hostname: "i.ytimg.com",
      },
      {
        protocol: "https",
        hostname: "*.tiktokcdn.com",
      },
    ],
    formats: ["image/avif", "image/webp"],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
  },

  // Przekierowania i przepisywania
  async rewrites() {
    return [
      // Proxy do API backendu (unika problemów z CORS w deweloperskim)
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },

  // Nagłówki bezpieczeństwa
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          // Bezpieczeństwo EU AI Act – wymóg ujawnienia treści AI
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-XSS-Protection", value: "1; mode=block" },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob: https:",
              "media-src 'self' blob: https:",
              "connect-src 'self' https://api.viraloop.pl wss://liveblocks.io",
              "worker-src 'self' blob:",
              "frame-src 'none'",
            ].join("; "),
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(self), geolocation=()",
          },
        ],
      },
      // Nagłówki WASM dla WebGPU (Diffusion Studio)
      {
        source: "/:path*.wasm",
        headers: [
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
          { key: "Cross-Origin-Embedder-Policy", value: "require-corp" },
        ],
      },
    ];
  },

  // Zmienne środowiskowe dostępne po stronie klienta
  env: {
    NEXT_PUBLIC_APP_NAME: "ViraLoop",
    NEXT_PUBLIC_APP_VERSION: "1.0.0",
  },

  // Kompresja
  compress: true,

  // Generowanie source maps w produkcji (dla monitorowania błędów)
  productionBrowserSourceMaps: false,

  // Pomijanie ESLint podczas build (sprawdzamy oddzielnie w CI)
  eslint: {
    ignoreDuringBuilds: false,
  },

  // TypeScript – pełna ścisłość
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default nextKonfiguracja;
