"use client";

import { useState, useEffect } from "react";
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
  kluczowe_slabe?: string;
}

const PRZYKŁADOWE_BRIEFY = [
  "Jak zimne prysznice zwiększają testosteron i energię",
  "3 błędy, które zabijają Twoje wideo na TikToku",
  "Sekret produktywności, który stosują milionerzy",
  "Dlaczego 90% twórców nigdy nie viralizuje",
];

function GrafSlupkowy({ etykieta, wartosc, kolor = "indigo" }: {
  etykieta: string;
  wartosc: number;
  kolor?: string;
}) {
  const kolorKlasa = {
    indigo: "from-indigo-500 to-purple-500",
    green: "from-green-500 to-emerald-500",
    orange: "from-orange-500 to-red-500",
    pink: "from-pink-500 to-rose-500",
  }[kolor] ?? "from-indigo-500 to-purple-500";

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-white/60">{etykieta}</span>
        <span className="font-bold">{wartosc}/100</span>
      </div>
      <div className="w-full bg-white/10 rounded-full h-2.5">
        <div
          className={`h-2.5 rounded-full bg-gradient-to-r ${kolorKlasa} transition-all duration-1000`}
          style={{ width: `${wartosc}%` }}
        />
      </div>
    </div>
  );
}

export default function AnaliitykaPage() {
  const [brief, setBrief] = useState("");
  const [platforma, setPlatforma] = useState(["tiktok", "youtube"]);
  const [dlugosc, setDlugosc] = useState(60);
  const [ladowanie, setLadowanie] = useState(false);
  const [wynik, setWynik] = useState<WynikWiralnosci | null>(null);
  const [historia, setHistoria] = useState<WynikWiralnosci[]>([]);

  const analizuj = async () => {
    if (!brief.trim() || brief.length < 10) return;

    setLadowanie(true);
    setWynik(null);

    try {
      const odpowiedz = await fetch("/api/v1/wideo/wiralnosc", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brief,
          platforma,
          dlugosc_sekund: dlugosc,
        }),
      });

      if (!odpowiedz.ok) throw new Error("Błąd serwera");

      const dane: WynikWiralnosci = await odpowiedz.json();
      setWynik(dane);
      setHistoria((prev) => [dane, ...prev.slice(0, 4)]);
    } catch (e) {
      console.error(e);
      // Mock dla demonstracji
      const mockWynik: WynikWiralnosci = {
        wynik_nwv: Math.floor(65 + Math.random() * 25),
        wynik_haka: Math.floor(60 + Math.random() * 30),
        wynik_zatrzymania: Math.floor(60 + Math.random() * 25),
        wynik_udostepnialnosci: Math.floor(55 + Math.random() * 30),
        wynik_platformy: {
          tiktok: Math.floor(65 + Math.random() * 25),
          youtube: Math.floor(60 + Math.random() * 25),
          instagram: Math.floor(58 + Math.random() * 25),
        },
        odznaka: "✅ Dobry content",
        uzasadnienie: "Demo mode — backend niedostępny",
        wskazowki_optymalizacji: [
          "Dodaj tekst na ekranie w pierwszych 3 sekundach",
          "Skróć CTA do 5-7 słów",
          "Rozważ zakończenie z pętlą",
        ],
      };
      setWynik(mockWynik);
    } finally {
      setLadowanie(false);
    }
  };

  const nwv = wynik?.wynik_nwv ?? 0;
  const klasaNVS =
    nwv >= 85 ? "score-high" : nwv >= 60 ? "score-good" : "score-warn";

  return (
    <div className="min-h-screen bg-[#0f0f1a] text-white">
      <div className="fixed inset-0 bg-gradient-to-br from-purple-950/20 via-[#0f0f1a] to-indigo-950/10 pointer-events-none" />

      {/* Nawigacja */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-5 border-b border-white/10">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-xl font-black">
            N
          </div>
          <span className="text-xl font-black gradient-text">NEXUS Analityka</span>
        </Link>
        <Link href="/studio" className="nexus-button text-sm">
          Studio →
        </Link>
      </nav>

      <div className="relative z-10 max-w-5xl mx-auto px-8 py-10">
        <div className="mb-10">
          <h1 className="text-4xl font-black mb-2">
            Silnik <span className="gradient-text">Wiralności</span>
          </h1>
          <p className="text-white/50">
            Predykcja wiralności przed publikacją. Analizuj brief i optymalizuj
            zanim stworzysz wideo.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Formularz analizy */}
          <div className="space-y-6">
            <div className="nexus-card">
              <label className="text-sm font-bold text-white/80 block mb-2">
                Brief / Temat wideo
              </label>
              <textarea
                className="nexus-input resize-none h-24"
                placeholder="Opisz swoje wideo lub wklej temat..."
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                disabled={ladowanie}
              />

              {/* Przykładowe briefy */}
              <div className="mt-3 flex flex-wrap gap-2">
                {PRZYKŁADOWE_BRIEFY.map((p) => (
                  <button
                    key={p}
                    onClick={() => setBrief(p)}
                    className="text-xs bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg px-3 py-1 text-white/60 hover:text-white/80 transition-all"
                  >
                    {p.substring(0, 30)}...
                  </button>
                ))}
              </div>
            </div>

            {/* Platformy i długość */}
            <div className="nexus-card">
              <div className="flex flex-wrap gap-3 mb-4">
                {["tiktok", "youtube", "instagram"].map((p) => (
                  <button
                    key={p}
                    onClick={() =>
                      setPlatforma((prev) =>
                        prev.includes(p)
                          ? prev.filter((x) => x !== p)
                          : [...prev, p]
                      )
                    }
                    className={`px-3 py-1.5 rounded-lg text-sm font-bold transition-all ${
                      platforma.includes(p)
                        ? "bg-indigo-500/20 border border-indigo-500 text-indigo-300"
                        : "bg-white/5 border border-white/20 text-white/50"
                    }`}
                  >
                    {p === "tiktok" ? "🎵" : p === "youtube" ? "▶️" : "📸"}{" "}
                    {p}
                  </button>
                ))}
              </div>

              <div>
                <label className="text-xs text-white/50 block mb-1">
                  Docelowa długość: {dlugosc}s
                </label>
                <input
                  type="range"
                  min={15}
                  max={180}
                  step={15}
                  value={dlugosc}
                  onChange={(e) => setDlugosc(Number(e.target.value))}
                  className="w-full accent-indigo-500"
                />
                <div className="flex justify-between text-xs text-white/30 mt-1">
                  <span>15s</span>
                  <span>60s</span>
                  <span>120s</span>
                  <span>180s</span>
                </div>
              </div>
            </div>

            <button
              onClick={analizuj}
              disabled={ladowanie || brief.length < 10}
              className="w-full nexus-button py-3"
            >
              {ladowanie ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Analizuję...
                </span>
              ) : (
                "🔮 Analizuj Wiralność"
              )}
            </button>

            {/* Historia */}
            {historia.length > 0 && (
              <div className="nexus-card">
                <h4 className="font-bold mb-3 text-sm">Historia analiz</h4>
                <div className="space-y-2">
                  {historia.map((h, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between py-2 border-b border-white/5 last:border-0"
                    >
                      <div
                        className={`text-lg font-black ${
                          h.wynik_nwv >= 85
                            ? "text-orange-400"
                            : h.wynik_nwv >= 60
                            ? "text-green-400"
                            : "text-yellow-400"
                        }`}
                      >
                        NVS {h.wynik_nwv}
                      </div>
                      <div className="text-white/40 text-xs">{h.odznaka}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Wyniki */}
          <div>
            {!wynik && !ladowanie && (
              <div className="nexus-card h-full flex flex-col items-center justify-center text-center py-20">
                <div className="text-6xl mb-4">🔮</div>
                <h3 className="text-xl font-bold mb-2">Predykcja Wiralności</h3>
                <p className="text-white/40 max-w-xs">
                  Wpisz brief i kliknij analizuj — otrzymasz szczegółową
                  predykcję NVS przed stworzeniem wideo.
                </p>
              </div>
            )}

            {ladowanie && (
              <div className="nexus-card h-full flex flex-col items-center justify-center py-20">
                <div className="w-16 h-16 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-4" />
                <p className="text-white/60">Analizuję algorytmy platform...</p>
              </div>
            )}

            {wynik && !ladowanie && (
              <div className="space-y-6 animate-slide-up">
                {/* NVS Score */}
                <div className="nexus-card text-center">
                  <div className="text-7xl font-black gradient-text mb-2">
                    {wynik.wynik_nwv}
                  </div>
                  <div className="text-white/50 mb-3">NEXUS Viral Score</div>
                  <div className={klasaNVS}>{wynik.odznaka}</div>
                  {wynik.uzasadnienie && (
                    <p className="text-white/50 text-sm mt-3">
                      {wynik.uzasadnienie}
                    </p>
                  )}
                </div>

                {/* Komponenty NVS */}
                <div className="nexus-card space-y-4">
                  <h4 className="font-bold">Komponenty NVS</h4>
                  <GrafSlupkowy
                    etykieta="💥 Siła Haka"
                    wartosc={wynik.wynik_haka}
                    kolor="orange"
                  />
                  <GrafSlupkowy
                    etykieta="⏱️ Retencja"
                    wartosc={wynik.wynik_zatrzymania}
                    kolor="indigo"
                  />
                  <GrafSlupkowy
                    etykieta="🔁 Udostępnialność"
                    wartosc={wynik.wynik_udostepnialnosci}
                    kolor="green"
                  />
                </div>

                {/* Per platforma */}
                {wynik.wynik_platformy && (
                  <div className="nexus-card space-y-4">
                    <h4 className="font-bold">Per Platforma</h4>
                    {Object.entries(wynik.wynik_platformy).map(
                      ([platf, wynik_p]) => (
                        <GrafSlupkowy
                          key={platf}
                          etykieta={
                            platf === "tiktok"
                              ? "🎵 TikTok"
                              : platf === "youtube"
                              ? "▶️ YouTube"
                              : "📸 Instagram"
                          }
                          wartosc={wynik_p}
                          kolor="pink"
                        />
                      )
                    )}
                  </div>
                )}

                {/* Wskazówki */}
                {wynik.wskazowki_optymalizacji?.length > 0 && (
                  <div className="nexus-card">
                    <h4 className="font-bold mb-3">💡 Jak zwiększyć NVS</h4>
                    <ul className="space-y-2">
                      {wynik.wskazowki_optymalizacji.map((w, i) => (
                        <li
                          key={i}
                          className="flex gap-2 text-sm text-white/70"
                        >
                          <span className="text-indigo-400 flex-shrink-0">
                            {i + 1}.
                          </span>
                          {w}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* CTA do Studio */}
                <Link href="/studio" className="nexus-button block text-center py-3">
                  Stwórz wideo z tym briefem →
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
