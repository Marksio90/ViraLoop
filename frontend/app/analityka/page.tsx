"use client";

import { useState } from "react";
import Link from "next/link";

interface WynikWiralnosci {
  wynik_nwv: number;
  wynik_haka: number;
  wynik_zatrzymania: number;
  wynik_udostepnialnosci: number;
  wynik_platformy: Record<string, number>;
  odznaka: string;
  uzasadnienie: string;
  wskazowki_optymalizacji: string[];
}

const PRZYKŁADY = [
  "Tajemnica zaginięcia Kolumny Fararona — 3 teorie których nie znasz",
  "Jak Tesla był skazany na zapomnienie przez Edisona i JP Morgana",
  "3 decyzje które doprowadziły do upadku Cesarstwa Rzymskiego",
  "Sekrety piramid których szkoła ci nie powiedziała",
];

function ScoreMeter({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-2">
        <span style={{ color: "var(--c-muted)" }}>{label}</span>
        <span className="font-bold">{value}/100</span>
      </div>
      <div className="h-2 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${value}%`, background: color }}
        />
      </div>
    </div>
  );
}

function getNVSColor(nwv: number) {
  if (nwv >= 85) return "#10b981";
  if (nwv >= 60) return "#f59e0b";
  return "#ef4444";
}

export default function AnalitikaPage() {
  const [brief, setBrief] = useState("");
  const [platformy, setPlatformy] = useState<string[]>(["tiktok", "youtube"]);
  const [dlugosc, setDlugosc] = useState(60);
  const [ladowanie, setLadowanie] = useState(false);
  const [wynik, setWynik] = useState<WynikWiralnosci | null>(null);
  const [historia, setHistoria] = useState<{ brief: string; nwv: number }[]>([]);

  const analizuj = async () => {
    if (brief.trim().length < 10) return;
    setLadowanie(true);
    setWynik(null);

    try {
      const res = await fetch("/api/v1/wideo/wiralnosc", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief, platforma: platformy, dlugosc_sekund: dlugosc }),
      });

      if (!res.ok) throw new Error();
      const dane: WynikWiralnosci = await res.json();
      setWynik(dane);
      setHistoria(prev => [{ brief: brief.slice(0, 50), nwv: dane.wynik_nwv }, ...prev.slice(0, 5)]);
    } catch {
      // Demo fallback
      const nwv = Math.floor(62 + Math.random() * 28);
      const mock: WynikWiralnosci = {
        wynik_nwv: nwv,
        wynik_haka: Math.floor(nwv - 5 + Math.random() * 15),
        wynik_zatrzymania: Math.floor(nwv - 8 + Math.random() * 12),
        wynik_udostepnialnosci: Math.floor(nwv - 10 + Math.random() * 18),
        wynik_platformy: {
          tiktok: Math.floor(nwv + Math.random() * 10),
          youtube: Math.floor(nwv - 5 + Math.random() * 10),
          instagram: Math.floor(nwv - 8 + Math.random() * 10),
        },
        odznaka: nwv >= 85 ? "🔥 Wysoki potencjał wiralny" : nwv >= 60 ? "✅ Dobry content" : "⚠️ Wymaga optymalizacji",
        uzasadnienie: "Demo mode — wyniki szacunkowe (backend offline)",
        wskazowki_optymalizacji: [
          "Zacznij od szokującego pytania lub faktu w pierwszych 3 sekundach",
          "Dodaj animowany tekst na ekranie — zwiększa retencję o ~40%",
          "Zakończ z cliffhangerem do następnego odcinka serii",
          "Skróć tytuł do max 8 słów — lepszy CTR na YT Shorts",
        ],
      };
      setWynik(mock);
      setHistoria(prev => [{ brief: brief.slice(0, 50), nwv }, ...prev.slice(0, 5)]);
    } finally {
      setLadowanie(false);
    }
  };

  return (
    <div className="min-h-screen relative" style={{ background: "var(--c-bg)" }}>
      {/* Orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 right-0 w-[350px] h-[350px] rounded-full opacity-10"
          style={{ background: "radial-gradient(circle, #7c3aed 0%, transparent 70%)" }} />
        <div className="absolute bottom-0 left-0 w-[250px] h-[250px] rounded-full opacity-10"
          style={{ background: "radial-gradient(circle, #06b6d4 0%, transparent 70%)" }} />
      </div>

      {/* NAV */}
      <nav className="relative z-20 flex items-center justify-between px-6 py-4 border-b"
        style={{ borderColor: "var(--c-border)", background: "rgba(5,5,16,0.9)", backdropFilter: "blur(20px)" }}>
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-black text-white"
            style={{ background: "linear-gradient(135deg, #7c3aed, #06b6d4)" }}>
            VL
          </div>
          <span className="font-bold">ViraLoop</span>
        </Link>
        <div className="flex items-center gap-3">
          <Link href="/studio" className="btn-ghost text-sm">Studio</Link>
          <Link href="/serie" className="btn-ghost text-sm">Serie</Link>
        </div>
      </nav>

      <div className="relative z-10 max-w-5xl mx-auto px-4 md:px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-black mb-2">
            Silnik <span className="gradient-text">Wiralności</span>
          </h1>
          <p style={{ color: "var(--c-muted)" }}>
            Predykcja NEXUS Viral Score przed stworzeniem wideo. Analizuj i optymalizuj brief zanim wydasz pieniądze.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Lewa — formularz */}
          <div className="space-y-4">
            <div className="glass p-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider mb-2"
                  style={{ color: "var(--c-muted)" }}>
                  Brief / Temat wideo
                </label>
                <textarea
                  className="input-premium"
                  placeholder="Opisz temat wideo lub odcinka serii..."
                  value={brief}
                  onChange={e => setBrief(e.target.value)}
                  rows={4}
                  disabled={ladowanie}
                />
              </div>

              {/* Quick examples */}
              <div>
                <p className="text-xs mb-2" style={{ color: "var(--c-muted)" }}>Przykłady:</p>
                <div className="flex flex-wrap gap-2">
                  {PRZYKŁADY.map(p => (
                    <button
                      key={p}
                      onClick={() => setBrief(p)}
                      className="tag"
                    >
                      {p.slice(0, 35)}…
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Platformy + długość */}
            <div className="glass p-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold mb-2" style={{ color: "var(--c-muted)" }}>
                  Platformy docelowe
                </label>
                <div className="flex flex-wrap gap-2">
                  {["tiktok", "youtube", "instagram"].map(p => (
                    <button
                      key={p}
                      onClick={() => setPlatformy(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p])}
                      className={`platform-pill ${platformy.includes(p) ? `active-${p}` : "inactive"}`}
                    >
                      {p === "tiktok" ? "🎵 TikTok" : p === "youtube" ? "▶️ YouTube" : "📸 Instagram"}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold mb-2" style={{ color: "var(--c-muted)" }}>
                  Długość: <span className="text-white font-bold">{dlugosc}s</span>
                </label>
                <input
                  type="range" min={15} max={180} step={15} value={dlugosc}
                  onChange={e => setDlugosc(+e.target.value)}
                  className="w-full accent-violet-500"
                  disabled={ladowanie}
                />
              </div>
            </div>

            <button
              onClick={analizuj}
              disabled={ladowanie || brief.trim().length < 10}
              className="btn-primary w-full justify-center"
              style={{ padding: "15px", fontSize: 15, opacity: brief.trim().length < 10 ? 0.5 : 1 }}
            >
              {ladowanie ? (
                <><svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z" />
                </svg> Analizuję...</>
              ) : "🔮 Analizuj wiralność"}
            </button>

            {/* Historia */}
            {historia.length > 0 && (
              <div className="glass p-4">
                <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: "var(--c-muted)" }}>
                  Historia analiz
                </p>
                <div className="space-y-2">
                  {historia.map((h, i) => (
                    <div key={i} className="flex items-center justify-between py-2 border-b" style={{ borderColor: "var(--c-border)" }}>
                      <span className="text-xs truncate max-w-[200px]" style={{ color: "var(--c-muted)" }}>{h.brief}…</span>
                      <span className="font-bold text-sm ml-2" style={{ color: getNVSColor(h.nwv) }}>
                        {h.nwv}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Prawa — wyniki */}
          <div>
            {!wynik && !ladowanie && (
              <div className="glass p-10 h-full flex flex-col items-center justify-center text-center">
                <div className="text-5xl mb-4">🔮</div>
                <h3 className="font-bold text-lg mb-2">Predykcja NVS</h3>
                <p className="text-sm" style={{ color: "var(--c-muted)" }}>
                  Wpisz brief i kliknij Analizuj — otrzymasz szczegółową ocenę wiralności przed inwestycją w generację.
                </p>
              </div>
            )}

            {ladowanie && (
              <div className="glass p-10 h-full flex flex-col items-center justify-center text-center">
                <div className="w-14 h-14 rounded-full border-2 border-violet-500 border-t-transparent animate-spin mb-4" />
                <p className="text-sm" style={{ color: "var(--c-muted)" }}>
                  Analizuję algorytmy platform…
                </p>
              </div>
            )}

            {wynik && !ladowanie && (
              <div className="space-y-4 animate-fade-in">
                {/* Główny score */}
                <div className="glass p-6 text-center">
                  <div
                    className="text-7xl font-black stat-number mb-2"
                    style={{ color: getNVSColor(wynik.wynik_nwv) }}
                  >
                    {wynik.wynik_nwv}
                  </div>
                  <div className="text-sm mb-2" style={{ color: "var(--c-muted)" }}>NEXUS Viral Score</div>
                  <div className="font-bold">{wynik.odznaka}</div>
                  {wynik.uzasadnienie && (
                    <p className="text-xs mt-2" style={{ color: "var(--c-muted)" }}>
                      {wynik.uzasadnienie}
                    </p>
                  )}
                </div>

                {/* Komponenty */}
                <div className="glass p-5 space-y-4">
                  <h4 className="font-bold text-sm">Składniki NVS</h4>
                  <ScoreMeter label="💥 Siła haka" value={wynik.wynik_haka} color="linear-gradient(90deg, #f59e0b, #ef4444)" />
                  <ScoreMeter label="⏱ Retencja widza" value={wynik.wynik_zatrzymania} color="linear-gradient(90deg, #7c3aed, #06b6d4)" />
                  <ScoreMeter label="🔁 Udostępnialność" value={wynik.wynik_udostepnialnosci} color="linear-gradient(90deg, #10b981, #059669)" />
                </div>

                {/* Per platforma */}
                <div className="glass p-5 space-y-4">
                  <h4 className="font-bold text-sm">Per platforma</h4>
                  {Object.entries(wynik.wynik_platformy).map(([p, v]) => (
                    <ScoreMeter
                      key={p}
                      label={p === "tiktok" ? "🎵 TikTok" : p === "youtube" ? "▶️ YouTube" : "📸 Instagram"}
                      value={v}
                      color="linear-gradient(90deg, #ec4899, #8b5cf6)"
                    />
                  ))}
                </div>

                {/* Wskazówki */}
                {wynik.wskazowki_optymalizacji.length > 0 && (
                  <div className="glass p-5">
                    <h4 className="font-bold text-sm mb-3">💡 Jak zwiększyć NVS</h4>
                    <ul className="space-y-2">
                      {wynik.wskazowki_optymalizacji.map((w, i) => (
                        <li key={i} className="flex gap-2 text-sm">
                          <span className="text-violet-400 flex-shrink-0 font-bold">{i + 1}.</span>
                          <span style={{ color: "var(--c-muted)" }}>{w}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <Link
                  href={`/studio?gatunek=${encodeURIComponent(brief.slice(0, 40))}`}
                  className="btn-primary w-full justify-center"
                  style={{ padding: "14px" }}
                >
                  🎬 Stwórz wideo z tym briefem
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
