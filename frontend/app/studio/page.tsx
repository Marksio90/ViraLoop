"use client";

import { useState, useCallback } from "react";
import Link from "next/link";

// Typy
interface WynikGeneracji {
  sesja_id: string;
  status: string;
  wideo?: {
    sciezka_pliku: string;
    rozdzielczosc: string;
    czas_trwania: number;
    rozmiar_mb: number;
  };
  plan_tresci?: {
    tytul: string;
    typ_haka: string;
    hak_wizualny: string;
    hak_tekstowy: string;
    hak_werbalny: string;
    platforma_docelowa: string[];
    dlugosc_sekund: number;
  };
  scenariusz?: {
    tytul: string;
    streszczenie: string;
    calkowity_czas: number;
    hook_otwierający: string;
    cta: string;
    sceny: Array<{
      numer: number;
      tekst_narracji: string;
      tekst_na_ekranie: string;
      emocja: string;
    }>;
  };
  ocena_wiralnosci?: {
    wynik_nwv: number;
    odznaka: string;
    wynik_haka: number;
    wynik_zatrzymania: number;
    wynik_udostepnialnosci: number;
    wynik_platformy: Record<string, number>;
    wskazowki_optymalizacji: string[];
    uzasadnienie: string;
  };
  ocena_jakosci?: {
    wynik_ogolny: number;
    wynik_haka: number;
    wynik_scenariusza: number;
    wynik_wizualny: number;
    wynik_audio: number;
    mocne_punkty: string[];
    slabe_punkty: string[];
  };
  koszt_usd: number;
  czas_generacji_s: number;
  bledy: string[];
}

interface FormDanych {
  brief: string;
  platforma: string[];
  dlugosc_sekund: number;
  glos: string;
  styl_wizualny: string;
  marka_nazwa: string;
  marka_ton: string;
}

type StatusGeneracji = "idle" | "generowanie" | "sukces" | "blad";

// Etapy pipeline (wizualizacja)
const ETAPY_PIPELINE = [
  { id: "strateg", ikona: "🧠", nazwa: "Strateg Treści", opis: "Analizuje brief..." },
  { id: "pisarz", ikona: "✍️", nazwa: "Pisarz Scenariuszy", opis: "Tworzy scenariusz..." },
  { id: "audio", ikona: "🎙️", nazwa: "Reżyser Głosu", opis: "Generuje narrację..." },
  { id: "wizualia", ikona: "🎨", nazwa: "Producent Wizualny", opis: "Generuje obrazy DALL-E 3..." },
  { id: "recenzja", ikona: "🔍", nazwa: "Recenzent Jakości", opis: "Ocenia i zatwierdza..." },
  { id: "compositor", ikona: "🎬", nazwa: "Compositor", opis: "Scala wideo MP4..." },
];

function PasekPostepu({ etap }: { etap: number }) {
  return (
    <div className="w-full">
      <div className="flex items-start justify-between mb-4 overflow-x-auto gap-2 pb-2">
        {ETAPY_PIPELINE.map((e, i) => (
          <div
            key={e.id}
            className={`flex flex-col items-center gap-1 flex-shrink-0 transition-all duration-500 ${
              i < etap
                ? "opacity-100"
                : i === etap
                ? "opacity-100 agent-aktywny"
                : "opacity-30"
            }`}
          >
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center text-lg border-2 transition-all ${
                i < etap
                  ? "bg-green-500/20 border-green-500 text-green-400"
                  : i === etap
                  ? "bg-indigo-500/20 border-indigo-500 text-indigo-400"
                  : "bg-white/5 border-white/20"
              }`}
            >
              {i < etap ? "✓" : e.ikona}
            </div>
            <div className="text-xs text-center text-white/60 max-w-[64px] leading-tight">
              {e.nazwa}
            </div>
          </div>
        ))}
      </div>
      {/* Pasek postępu */}
      <div className="w-full bg-white/10 rounded-full h-1.5">
        <div
          className="bg-gradient-to-r from-indigo-500 to-purple-500 h-1.5 rounded-full transition-all duration-1000"
          style={{ width: `${(etap / ETAPY_PIPELINE.length) * 100}%` }}
        />
      </div>
      {etap < ETAPY_PIPELINE.length && (
        <p className="text-center text-white/50 text-sm mt-2">
          {ETAPY_PIPELINE[etap].opis}
        </p>
      )}
    </div>
  );
}

function KartaWynikow({ wynik }: { wynik: WynikGeneracji }) {
  const nwv = wynik.ocena_wiralnosci?.wynik_nwv ?? 0;

  const klasaNVS =
    nwv >= 85 ? "score-high" : nwv >= 60 ? "score-good" : "score-warn";

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Nagłówek */}
      <div className="nexus-card">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-xl font-bold">
              {wynik.scenariusz?.tytul ?? wynik.plan_tresci?.tytul ?? "Wideo NEXUS"}
            </h3>
            <p className="text-white/50 text-sm mt-1">
              Sesja: {wynik.sesja_id}
            </p>
          </div>
          <div className="text-right">
            <div className={klasaNVS}>
              {wynik.ocena_wiralnosci?.odznaka ?? "N/A"}
            </div>
            <div className="text-white/50 text-xs mt-1">
              NVS: {nwv}/100
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-black text-green-400">
              ${wynik.koszt_usd.toFixed(3)}
            </div>
            <div className="text-white/50 text-xs">Koszt OpenAI</div>
          </div>
          <div>
            <div className="text-2xl font-black text-blue-400">
              {wynik.czas_generacji_s.toFixed(0)}s
            </div>
            <div className="text-white/50 text-xs">Czas generacji</div>
          </div>
          <div>
            <div className="text-2xl font-black text-purple-400">
              {wynik.wideo?.czas_trwania?.toFixed(0) ?? "—"}s
            </div>
            <div className="text-white/50 text-xs">Długość wideo</div>
          </div>
        </div>
      </div>

      {/* Pobierz wideo */}
      {wynik.wideo && wynik.status === "sukces" && (
        <div className="nexus-card bg-green-500/5 border-green-500/30">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-bold text-green-400 mb-1">🎬 Wideo gotowe!</h4>
              <p className="text-white/50 text-sm">
                {wynik.wideo.rozdzielczosc} • {wynik.wideo.rozmiar_mb} MB
              </p>
            </div>
            <a
              href={`/api/v1/wideo/${wynik.sesja_id}/pobierz`}
              className="nexus-button text-sm"
              download
            >
              Pobierz MP4
            </a>
          </div>
        </div>
      )}

      {/* Wyniki per agent */}
      {wynik.ocena_jakosci && (
        <div className="nexus-card">
          <h4 className="font-bold mb-4">Wyniki per Agent</h4>
          <div className="space-y-2">
            {[
              { etykieta: "Hak", wynik: wynik.ocena_jakosci.wynik_haka },
              { etykieta: "Scenariusz", wynik: wynik.ocena_jakosci.wynik_scenariusza },
              { etykieta: "Wizualia", wynik: wynik.ocena_jakosci.wynik_wizualny },
              { etykieta: "Audio", wynik: wynik.ocena_jakosci.wynik_audio },
              { etykieta: "Ogólny", wynik: wynik.ocena_jakosci.wynik_ogolny },
            ].map((item) => (
              <div key={item.etykieta} className="flex items-center gap-3">
                <div className="w-20 text-white/60 text-sm">{item.etykieta}</div>
                <div className="flex-1 bg-white/10 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-1000 ${
                      item.wynik >= 80
                        ? "bg-green-500"
                        : item.wynik >= 60
                        ? "bg-indigo-500"
                        : "bg-yellow-500"
                    }`}
                    style={{ width: `${item.wynik}%` }}
                  />
                </div>
                <div className="w-8 text-right text-sm font-bold">
                  {item.wynik}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Wiralność per platforma */}
      {wynik.ocena_wiralnosci?.wynik_platformy && (
        <div className="nexus-card">
          <h4 className="font-bold mb-4">NVS per Platforma</h4>
          <div className="space-y-2">
            {Object.entries(wynik.ocena_wiralnosci.wynik_platformy).map(
              ([platforma, wynik_p]) => (
                <div key={platforma} className="flex items-center gap-3">
                  <div className="w-24 text-white/60 text-sm capitalize">
                    {platforma}
                  </div>
                  <div className="flex-1 bg-white/10 rounded-full h-2">
                    <div
                      className="h-2 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-1000"
                      style={{ width: `${wynik_p}%` }}
                    />
                  </div>
                  <div className="w-8 text-right text-sm font-bold">{wynik_p}</div>
                </div>
              )
            )}
          </div>
        </div>
      )}

      {/* Scenariusz */}
      {wynik.scenariusz && (
        <div className="nexus-card">
          <h4 className="font-bold mb-3">Scenariusz</h4>
          <div className="space-y-2">
            <div className="p-3 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
              <div className="text-xs text-indigo-400 font-bold mb-1">HOOK (0-3s)</div>
              <div className="text-sm">{wynik.scenariusz.hook_otwierający}</div>
            </div>
            {wynik.scenariusz.sceny.slice(0, 3).map((scena) => (
              <div key={scena.numer} className="p-3 bg-white/5 rounded-xl">
                <div className="text-xs text-white/40 mb-1">
                  Scena {scena.numer} • {scena.emocja}
                </div>
                <div className="text-sm text-white/80">{scena.tekst_narracji}</div>
                {scena.tekst_na_ekranie && (
                  <div className="text-xs text-yellow-400 mt-1">
                    [{scena.tekst_na_ekranie}]
                  </div>
                )}
              </div>
            ))}
            <div className="p-3 bg-green-500/10 rounded-xl border border-green-500/20">
              <div className="text-xs text-green-400 font-bold mb-1">CTA</div>
              <div className="text-sm">{wynik.scenariusz.cta}</div>
            </div>
          </div>
        </div>
      )}

      {/* Wskazówki optymalizacji */}
      {wynik.ocena_wiralnosci && wynik.ocena_wiralnosci.wskazowki_optymalizacji.length > 0 && (
        <div className="nexus-card">
          <h4 className="font-bold mb-3">💡 Wskazówki Optymalizacji</h4>
          <ul className="space-y-2">
            {wynik.ocena_wiralnosci.wskazowki_optymalizacji.map((w, i) => (
              <li key={i} className="flex gap-2 text-sm text-white/70">
                <span className="text-indigo-400 flex-shrink-0">→</span>
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Błędy */}
      {wynik.bledy.length > 0 && (
        <div className="nexus-card border-red-500/30 bg-red-500/5">
          <h4 className="font-bold text-red-400 mb-2">Ostrzeżenia</h4>
          {wynik.bledy.map((b, i) => (
            <p key={i} className="text-red-300 text-sm">{b}</p>
          ))}
        </div>
      )}
    </div>
  );
}

export default function StudioPage() {
  const [status, setStatus] = useState<StatusGeneracji>("idle");
  const [etapPipeline, setEtapPipeline] = useState(0);
  const [wynik, setWynik] = useState<WynikGeneracji | null>(null);
  const [formularz, setFormularz] = useState<FormDanych>({
    brief: "",
    platforma: ["tiktok", "youtube"],
    dlugosc_sekund: 60,
    glos: "nova",
    styl_wizualny: "nowoczesny",
    marka_nazwa: "",
    marka_ton: "energiczny",
  });

  const symulujPostepPipeline = useCallback(() => {
    let etap = 0;
    const interwał = setInterval(() => {
      etap++;
      setEtapPipeline(etap);
      if (etap >= ETAPY_PIPELINE.length) {
        clearInterval(interwał);
      }
    }, 12000); // ~12s per etap = ~72s całość
    return interwał;
  }, []);

  const generujWideo = useCallback(async () => {
    if (!formularz.brief.trim() || formularz.brief.length < 10) {
      alert("Brief musi mieć minimum 10 znaków");
      return;
    }

    setStatus("generowanie");
    setEtapPipeline(0);
    setWynik(null);

    const interwałPostepu = symulujPostepPipeline();

    try {
      const odpowiedz = await fetch("/api/v1/wideo/generuj", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brief: formularz.brief,
          platforma: formularz.platforma,
          dlugosc_sekund: formularz.dlugosc_sekund,
          glos: formularz.glos,
          styl_wizualny: formularz.styl_wizualny,
          marka: {
            nazwa: formularz.marka_nazwa || "NEXUS",
            ton: formularz.marka_ton,
          },
        }),
      });

      clearInterval(interwałPostepu);
      setEtapPipeline(ETAPY_PIPELINE.length);

      if (!odpowiedz.ok) {
        const blad = await odpowiedz.json();
        throw new Error(blad.detail ?? "Błąd serwera");
      }

      const dane: WynikGeneracji = await odpowiedz.json();
      setWynik(dane);
      setStatus("sukces");
    } catch (e) {
      clearInterval(interwałPostepu);
      setStatus("blad");
      console.error(e);
      setWynik({
        sesja_id: "error",
        status: "blad",
        koszt_usd: 0,
        czas_generacji_s: 0,
        bledy: [e instanceof Error ? e.message : "Nieznany błąd"],
      });
    }
  }, [formularz, symulujPostepPipeline]);

  const togglePlatforma = (platforma: string) => {
    setFormularz((prev) => ({
      ...prev,
      platforma: prev.platforma.includes(platforma)
        ? prev.platforma.filter((p) => p !== platforma)
        : [...prev.platforma, platforma],
    }));
  };

  return (
    <div className="min-h-screen bg-[#0f0f1a] text-white">
      {/* Tło */}
      <div className="fixed inset-0 bg-gradient-to-br from-indigo-950/20 via-[#0f0f1a] to-purple-950/10 pointer-events-none" />

      {/* Nawigacja */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-5 border-b border-white/10">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-xl font-black">
            N
          </div>
          <span className="text-xl font-black gradient-text">NEXUS Studio</span>
        </Link>

        <Link href="/analityka" className="text-white/60 hover:text-white text-sm transition-colors">
          Analityka →
        </Link>
      </nav>

      <div className="relative z-10 max-w-6xl mx-auto px-8 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Panel lewy: Formularz */}
          <div className="space-y-6">
            <div>
              <h1 className="text-3xl font-black mb-2">
                Studio <span className="gradient-text">Generacji</span>
              </h1>
              <p className="text-white/50">
                Opisz wideo — 5 agentów AI wykona resztę
              </p>
            </div>

            {/* Brief */}
            <div className="nexus-card">
              <label className="text-sm font-bold text-white/80 block mb-2">
                Brief wideo *
              </label>
              <textarea
                className="nexus-input resize-none h-28"
                placeholder="Np. Pokaż mi, jak 10 minut medytacji rano zmienia produktywność całego dnia. Konkretne korzyści, naukowe dowody, praktyczne wskazówki."
                value={formularz.brief}
                onChange={(e) =>
                  setFormularz((prev) => ({ ...prev, brief: e.target.value }))
                }
                disabled={status === "generowanie"}
              />
              <div className="text-right text-white/30 text-xs mt-1">
                {formularz.brief.length}/2000
              </div>
            </div>

            {/* Platformy */}
            <div className="nexus-card">
              <label className="text-sm font-bold text-white/80 block mb-3">
                Platformy docelowe
              </label>
              <div className="flex gap-3">
                {["tiktok", "youtube", "instagram"].map((p) => (
                  <button
                    key={p}
                    onClick={() => togglePlatforma(p)}
                    disabled={status === "generowanie"}
                    className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${
                      formularz.platforma.includes(p)
                        ? "bg-indigo-500/20 border border-indigo-500 text-indigo-300"
                        : "bg-white/5 border border-white/20 text-white/50 hover:border-white/40"
                    }`}
                  >
                    {p === "tiktok" ? "🎵 TikTok" : p === "youtube" ? "▶️ YouTube" : "📸 Instagram"}
                  </button>
                ))}
              </div>
            </div>

            {/* Parametry */}
            <div className="nexus-card">
              <label className="text-sm font-bold text-white/80 block mb-3">
                Parametry
              </label>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-white/50 block mb-1">
                    Długość (sekundy)
                  </label>
                  <select
                    className="nexus-input text-sm"
                    value={formularz.dlugosc_sekund}
                    onChange={(e) =>
                      setFormularz((prev) => ({
                        ...prev,
                        dlugosc_sekund: Number(e.target.value),
                      }))
                    }
                    disabled={status === "generowanie"}
                  >
                    <option value={30}>30s</option>
                    <option value={60}>60s</option>
                    <option value={90}>90s</option>
                    <option value={120}>120s</option>
                    <option value={180}>180s</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-white/50 block mb-1">
                    Głos lektora
                  </label>
                  <select
                    className="nexus-input text-sm"
                    value={formularz.glos}
                    onChange={(e) =>
                      setFormularz((prev) => ({ ...prev, glos: e.target.value }))
                    }
                    disabled={status === "generowanie"}
                  >
                    <option value="nova">nova (ciepły)</option>
                    <option value="alloy">alloy (neutralny)</option>
                    <option value="echo">echo (głęboki)</option>
                    <option value="fable">fable (dramatyczny)</option>
                    <option value="onyx">onyx (autorytatywny)</option>
                    <option value="shimmer">shimmer (delikatny)</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-white/50 block mb-1">
                    Styl wizualny
                  </label>
                  <select
                    className="nexus-input text-sm"
                    value={formularz.styl_wizualny}
                    onChange={(e) =>
                      setFormularz((prev) => ({
                        ...prev,
                        styl_wizualny: e.target.value,
                      }))
                    }
                    disabled={status === "generowanie"}
                  >
                    <option value="nowoczesny">Nowoczesny</option>
                    <option value="kinowy">Kinowy</option>
                    <option value="estetyczny">Estetyczny</option>
                    <option value="dynamiczny">Dynamiczny</option>
                    <option value="profesjonalny">Profesjonalny</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-white/50 block mb-1">
                    Nazwa marki
                  </label>
                  <input
                    type="text"
                    className="nexus-input text-sm"
                    placeholder="Twoja Marka"
                    value={formularz.marka_nazwa}
                    onChange={(e) =>
                      setFormularz((prev) => ({
                        ...prev,
                        marka_nazwa: e.target.value,
                      }))
                    }
                    disabled={status === "generowanie"}
                  />
                </div>
              </div>
            </div>

            {/* Przycisk */}
            <button
              onClick={generujWideo}
              disabled={
                status === "generowanie" ||
                formularz.brief.length < 10 ||
                formularz.platforma.length === 0
              }
              className="w-full nexus-button text-lg py-4"
            >
              {status === "generowanie" ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Pipeline aktywny...
                </span>
              ) : (
                "🚀 Generuj Wideo"
              )}
            </button>

            {/* Szacowany koszt */}
            <div className="text-center text-white/40 text-sm">
              Szacowany koszt: ~${(0.04 * Math.min(5, Math.ceil(formularz.dlugosc_sekund / 15)) + 0.025).toFixed(2)}
            </div>
          </div>

          {/* Panel prawy: Wyniki / Pipeline */}
          <div>
            {status === "idle" && (
              <div className="nexus-card h-full flex flex-col items-center justify-center text-center py-20">
                <div className="text-6xl mb-4">🎬</div>
                <h3 className="text-xl font-bold mb-2">Gotowy na akcję?</h3>
                <p className="text-white/40 max-w-xs">
                  Opisz swoje wideo i uruchom pipeline. 5 agentów AI stworzy
                  kompletne wideo wirusowe.
                </p>
              </div>
            )}

            {status === "generowanie" && (
              <div className="nexus-card space-y-6">
                <h3 className="text-lg font-bold">Pipeline Multi-Agentowy</h3>
                <PasekPostepu etap={etapPipeline} />
                <div className="text-center text-white/40 text-sm">
                  Każdy etap to wyspecjalizowany agent AI pracujący dla Ciebie...
                </div>
              </div>
            )}

            {(status === "sukces" || status === "blad") && wynik && (
              <KartaWynikow wynik={wynik} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
