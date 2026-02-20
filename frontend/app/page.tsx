"use client";

import { useState } from "react";
import Link from "next/link";

const AGENCI = [
  {
    ikona: "🧠",
    nazwa: "Strateg Treści",
    model: "GPT-4o-mini",
    opis: "Analizuje brief, tworzy strategiczny plan z optymalnym hakiem",
    koszt: "$0.001",
  },
  {
    ikona: "✍️",
    nazwa: "Pisarz Scenariuszy",
    model: "GPT-4o-mini",
    opis: "Pisze scenariusz scena po scenie z anotacjami wizualnymi",
    koszt: "$0.002",
  },
  {
    ikona: "🎙️",
    nazwa: "Reżyser Głosu",
    model: "OpenAI TTS",
    opis: "Syntezuje profesjonalną narrację z 6 głosami do wyboru",
    koszt: "$0.018",
  },
  {
    ikona: "🎨",
    nazwa: "Producent Wizualny",
    model: "DALL-E 3",
    opis: "Generuje cinematic obrazy 9:16 dla każdej sceny",
    koszt: "$0.120",
  },
  {
    ikona: "🔍",
    nazwa: "Recenzent Jakości",
    model: "GPT-4o",
    opis: "Ocenia i zatwierdza. Jeśli wynik < 60 → automatyczny retry",
    koszt: "$0.005",
  },
];

const PLATFORMY = [
  { ikona: "🎵", nazwa: "TikTok", kolor: "from-pink-500 to-rose-500" },
  { ikona: "▶️", nazwa: "YouTube Shorts", kolor: "from-red-500 to-red-700" },
  { ikona: "📸", nazwa: "Instagram Reels", kolor: "from-purple-500 to-pink-500" },
];

const STATYSTYKI = [
  { wartosc: "~$0.14", etykieta: "Koszt na wideo", ikona: "💰" },
  { wartosc: "~90s", etykieta: "Czas generacji", ikona: "⚡" },
  { wartosc: "0-100", etykieta: "NEXUS Viral Score", ikona: "🔥" },
  { wartosc: "5", etykieta: "Agentów AI", ikona: "🤖" },
];

export default function StronaGlowna() {
  const [aktywnyAgent, setAktywnyAgent] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-[#0f0f1a] text-white">
      {/* Tło z gradientem */}
      <div className="fixed inset-0 bg-gradient-to-br from-indigo-950/30 via-[#0f0f1a] to-purple-950/20 pointer-events-none" />

      {/* Nawigacja */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-5 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-xl font-black">
            N
          </div>
          <span className="text-xl font-black tracking-tight">
            <span className="gradient-text">NEXUS</span>
          </span>
        </div>

        <div className="flex items-center gap-4">
          <Link
            href="/studio"
            className="nexus-button text-sm"
          >
            Otwórz Studio →
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <main className="relative z-10 max-w-7xl mx-auto px-8 pt-20 pb-32">
        {/* Badge */}
        <div className="flex justify-center mb-8">
          <span className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-sm px-4 py-1.5 rounded-full">
            <span className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
            Na kluczu OpenAI — 100% polska platforma
          </span>
        </div>

        {/* Tytuł */}
        <div className="text-center mb-16">
          <h1 className="text-6xl md:text-8xl font-black tracking-tight mb-6 leading-none">
            <span className="gradient-text">AI Video</span>
            <br />
            <span className="text-white">Factory</span>
          </h1>

          <p className="text-xl text-white/60 max-w-2xl mx-auto leading-relaxed mb-8">
            5 agentów AI. 1 brief. Kompletne wideo wirusowe w 90 sekund.
            <br />
            Scenariusz → Głos → DALL-E 3 → Recenzja → MP4 gotowy do publikacji.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/studio" className="nexus-button text-lg px-8 py-4">
              🚀 Stwórz pierwsze wideo
            </Link>
            <Link
              href="/analityka"
              className="text-white/60 hover:text-white transition-colors px-6 py-4 text-lg"
            >
              Analityka →
            </Link>
          </div>
        </div>

        {/* Statystyki */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-20">
          {STATYSTYKI.map((stat) => (
            <div key={stat.etykieta} className="nexus-card text-center">
              <div className="text-3xl mb-2">{stat.ikona}</div>
              <div className="text-3xl font-black gradient-text">{stat.wartosc}</div>
              <div className="text-white/50 text-sm mt-1">{stat.etykieta}</div>
            </div>
          ))}
        </div>

        {/* Pipeline Multi-Agentowy */}
        <div className="mb-20">
          <h2 className="text-3xl font-black text-center mb-3">
            Pipeline <span className="gradient-text">Multi-Agentowy</span>
          </h2>
          <p className="text-white/50 text-center mb-10">
            5 wyspecjalizowanych agentów AI orkiestrowanych przez LangGraph
          </p>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {AGENCI.map((agent, i) => (
              <div
                key={agent.nazwa}
                className={`nexus-card cursor-pointer transition-all duration-300 ${
                  aktywnyAgent === i
                    ? "border-indigo-500/50 bg-indigo-500/10"
                    : "hover:border-indigo-500/30"
                }`}
                onMouseEnter={() => setAktywnyAgent(i)}
                onMouseLeave={() => setAktywnyAgent(null)}
              >
                {/* Numer kroku */}
                {i < 4 && (
                  <div className="hidden md:block absolute -right-2 top-1/2 -translate-y-1/2 z-10 text-white/30 text-lg">
                    →
                  </div>
                )}

                <div className="text-3xl mb-3">{agent.ikona}</div>
                <div className="text-xs text-indigo-400 font-bold mb-1">
                  Krok {i + 1}
                </div>
                <div className="font-bold mb-1">{agent.nazwa}</div>
                <div className="text-xs text-purple-400 mb-3 font-mono">
                  {agent.model}
                </div>
                <p className="text-white/50 text-xs leading-relaxed">{agent.opis}</p>
                <div className="mt-3 text-green-400 text-xs font-mono">
                  ~{agent.koszt}/wideo
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Platformy */}
        <div className="mb-20">
          <h2 className="text-3xl font-black text-center mb-10">
            Optymalizacja per <span className="gradient-text">Platforma</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {PLATFORMY.map((platforma) => (
              <div key={platforma.nazwa} className="nexus-card text-center">
                <div
                  className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${platforma.kolor} flex items-center justify-center text-3xl mx-auto mb-4`}
                >
                  {platforma.ikona}
                </div>
                <h3 className="text-xl font-bold mb-2">{platforma.nazwa}</h3>
              </div>
            ))}
          </div>
        </div>

        {/* NVS Score */}
        <div className="nexus-card text-center max-w-2xl mx-auto">
          <h2 className="text-2xl font-black mb-4">
            NEXUS Viral Score <span className="gradient-text">(NVS)</span>
          </h2>
          <p className="text-white/60 mb-6">
            Predykcja wiralności przed publikacją. Oceniamy hak, retencję,
            udostępnialność i optymalizację platformy.
          </p>
          <div className="flex justify-center gap-6">
            <div className="text-center">
              <div className="score-high mb-1">🔥 85-100</div>
              <div className="text-white/50 text-xs">Wysoki potencjał</div>
            </div>
            <div className="text-center">
              <div className="score-good mb-1">✅ 60-84</div>
              <div className="text-white/50 text-xs">Dobry content</div>
            </div>
            <div className="text-center">
              <div className="score-warn mb-1">⚠️ &lt;60</div>
              <div className="text-white/50 text-xs">Auto-retry</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
