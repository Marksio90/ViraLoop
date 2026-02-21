import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ViraLoop — AI Shorts Factory",
  description: "Twórz wirusowe seriale shortsy z AI. Historyczne fabuły, połączone odcinki, automatyczna produkcja.",
  keywords: ["AI wideo", "shorts", "TikTok AI", "YouTube Shorts", "Instagram Reels", "serie historyczne", "automatyzacja"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pl" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <meta name="theme-color" content="#050510" />
      </head>
      <body className="noise grid-bg antialiased">{children}</body>
    </html>
  );
}
