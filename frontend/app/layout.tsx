import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NEXUS — AI Video Factory",
  description:
    "Bezkonkurencyjna platforma multi-agentowa do tworzenia wirusowych wideo. GPT-4o + DALL-E 3 + TTS. Koszt: ~$0.14/wideo.",
  keywords: [
    "AI wideo",
    "generator wideo",
    "TikTok AI",
    "YouTube Shorts",
    "Instagram Reels",
    "multi-agent AI",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pl">
      <body className="antialiased min-h-screen bg-[#0f0f1a]">{children}</body>
    </html>
  );
}
