"use client";

import { useState, useRef, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

// ── TYPY ───────────────────────────────────────────────────────────

type Tryb = "seria" | "pojedynczy";
type Platforma = "tiktok" | "youtube" | "instagram";
type Glos = "nova" | "alloy" | "echo" | "fable" | "onyx" | "shimmer";
type StatusGeneracji = "idle" | "generating" | "done" | "error";

interface KrokGeneracji {
  id: string;
  nazwa: string;
  opis: string;
  status: "idle" | "running" | "done" | "error";
  czas?: number;
}

interface WynikWideo {
  sesja_id: string;
  tytul: string;
  sciezka_wideo: string;
  miniatura: string;
  nwv: number;
  koszt_usd: number;
  czas_s: number;
  odcinek?: number;
}

// ── STAŁE ──────────────────────────────────────────────────────────

const GATUNKI_QUICK = [
  "⚔️ Tajemnice Historii",
  "👑 Wielkie Imperia",
  "🔬 Nauka i Odkrycia",
  "🕵️ Zbrodnie i Sekrety",
  "💰 Fortuna i Bankructwo",
  "🚀 Wyścig Technologii",
  "🧬 Ewolucja i Natura",
  "🌍 Geopolityka",
];

const STYLE_WIZUALNE = [
  { id: "kinowy", label: "Kinowy", opis: "Dramatyczne, filmowe" },
  { id: "dokumentalny", label: "Dokumentalny", opis: "Realistyczny, fakty" },
  { id: "epicka", label: "Epicka ilustracja", opis: "Artystyczna, malarska" },
  { id: "nowoczesny", label: "Nowoczesny", opis: "Minimalistyczny, czysty" },
];

const GLOSY: { id: Glos; label: string; opis: string; plec: string }[] = [
  { id: "nova", label: "Nova", opis: "Ciepły, kobiecy", plec: "K" },
  { id: "alloy", label: "Alloy", opis: "Neutralny, profesjonalny", plec: "M" },
  { id: "echo", label: "Echo", opis: "Głęboki, dramatyczny", plec: "M" },
  { id: "fable", label: "Fable", opis: "Opowieść, emocjonalny", plec: "M" },
  { id: "onyx", label: "Onyx", opis: "Mocny, autorytarny", plec: "M" },
  { id: "shimmer", label: "Shimmer", opis: "Dynamiczny, energiczny", plec: "K" },
];

const KROKI_PIPELINE: KrokGeneracji[] = [
  { id: "strateg", nazwa: "Strateg Narracji", opis: "Projektuje łuk fabularny i hak odcinka", status: "idle" },
  { id: "pisarz", nazwa: "Pisarz Scenariuszy", opis: "Pisze scenariusz scena po scenie", status: "idle" },
  { id: "glos", nazwa: "Reżyser Głosu", opis: "Syntezuje narrację z segmentami TTS", status: "idle" },
  { id: "wizualia", nazwa: "Producent Wizualny", opis: "Generuje klatki DALL-E 3 w 9:16", status: "idle" },
  { id: "recenzent", nazwa: "Recenzent Jakości", opis: "Ocenia i zatwierdza (próg: 60 NVS)", status: "idle" },
  { id: "compositor", nazwa: "Montażysta AI", opis: "Scala wideo z animowanymi napisami", status: "idle" },
];

function getScoreColor(score: number) {
  if (score >= 85) return "#10b981";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

// ── GŁÓWNY KOMPONENT ────────────────────────────────────────────────

function StudioInner() {
  const searchParams = useSearchParams();

  // Formularz
  const [tryb, setTryb] = useState<Tryb>("seria");
  const [brief, setBrief] = useState(searchParams.get("gatunek") ? `${searchParams.get("gatunek")} — ` : "");
  const [tytulSerii, setTytulSerii] = useState("");
  const [liczbaOdcinkow, setLiczbaOdcinkow] = useState(5);
  const [platformy, setPlatformy] = useState<Platforma[]>(["tiktok", "youtube"]);
  const [styl, setStyl] = useState("kinowy");
  const [glos, setGlos] = useState<Glos>("nova");
  const [dlugosc, setDlugosc] = useState(60);

  // Generacja
  const [status, setStatus] = useState<StatusGeneracji>("idle");
  const [kroki, setKroki] = useState<KrokGeneracji[]>(KROKI_PIPELINE.map(k => ({ ...k })));
  const [wyniki, setWyniki] = useState<WynikWideo[]>([]);
  const [aktualnyKrok, setAktualnyKrok] = useState(-1);
  const [blad, setBlad] = useState("");
  const [wsUrl, setWsUrl] = useState("");

  const wsRef = useRef<WebSocket | null>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);

  // Rozszerzanie textarea
  useEffect(() => {
    if (textarea.current) {
      textarea.current.style.height = "auto";
      textarea.current.style.height = Math.min(textarea.current.scrollHeight, 200) + "px";
    }
  }, [brief]);

  // Wybór platformy
  const togglePlatforma = (p: Platforma) => {
    setPlatformy(prev =>
      prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]
    );
  };

  // Reset pipeline
  const resetKroki = () => {
    setKroki(KROKI_PIPELINE.map(k => ({ ...k, status: "idle" })));
    setAktualnyKrok(-1);
  };

  // Symulacja kroków (podczas oczekiwania na backend)
  const symulujKroki = async () => {
    const czasy = [3, 4, 6, 12, 5, 8];
    for (let i = 0; i < kroki.length; i++) {
      setAktualnyKrok(i);
      setKroki(prev => prev.map((k, idx) => ({
        ...k,
        status: idx === i ? "running" : idx < i ? "done" : "idle"
      })));
      await new Promise(r => setTimeout(r, czasy[i] * 1000));
    }
    setKroki(prev => prev.map(k => ({ ...k, status: "done" })));
    setAktualnyKrok(-1);
  };

  // Generacja
  const generuj = async () => {
    if (!brief.trim()) return;
    if (platformy.length === 0) return;

    setStatus("generating");
    setBlad("");
    setWyniki([]);
    resetKroki();

    // Uruchom symulację kroków w tle
    symulujKroki();

    try {
      const endpoint = tryb === "seria" ? "/api/v1/serie/generuj" : "/api/v1/wideo/generuj";

      const body = tryb === "seria"
        ? {
            temat: brief,
            tytul_serii: tytulSerii || brief.slice(0, 60),
            liczba_odcinkow: liczbaOdcinkow,
            platforma: platformy,
            styl_wizualny: styl,
            glos,
            dlugosc_odcinka_sekund: dlugosc,
          }
        : {
            brief,
            platforma: platformy,
            styl_wizualny: styl,
            glos,
            dlugosc_sekund: dlugosc,
          };

      const res = await fetch(`http://localhost:8000${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Mapuj wyniki
      if (tryb === "seria" && data.odcinki) {
        setWyniki(data.odcinki.map((od: Record<string, unknown>, i: number) => ({
          sesja_id: od.sesja_id as string || `ep_${i}`,
          tytul: od.tytul as string || `Odcinek ${i + 1}`,
          sciezka_wideo: (od.wideo as Record<string, string>)?.sciezka_pliku || "",
          miniatura: (od.wideo as Record<string, string>)?.miniatura_sciezka || "",
          nwv: (od.ocena_wiralnosci as Record<string, unknown>)?.wynik_nwv as number || 0,
          koszt_usd: od.koszt_usd as number || 0,
          czas_s: od.czas_generacji_s as number || 0,
          odcinek: i + 1,
        })));
      } else {
        setWyniki([{
          sesja_id: data.sesja_id || "wynik",
          tytul: data.plan_tresci?.tytul || brief.slice(0, 60),
          sciezka_wideo: data.wideo?.sciezka_pliku || "",
          miniatura: data.wideo?.miniatura_sciezka || "",
          nwv: data.ocena_wiralnosci?.wynik_nwv || 0,
          koszt_usd: data.koszt_usd || 0,
          czas_s: data.czas_generacji_s || 0,
        }]);
      }

      setStatus("done");
      setKroki(prev => prev.map(k => ({ ...k, status: "done" })));

    } catch (e) {
      setBlad(e instanceof Error ? e.message : "Błąd połączenia z backendem");
      setStatus("error");
      setKroki(prev => prev.map((k, i) => ({
        ...k,
        status: i <= aktualnyKrok ? "done" : i === aktualnyKrok + 1 ? "error" : "idle"
      })));
    }
  };

  const isGenerating = status === "generating";

  return (
    <div className="min-h-screen relative" style={{ background: "var(--c-bg)" }}>
      {/* Orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 right-0 w-[400px] h-[400px] rounded-full opacity-10"
          style={{ background: "radial-gradient(circle, #7c3aed 0%, transparent 70%)" }} />
        <div className="absolute bottom-0 left-0 w-[300px] h-[300px] rounded-full opacity-10"
          style={{ background: "radial-gradient(circle, #06b6d4 0%, transparent 70%)" }} />
      </div>

      {/* NAV */}
      <nav className="relative z-20 flex items-center justify-between px-6 py-4 border-b"
        style={{ borderColor: "var(--c-border)", background: "rgba(5,5,16,0.9)", backdropFilter: "blur(20px)" }}>
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-black text-white"
              style={{ background: "linear-gradient(135deg, #7c3aed, #06b6d4)" }}>
              VL
            </div>
            <span className="font-bold">ViraLoop</span>
          </Link>
          <span style={{ color: "var(--c-muted)" }}>/</span>
          <span className="font-semibold text-sm">Studio</span>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/serie" className="btn-ghost text-sm">Moje Serie</Link>
          <Link href="/analityka" className="btn-ghost text-sm">Analityka</Link>
        </div>
      </nav>

      {/* MAIN LAYOUT */}
      <div className="relative z-10 max-w-7xl mx-auto px-4 md:px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">

          {/* ── LEWA KOLUMNA: FORMULARZ ─────────────────────────── */}
          <div className="space-y-4">
            {/* Header */}
            <div>
              <h1 className="text-2xl md:text-3xl font-black mb-1">
                Kreator <span className="gradient-text">AI Shorts</span>
              </h1>
              <p className="text-sm" style={{ color: "var(--c-muted)" }}>
                Wpisz temat — AI wygeneruje serię powiązanych odcinków gotowych do publikacji
              </p>
            </div>

            {/* TRYB: seria vs pojedynczy */}
            <div className="glass p-1 inline-flex rounded-xl">
              {(["seria", "pojedynczy"] as Tryb[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTryb(t)}
                  className="px-5 py-2 rounded-lg text-sm font-semibold transition-all"
                  style={{
                    background: tryb === t ? "linear-gradient(135deg, #7c3aed, #4f46e5)" : "transparent",
                    color: tryb === t ? "#fff" : "var(--c-muted)",
                  }}
                >
                  {t === "seria" ? "🎬 Seria odcinków" : "▶️ Pojedynczy film"}
                </button>
              ))}
            </div>

            {/* QUICK TAGS */}
            <div className="scroll-row">
              {GATUNKI_QUICK.map((g) => (
                <button
                  key={g}
                  className={`tag flex-shrink-0 ${brief.includes(g.split(" ").slice(1).join(" ")) ? "selected" : ""}`}
                  onClick={() => setBrief(g.split(" ").slice(1).join(" ") + " — ")}
                >
                  {g}
                </button>
              ))}
            </div>

            {/* BRIEF / TEMAT */}
            <div className="glass p-5 space-y-4">
              {tryb === "seria" && (
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider mb-2"
                    style={{ color: "var(--c-muted)" }}>
                    Tytuł serii (opcjonalny)
                  </label>
                  <input
                    className="input-premium"
                    placeholder="np. Sekrety Watykanu — nieznane archiwa..."
                    value={tytulSerii}
                    onChange={e => setTytulSerii(e.target.value)}
                    disabled={isGenerating}
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider mb-2"
                  style={{ color: "var(--c-muted)" }}>
                  {tryb === "seria" ? "Temat i koncepcja serii" : "Co ma pokazać film?"}
                </label>
                <textarea
                  ref={textarea}
                  className="input-premium"
                  placeholder={
                    tryb === "seria"
                      ? "np. Tajemnicze zaginięcia z historii, których nauka wciąż nie wyjaśniła — od Atlantydy po zaginiony oddział Armii..."
                      : "np. 3 fakty o Imperium Rzymskim, które zmienią Twoje postrzeganie historii"
                  }
                  value={brief}
                  onChange={e => setBrief(e.target.value)}
                  rows={3}
                  disabled={isGenerating}
                  style={{ minHeight: 80, maxHeight: 200 }}
                />
                <div className="flex justify-between mt-1">
                  <span className="text-xs" style={{ color: "var(--c-muted)" }}>
                    {brief.length}/2000 znaków
                  </span>
                  {brief.length < 20 && (
                    <span className="text-xs" style={{ color: "#f59e0b" }}>
                      Dodaj więcej szczegółów dla lepszych wyników
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* USTAWIENIA */}
            <div className="glass p-5 space-y-5">
              <h3 className="text-sm font-bold uppercase tracking-wider" style={{ color: "var(--c-muted)" }}>
                Parametry produkcji
              </h3>

              {/* Liczba odcinków (tylko seria) */}
              {tryb === "seria" && (
                <div>
                  <label className="block text-xs font-semibold mb-3" style={{ color: "var(--c-muted)" }}>
                    Liczba odcinków: <span className="text-white font-bold">{liczbaOdcinkow}</span>
                    <span className="ml-2 text-xs badge badge-cyan">{liczbaOdcinkow * 0.15 < 1 ? `~$${(liczbaOdcinkow * 0.15).toFixed(2)}` : `~$${(liczbaOdcinkow * 0.15).toFixed(2)}`}</span>
                  </label>
                  <input
                    type="range" min={2} max={10} value={liczbaOdcinkow}
                    onChange={e => setLiczbaOdcinkow(+e.target.value)}
                    className="w-full accent-violet-500"
                    disabled={isGenerating}
                  />
                  <div className="flex justify-between text-xs mt-1" style={{ color: "var(--c-muted)" }}>
                    <span>2</span><span>Mini-seria (5)</span><span>10</span>
                  </div>
                </div>
              )}

              {/* Platformy */}
              <div>
                <label className="block text-xs font-semibold mb-3" style={{ color: "var(--c-muted)" }}>
                  Platformy docelowe
                </label>
                <div className="flex flex-wrap gap-2">
                  {(["tiktok", "youtube", "instagram"] as Platforma[]).map(p => (
                    <button
                      key={p}
                      onClick={() => togglePlatforma(p)}
                      disabled={isGenerating}
                      className={`platform-pill ${platformy.includes(p) ? `active-${p}` : "inactive"}`}
                    >
                      {p === "tiktok" && "🎵 TikTok"}
                      {p === "youtube" && "▶️ YouTube Shorts"}
                      {p === "instagram" && "📸 Instagram Reels"}
                    </button>
                  ))}
                </div>
              </div>

              {/* Długość */}
              <div>
                <label className="block text-xs font-semibold mb-3" style={{ color: "var(--c-muted)" }}>
                  Długość odcinka: <span className="text-white font-bold">{dlugosc}s</span>
                </label>
                <input
                  type="range" min={15} max={180} step={15} value={dlugosc}
                  onChange={e => setDlugosc(+e.target.value)}
                  className="w-full accent-violet-500"
                  disabled={isGenerating}
                />
                <div className="flex justify-between text-xs mt-1" style={{ color: "var(--c-muted)" }}>
                  <span>15s</span><span>60s (optimal)</span><span>3min</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* Styl wizualny */}
                <div>
                  <label className="block text-xs font-semibold mb-2" style={{ color: "var(--c-muted)" }}>
                    Styl wizualny
                  </label>
                  <div className="space-y-1">
                    {STYLE_WIZUALNE.map(s => (
                      <button
                        key={s.id}
                        onClick={() => setStyl(s.id)}
                        disabled={isGenerating}
                        className="w-full text-left px-3 py-2 rounded-lg text-xs transition-all"
                        style={{
                          background: styl === s.id ? "rgba(124,58,237,0.15)" : "rgba(255,255,255,0.02)",
                          border: `1px solid ${styl === s.id ? "rgba(124,58,237,0.4)" : "rgba(255,255,255,0.06)"}`,
                          color: styl === s.id ? "#a78bfa" : "var(--c-muted)",
                        }}
                      >
                        <span className="font-semibold">{s.label}</span>
                        <span className="block opacity-70">{s.opis}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Głos */}
                <div>
                  <label className="block text-xs font-semibold mb-2" style={{ color: "var(--c-muted)" }}>
                    Głos lektora
                  </label>
                  <div className="space-y-1">
                    {GLOSY.map(g => (
                      <button
                        key={g.id}
                        onClick={() => setGlos(g.id)}
                        disabled={isGenerating}
                        className="w-full text-left px-3 py-2 rounded-lg text-xs transition-all"
                        style={{
                          background: glos === g.id ? "rgba(6,182,212,0.12)" : "rgba(255,255,255,0.02)",
                          border: `1px solid ${glos === g.id ? "rgba(6,182,212,0.35)" : "rgba(255,255,255,0.06)"}`,
                          color: glos === g.id ? "#67e8f9" : "var(--c-muted)",
                        }}
                      >
                        <span className="font-semibold">{g.label}</span>
                        <span className="text-xs opacity-60 ml-1">({g.plec})</span>
                        <span className="block opacity-70">{g.opis}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* CTA BUTTON */}
            <button
              onClick={generuj}
              disabled={isGenerating || !brief.trim() || platformy.length === 0}
              className="btn-primary w-full justify-center"
              style={{
                fontSize: 16,
                padding: "16px",
                opacity: isGenerating || !brief.trim() ? 0.6 : 1,
              }}
            >
              {isGenerating ? (
                <>
                  <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z" />
                  </svg>
                  Generuję{tryb === "seria" ? ` ${liczbaOdcinkow} odcinków` : " film"}...
                </>
              ) : (
                <>
                  🎬 {tryb === "seria" ? `Generuj serię ${liczbaOdcinkow} odcinków` : "Generuj film"}
                </>
              )}
            </button>

            {blad && (
              <div className="glass p-4 rounded-xl border" style={{ borderColor: "rgba(239,68,68,0.3)", background: "rgba(239,68,68,0.08)" }}>
                <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: "#fca5a5" }}>
                  <span>⚠️</span> Błąd generacji
                </div>
                <p className="text-xs mt-1" style={{ color: "rgba(252,165,165,0.7)" }}>{blad}</p>
              </div>
            )}
          </div>

          {/* ── PRAWA KOLUMNA: PIPELINE + WYNIKI ────────────────── */}
          <div className="space-y-4">

            {/* Pipeline Steps */}
            <div className="glass p-5">
              <h3 className="text-sm font-bold uppercase tracking-wider mb-4" style={{ color: "var(--c-muted)" }}>
                Pipeline AI
              </h3>
              <div className="space-y-3">
                {kroki.map((krok, i) => (
                  <div key={krok.id} className="flex items-start gap-3">
                    {/* Dot */}
                    <div className="mt-1 flex-shrink-0">
                      {krok.status === "done" && (
                        <div className="w-5 h-5 rounded-full flex items-center justify-center text-xs"
                          style={{ background: "#10b981" }}>✓</div>
                      )}
                      {krok.status === "running" && (
                        <div className="w-5 h-5 rounded-full border-2 border-violet-500 border-t-transparent animate-spin" />
                      )}
                      {krok.status === "error" && (
                        <div className="w-5 h-5 rounded-full flex items-center justify-center text-xs"
                          style={{ background: "#ef4444" }}>✕</div>
                      )}
                      {krok.status === "idle" && (
                        <div className="w-5 h-5 rounded-full border"
                          style={{ borderColor: "var(--c-border)", background: "rgba(255,255,255,0.04)" }} />
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold truncate"
                          style={{ color: krok.status === "running" ? "#a78bfa" : krok.status === "done" ? "#6ee7b7" : "var(--c-text)" }}>
                          {krok.nazwa}
                        </span>
                        {krok.status === "running" && (
                          <span className="badge badge-purple text-xs">aktywny</span>
                        )}
                      </div>
                      <p className="text-xs mt-0.5" style={{ color: "var(--c-muted)" }}>{krok.opis}</p>
                    </div>
                  </div>
                ))}
              </div>

              {isGenerating && (
                <div className="progress-bar mt-4">
                  <div className="progress-fill"
                    style={{ width: `${Math.round((kroki.filter(k => k.status === "done").length / kroki.length) * 100)}%` }} />
                </div>
              )}
            </div>

            {/* Wyniki */}
            {wyniki.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-bold uppercase tracking-wider" style={{ color: "var(--c-muted)" }}>
                  {wyniki.length > 1 ? `Wygenerowane odcinki (${wyniki.length})` : "Gotowy film"}
                </h3>

                {wyniki.map((w) => (
                  <div key={w.sesja_id} className="glass p-4 card-hover">
                    <div className="flex items-start gap-3">
                      {/* Miniatura */}
                      <div className="w-16 h-28 rounded-lg overflow-hidden flex-shrink-0"
                        style={{ background: "rgba(255,255,255,0.05)" }}>
                        {w.miniatura ? (
                          <img src={`http://localhost:8000/api/v1/wideo/${w.sesja_id}/miniaturka`}
                            alt={w.tytul} className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-2xl">🎬</div>
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        {w.odcinek && (
                          <span className="badge badge-cyan mb-1 text-xs">Odcinek {w.odcinek}</span>
                        )}
                        <h4 className="font-bold text-sm truncate mb-2">{w.tytul}</h4>

                        {/* NVS Score */}
                        <div className="flex items-center gap-2 mb-3">
                          <div className="text-2xl font-black stat-number"
                            style={{ color: getScoreColor(w.nwv) }}>
                            {w.nwv}
                          </div>
                          <div>
                            <div className="text-xs font-bold">NVS Score</div>
                            <div className="text-xs" style={{ color: "var(--c-muted)" }}>
                              {w.nwv >= 85 ? "🔥 Wysoki" : w.nwv >= 60 ? "✅ Dobry" : "⚠️ Przeciętny"}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-3 text-xs" style={{ color: "var(--c-muted)" }}>
                          <span>⏱ {Math.round(w.czas_s)}s</span>
                          <span>💰 ${w.koszt_usd.toFixed(3)}</span>
                        </div>

                        <div className="flex gap-2 mt-3">
                          <a
                            href={`http://localhost:8000/api/v1/wideo/${w.sesja_id}/pobierz`}
                            className="btn-primary flex-1 justify-center"
                            style={{ padding: "8px 12px", fontSize: 12 }}
                            target="_blank" rel="noopener noreferrer"
                          >
                            ↓ Pobierz MP4
                          </a>
                          <Link
                            href={`/serie?sesja=${w.sesja_id}`}
                            className="btn-secondary"
                            style={{ padding: "8px 12px", fontSize: 12 }}
                          >
                            + Seria
                          </Link>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Stan idle - wskazówki */}
            {status === "idle" && (
              <div className="glass p-5">
                <h3 className="text-sm font-bold mb-3" style={{ color: "var(--c-muted)" }}>
                  Jak to działa?
                </h3>
                <div className="space-y-3">
                  {[
                    { icon: "1️⃣", text: "Wpisz temat lub wybierz gatunek" },
                    { icon: "2️⃣", text: "Ustaw liczbę odcinków i platformy" },
                    { icon: "3️⃣", text: "Kliknij Generuj — AI robi resztę" },
                    { icon: "4️⃣", text: "Pobierz gotowe MP4 i publikuj" },
                  ].map(h => (
                    <div key={h.icon} className="flex items-center gap-3 text-sm">
                      <span>{h.icon}</span>
                      <span style={{ color: "var(--c-muted)" }}>{h.text}</span>
                    </div>
                  ))}
                </div>

                <div className="divider my-4" />

                <div className="text-xs space-y-1" style={{ color: "var(--c-muted)" }}>
                  <div className="flex justify-between">
                    <span>Koszt / odcinek</span>
                    <span className="text-white">~$0.15</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Czas generacji</span>
                    <span className="text-white">~90 sekund</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Format</span>
                    <span className="text-white">MP4 1080×1920</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Napisy</span>
                    <span className="text-emerald-400">Animowane karaoke</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function StudioPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--c-bg)" }}>
        <div className="animate-spin w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full" />
      </div>
    }>
      <StudioInner />
    </Suspense>
  );
}
