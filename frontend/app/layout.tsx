/**
 * ViraLoop – Główny layout aplikacji (Root Layout)
 *
 * Next.js 16 App Router z:
 * - React 19.2 + React Compiler (auto-memoizowanie)
 * - Intl (next-intl) dla obsługi 20+ języków
 * - Liveblocks (współpraca w czasie rzeczywistym)
 * - Theme Provider (tryb jasny/ciemny)
 */

import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { Toaster } from "@/components/ui/toaster";
import { QueryProvider } from "@/components/layout/query-provider";
import "./globals.css";

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    template: "%s | ViraLoop",
    default: "ViraLoop – Platforma AI do generowania wirusowych treści wideo",
  },
  description:
    "Twórz, optymalizuj i publikuj wirusowe treści wideo z pomocą AI. " +
    "Kling 3.0, Veo 3.1, algorytmy ewolucyjne i analityka w czasie rzeczywistym.",
  keywords: [
    "AI wideo",
    "generowanie wideo",
    "platforma wideo AI",
    "wirusowe treści",
    "marketing wideo",
  ],
  authors: [{ name: "ViraLoop" }],
  creator: "ViraLoop",
  metadataBase: new URL("https://app.viraloop.pl"),
  openGraph: {
    type: "website",
    locale: "pl_PL",
    alternateLocale: ["en_US", "de_DE", "fr_FR"],
    siteName: "ViraLoop",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
};

export default async function GlownyLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  const wiadomosci = await getMessages();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <NextIntlClientProvider messages={wiadomosci}>
          <QueryProvider>
            {children}
            <Toaster />
          </QueryProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
