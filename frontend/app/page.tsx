"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

const AGENCI = [
  {
    ikona: "🧠",
    kolor: "from-violet-500 to-purple-600",
    nazwa: "Strateg Narracji",
    model: "GPT-4o",
    opis: "Projektuje łuk fabularny, haki emocjonalne i cliffhangery między odcinkami",
    krok: "01",
  },
  {
    ikona: "✍️",
    kolor: "from-blue-500 to-cyan-500",
    nazwa: "Pisarz Scenariuszy",
    model: "GPT-4o",
    opis: "Pisze pełny scenariusz z dialogami, opisami scen i animowanymi napisami",
    krok: "02",
  },
  {
    ikona: "🎙️",
    kolor: "from-emerald-500 to-teal-500",
    nazwa: "Reżyser Głosu",
    model: "OpenAI TTS",
    opis: "Generuje profesjonalną narrację z segmentami czasowymi dla karaoke",
    krok: "03",
  },
  {
    ikona: "🎨",
    kolor: "from-orange-500 to-amber-500",
    nazwa: "Producent Wizualny",
    model: "DALL-E 3",
    opis: "Tworzy spójne wizualnie klatki 9:16 z dynamicznym oświetleniem i stylem",
    krok: "04",
  },
  {
    ikona: "🎬",
    kolor: "from-rose-500 to-pink-600",
    nazwa: "Montażysta AI",
    model: "FFmpeg + AI",
    opis: "Scala animowane napisy, efekty Ken Burns, przejścia i muzykę w gotowe MP4",
    krok: "05",
  },
  {
    ikona: "📡",
    kolor: "from-indigo-500 to-violet-600",
    nazwa: "Analityk Wiralności",
    model: "GPT-4o-mini",
    opis: "Predykcja NEXUS Viral Score i optymalizacja pod TikTok/YT/Reels algorytmy",
    krok: "06",
  },
];

const GATUNKI = [
  { emoji: "⚔️", tytul: "Tajemnice Historii", opis: "Zapomniane sekrety i spiski", gradient: "from-amber-900/60 to-red-900/60" },
  { emoji: "🔬", tytul: "Nauka i Odkrycia", opis: "Przełomowe momenty ludzkości", gradient: "from-cyan-900/60 to-blue-900/60" },
  { emoji: "👑", tytul: "Wielkie Imperia", opis: "Powstanie i upadek cywilizacji", gradient: "from-purple-900/60 to-violet-900/60" },
  { emoji: "🕵️", tytul: "Zbrodnie i Sekrety", opis: "Nierozwiązane zagadki i misterium", gradient: "from-slate-900/60 to-zinc-800/60" },
  { emoji: "🚀", tytul: "Wyścig Technologii", opis: "Od ognia do AI — historia techniki", gradient: "from-emerald-900/60 to-teal-900/60" },
  { emoji: "💰", tytul: "Fortuna i Bankructwo", opis: "Wzloty i upadki finansowych imperiów", gradient: "from-yellow-900/60 to-orange-900/60" },
];

const STATS = [
  { value: "6", label: "Agentów AI", sub: "pracujących równolegle" },
  { value: "~$0.15", label: "Koszt odcinka", sub: "DALL-E 3 + GPT-4o + TTS" },
  { value: "9:16", label: "Format natywny", sub: "TikTok • YT Shorts • Reels" },
  { value: "∞", label: "Serie odcinków", sub: "połączone cliffhangerami" },
];

const PRZYKLADOWE_SERIE = [
  { tytul: "Sekrety Watykanu", odcinki: 8, wyswietlenia: "2.1M", emoji: "⛪" },
  { tytul: "Tesla vs Edison", odcinki: 5, wyswietlenia: "890K", emoji: "⚡" },
  { tytul: "Zaginiony skarb Templa", odcinki: 12, wyswietlenia: "4.3M", emoji: "💎" },
];

export default function StronaGlowna() {
  const [aktywnyAgent, setAktywnyAgent] = useState<number | null>(null);
  const [tekst, setTekst] = useState("");
  const PELNY_TEKST = "Sekrety Watykanu — 8-odcinkowa seria o ukrytych archiwach";

  useEffect(() => {
    let i = 0;
    const interval = setInterval(() => {
      if (i <= PELNY_TEKST.length) {
        setTekst(PELNY_TEKST.slice(0, i));
        i++;
      } else {
        clearInterval(interval);
      }
    }, 50);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen relative" style={{ background: "var(--c-bg)" }}>
      {/* Orbs tła */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full opacity-20"
          style={{ background: "radial-gradient(circle, #7c3aed 0%, transparent 70%)" }} />
        <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full opacity-15"
          style={{ background: "radial-gradient(circle, #06b6d4 0%, transparent 70%)" }} />
        <div className="absolute top-[40%] left-[50%] w-[300px] h-[300px] rounded-full opacity-10"
          style={{ background: "radial-gradient(circle, #f59e0b 0%, transparent 70%)" }} />
      </div>

      {/* NAV */}
      <nav className="relative z-20 flex items-center justify-between px-6 md:px-10 py-5 border-b"
        style={{ borderColor: "var(--c-border)", background: "rgba(5,5,16,0.8)", backdropFilter: "blur(20px)" }}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center font-black text-white text-sm"
            style={{ background: "linear-gradient(135deg, #7c3aed, #06b6d4)" }}>
            VL
          </div>
          <span className="text-lg font-bold tracking-tight">
            Vira<span className="gradient-text-2">Loop</span>
          </span>
          <span className="badge badge-purple ml-2">BETA</span>
        </div>

        <div className="hidden md:flex items-center gap-6">
          <Link href="/serie" className="btn-ghost text-sm">Serie</Link>
          <Link href="/analityka" className="btn-ghost text-sm">Analityka</Link>
          <Link href="/studio" className="btn-primary" style={{ padding: "10px 20px", fontSize: "14px" }}>
            Otwórz Studio →
          </Link>
        </div>

        <Link href="/studio" className="md:hidden btn-primary" style={{ padding: "8px 16px", fontSize: "13px" }}>
          Studio →
        </Link>
      </nav>

      {/* HERO */}
      <main className="relative z-10">
        <section className="max-w-7xl mx-auto px-6 md:px-10 pt-20 pb-24 text-center">
          <div className="flex justify-center mb-6">
            <span className="badge badge-cyan">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse inline-block" />
              Automatyczna produkcja seriali shortsy z AI
            </span>
          </div>

          <h1 className="text-5xl md:text-7xl lg:text-8xl font-black tracking-tight leading-none mb-6">
            <span className="gradient-text">Seriale Shortsy</span>
            <br />
            <span className="text-white">Które Uzależniają</span>
          </h1>

          <p className="text-lg md:text-xl max-w-2xl mx-auto mb-4" style={{ color: "var(--c-muted)" }}>
            Wybierz temat. AI tworzy powiązane odcinki z cliffhangerami, animowanymi napisami
            i dynamiczną muzyką — gotowe do publikacji na TikTok, YT Shorts i Reels.
          </p>

          {/* Demo typing */}
          <div className="inline-flex items-center gap-3 glass px-5 py-3 mb-10 text-left">
            <span style={{ color: "var(--c-muted)", fontSize: 13 }}>Twój temat:</span>
            <span className="font-mono text-sm" style={{ color: "#a78bfa" }}>
              {tekst}<span className="animate-pulse">|</span>
            </span>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/studio" className="btn-primary" style={{ fontSize: "16px", padding: "15px 32px" }}>
              🎬 Stwórz pierwszą serię
            </Link>
            <Link href="/serie" className="btn-secondary" style={{ fontSize: "16px" }}>
              Przeglądaj serie →
            </Link>
          </div>
        </section>

        {/* STATS */}
        <section className="max-w-7xl mx-auto px-6 md:px-10 pb-20">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {STATS.map((s) => (
              <div key={s.label} className="glass p-6 text-center card-hover">
                <div className="stat-number text-3xl md:text-4xl gradient-text mb-1">{s.value}</div>
                <div className="font-semibold text-sm mb-1">{s.label}</div>
                <div className="text-xs" style={{ color: "var(--c-muted)" }}>{s.sub}</div>
              </div>
            ))}
          </div>
        </section>

        {/* PIPELINE */}
        <section className="max-w-7xl mx-auto px-6 md:px-10 pb-24">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-black mb-3">
              6 Agentów AI — <span className="gradient-text">1 Przycisk</span>
            </h2>
            <p style={{ color: "var(--c-muted)" }}>
              Wieloagentowy pipeline z równoległym wykonaniem i automatycznym retry
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {AGENCI.map((agent, i) => (
              <div
                key={agent.nazwa}
                className="glass p-6 card-hover relative overflow-hidden"
                style={{ borderColor: aktywnyAgent === i ? "rgba(124,58,237,0.4)" : "var(--c-border)" }}
                onMouseEnter={() => setAktywnyAgent(i)}
                onMouseLeave={() => setAktywnyAgent(null)}
              >
                <div className="absolute top-4 right-4 font-mono text-xs font-bold"
                  style={{ color: "var(--c-muted)" }}>
                  {agent.krok}
                </div>

                {/* Icon */}
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${agent.kolor} flex items-center justify-center text-2xl mb-4`}>
                  {agent.ikona}
                </div>

                <div className="font-bold text-base mb-1">{agent.nazwa}</div>
                <div className="badge badge-purple mb-3 text-xs">{agent.model}</div>
                <p className="text-sm leading-relaxed" style={{ color: "var(--c-muted)" }}>{agent.opis}</p>

                {/* Active glow */}
                {aktywnyAgent === i && (
                  <div className="absolute inset-0 pointer-events-none rounded-[var(--r-card)]"
                    style={{ background: "linear-gradient(135deg, rgba(124,58,237,0.05), transparent)" }} />
                )}
              </div>
            ))}
          </div>
        </section>

        {/* GATUNKI */}
        <section className="max-w-7xl mx-auto px-6 md:px-10 pb-24">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-black mb-3">
              Gatunki <span className="gradient-text">Które Działają</span>
            </h2>
            <p style={{ color: "var(--c-muted)" }}>
              Sprawdzone formaty narracyjne generujące miliony wyświetleń
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {GATUNKI.map((g) => (
              <Link href={`/studio?gatunek=${encodeURIComponent(g.tytul)}`} key={g.tytul}>
                <div className={`relative overflow-hidden rounded-2xl p-6 h-40 cursor-pointer card-hover bg-gradient-to-br ${g.gradient} border`}
                  style={{ borderColor: "var(--c-border)" }}>
                  <div className="text-4xl mb-3">{g.emoji}</div>
                  <div className="font-bold text-base">{g.tytul}</div>
                  <div className="text-sm mt-1" style={{ color: "var(--c-muted)" }}>{g.opis}</div>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* PRZYKŁADOWE SERIE */}
        <section className="max-w-7xl mx-auto px-6 md:px-10 pb-24">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-2xl md:text-3xl font-black">
              Przykłady <span className="gradient-text">Gotowych Serii</span>
            </h2>
            <Link href="/serie" className="btn-ghost">
              Wszystkie →
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {PRZYKLADOWE_SERIE.map((s) => (
              <div key={s.tytul} className="glass p-6 card-hover">
                <div className="text-4xl mb-4">{s.emoji}</div>
                <h3 className="font-bold text-lg mb-2">{s.tytul}</h3>
                <div className="flex items-center gap-4 text-sm" style={{ color: "var(--c-muted)" }}>
                  <span>{s.odcinki} odcinków</span>
                  <span className="text-emerald-400 font-semibold">{s.wyswietlenia} wyśw.</span>
                </div>
                <div className="progress-bar mt-4">
                  <div className="progress-fill" style={{ width: `${Math.random() * 40 + 60}%` }} />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="max-w-3xl mx-auto px-6 md:px-10 pb-32 text-center">
          <div className="glass p-10 md:p-14 relative overflow-hidden animate-pulse-glow">
            <div className="absolute inset-0 pointer-events-none"
              style={{ background: "radial-gradient(circle at 50% 0%, rgba(124,58,237,0.15), transparent 70%)" }} />

            <h2 className="text-3xl md:text-4xl font-black mb-4 relative">
              Gotowy żeby <span className="gradient-text">startować?</span>
            </h2>
            <p className="mb-8 relative" style={{ color: "var(--c-muted)" }}>
              Wpisz temat serii. AI zajmie się resztą — od scenariusza po gotowe pliki MP4.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center relative">
              <Link href="/studio" className="btn-primary" style={{ fontSize: "16px", padding: "16px 36px" }}>
                🚀 Zacznij teraz — za darmo
              </Link>
              <Link href="/analityka" className="btn-secondary">
                Sprawdź analitykę
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="border-t px-6 md:px-10 py-8" style={{ borderColor: "var(--c-border)" }}>
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-black text-white"
              style={{ background: "linear-gradient(135deg, #7c3aed, #06b6d4)" }}>
              VL
            </div>
            <span className="font-semibold">ViraLoop</span>
            <span className="text-xs" style={{ color: "var(--c-muted)" }}>— AI Shorts Factory</span>
          </div>
          <div className="flex items-center gap-6 text-sm" style={{ color: "var(--c-muted)" }}>
            <Link href="/studio" className="hover:text-white transition-colors">Studio</Link>
            <Link href="/serie" className="hover:text-white transition-colors">Serie</Link>
            <Link href="/analityka" className="hover:text-white transition-colors">Analityka</Link>
            <span>OpenAI Powered</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
