"use client";

import { useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

// ── TYPY ────────────────────────────────────────────────────────────

interface Odcinek {
  numer: number;
  sesja_id: string;
  tytul: string;
  status: "gotowy" | "generacja" | "oczekuje";
  nwv: number;
  czas_trwania_s: number;
  gotowy: boolean;
}

interface Seria {
  seria_id: string;
  tytul: string;
  gatunek: string;
  emoji: string;
  odcinki: Odcinek[];
  status: "aktywna" | "ukonczona" | "wstrzymana";
  data_utworzenia: string;
  calkowity_nwv: number;
  wyswietlenia_mock: string;
}

// ── MOCK DATA (zastąpi prawdziwe API po podłączeniu) ────────────────

const MOCK_SERIE: Seria[] = [
  {
    seria_id: "ser_001",
    tytul: "Sekrety Watykanu",
    gatunek: "Tajemnice Historii",
    emoji: "⛪",
    status: "aktywna",
    data_utworzenia: "2024-02-15",
    calkowity_nwv: 88,
    wyswietlenia_mock: "2.1M",
    odcinki: [
      { numer: 1, sesja_id: "s01", tytul: "Ukryte archiwum Piusa XII", status: "gotowy", nwv: 91, czas_trwania_s: 58, gotowy: true },
      { numer: 2, sesja_id: "s02", tytul: "Masoneria i Watykan — prawda", status: "gotowy", nwv: 87, czas_trwania_s: 62, gotowy: true },
      { numer: 3, sesja_id: "s03", tytul: "Tajemny Bank Watykański", status: "gotowy", nwv: 84, czas_trwania_s: 55, gotowy: true },
      { numer: 4, sesja_id: "s04", tytul: "Egzorcyści na usługach papieża", status: "oczekuje", nwv: 0, czas_trwania_s: 0, gotowy: false },
    ],
  },
  {
    seria_id: "ser_002",
    tytul: "Tesla vs Edison",
    gatunek: "Wyścig Technologii",
    emoji: "⚡",
    status: "ukonczona",
    data_utworzenia: "2024-02-10",
    calkowity_nwv: 82,
    wyswietlenia_mock: "890K",
    odcinki: [
      { numer: 1, sesja_id: "t01", tytul: "Geniusze czy wrogowie?", status: "gotowy", nwv: 85, czas_trwania_s: 60, gotowy: true },
      { numer: 2, sesja_id: "t02", tytul: "Prąd zmienny, który zmienił świat", status: "gotowy", nwv: 83, czas_trwania_s: 57, gotowy: true },
      { numer: 3, sesja_id: "t03", tytul: "Kradzież patentów — wielki spisek", status: "gotowy", nwv: 79, czas_trwania_s: 63, gotowy: true },
    ],
  },
  {
    seria_id: "ser_003",
    tytul: "Zaginiony skarb Templariuszy",
    gatunek: "Zbrodnie i Sekrety",
    emoji: "💎",
    status: "aktywna",
    data_utworzenia: "2024-02-18",
    calkowity_nwv: 93,
    wyswietlenia_mock: "4.3M",
    odcinki: [
      { numer: 1, sesja_id: "k01", tytul: "Piątek Trzynastego — prawdziwa historia", status: "gotowy", nwv: 95, czas_trwania_s: 61, gotowy: true },
      { numer: 2, sesja_id: "k02", tytul: "Gdzie zniknęło złoto rycerzy?", status: "gotowy", nwv: 92, czas_trwania_s: 58, gotowy: true },
      { numer: 3, sesja_id: "k03", tytul: "Katedra w Chartres — sekretny kod", status: "generacja", nwv: 0, czas_trwania_s: 0, gotowy: false },
    ],
  },
];

function getScoreColor(score: number) {
  if (score >= 85) return "#10b981";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

function getStatusBadge(status: Seria["status"]) {
  if (status === "aktywna") return <span className="badge badge-green">Aktywna</span>;
  if (status === "ukonczona") return <span className="badge badge-cyan">Ukończona</span>;
  return <span className="badge badge-amber">Wstrzymana</span>;
}

// ── KOMPONENT SERII ──────────────────────────────────────────────────

function SeriaCard({ seria, onClick, aktywna }: { seria: Seria; onClick: () => void; aktywna: boolean }) {
  const gotowych = seria.odcinki.filter(o => o.gotowy).length;
  const wszystkich = seria.odcinki.length;

  return (
    <div
      onClick={onClick}
      className="glass p-5 card-hover cursor-pointer"
      style={{
        borderColor: aktywna ? "rgba(124,58,237,0.45)" : "var(--c-border)",
        background: aktywna ? "rgba(124,58,237,0.06)" : undefined,
      }}
    >
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <div className="text-3xl">{seria.emoji}</div>
          <div>
            <h3 className="font-bold text-base leading-tight">{seria.tytul}</h3>
            <p className="text-xs mt-0.5" style={{ color: "var(--c-muted)" }}>{seria.gatunek}</p>
          </div>
        </div>
        {getStatusBadge(seria.status)}
      </div>

      {/* Odcinki progress */}
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1.5" style={{ color: "var(--c-muted)" }}>
          <span>{gotowych}/{wszystkich} odcinków</span>
          <span className="font-bold" style={{ color: getScoreColor(seria.calkowity_nwv) }}>
            NVS {seria.calkowity_nwv}
          </span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${(gotowych / wszystkich) * 100}%` }} />
        </div>
      </div>

      <div className="flex items-center justify-between text-xs" style={{ color: "var(--c-muted)" }}>
        <span>👁 {seria.wyswietlenia_mock} wyśw.</span>
        <span>{new Date(seria.data_utworzenia).toLocaleDateString("pl-PL")}</span>
      </div>
    </div>
  );
}

// ── DETAL SERII ──────────────────────────────────────────────────────

function SeriaDetail({ seria }: { seria: Seria }) {
  const [generujOdcinek, setGenerujOdcinek] = useState(false);

  const kontynuuj = async () => {
    setGenerujOdcinek(true);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/serie/${seria.seria_id}/kontynuuj`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ liczba_nowych_odcinkow: 1 }),
      });
      if (res.ok) {
        alert("Generacja nowego odcinka uruchomiona! Odśwież za chwilę.");
      }
    } catch {
      alert("Błąd połączenia z API. Sprawdź czy backend jest uruchomiony.");
    }
    setGenerujOdcinek(false);
  };

  return (
    <div className="glass p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="text-4xl">{seria.emoji}</div>
          <div>
            <h2 className="text-xl font-black">{seria.tytul}</h2>
            <p className="text-sm" style={{ color: "var(--c-muted)" }}>{seria.gatunek}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {getStatusBadge(seria.status)}
          <button
            onClick={kontynuuj}
            disabled={generujOdcinek}
            className="btn-primary"
            style={{ padding: "8px 14px", fontSize: 13 }}
          >
            {generujOdcinek ? (
              <><svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z" />
              </svg> Generuję...</>
            ) : "+ Nowy odcinek"}
          </button>
        </div>
      </div>

      {/* Statystyki serii */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="glass-light p-3 text-center">
          <div className="stat-number text-2xl gradient-text">{seria.odcinki.length}</div>
          <div className="text-xs mt-1" style={{ color: "var(--c-muted)" }}>Odcinków</div>
        </div>
        <div className="glass-light p-3 text-center">
          <div className="stat-number text-2xl" style={{ color: getScoreColor(seria.calkowity_nwv) }}>
            {seria.calkowity_nwv}
          </div>
          <div className="text-xs mt-1" style={{ color: "var(--c-muted)" }}>NVS avg</div>
        </div>
        <div className="glass-light p-3 text-center">
          <div className="stat-number text-2xl text-emerald-400">{seria.wyswietlenia_mock}</div>
          <div className="text-xs mt-1" style={{ color: "var(--c-muted)" }}>Wyświetleń</div>
        </div>
      </div>

      {/* Lista odcinków */}
      <h3 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: "var(--c-muted)" }}>
        Odcinki
      </h3>
      <div className="space-y-2">
        {seria.odcinki.map((od) => (
          <div key={od.sesja_id} className="glass-light p-4 rounded-xl">
            <div className="flex items-center gap-3">
              {/* Status */}
              <div className="flex-shrink-0">
                {od.status === "gotowy" && (
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                    style={{ background: "rgba(16,185,129,0.15)", color: "#6ee7b7", border: "1px solid rgba(16,185,129,0.3)" }}>
                    ✓
                  </div>
                )}
                {od.status === "generacja" && (
                  <div className="w-8 h-8 rounded-full border-2 border-violet-500 border-t-transparent animate-spin" />
                )}
                {od.status === "oczekuje" && (
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs"
                    style={{ background: "rgba(245,158,11,0.1)", color: "#fcd34d", border: "1px solid rgba(245,158,11,0.2)" }}>
                    {od.numer}
                  </div>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold" style={{ color: "var(--c-muted)" }}>
                    Odc. {od.numer}
                  </span>
                  {od.nwv > 0 && (
                    <span className="text-xs font-bold" style={{ color: getScoreColor(od.nwv) }}>
                      NVS {od.nwv}
                    </span>
                  )}
                </div>
                <p className="text-sm font-semibold truncate">{od.tytul}</p>
                {od.czas_trwania_s > 0 && (
                  <p className="text-xs" style={{ color: "var(--c-muted)" }}>{od.czas_trwania_s}s</p>
                )}
              </div>

              {od.gotowy && (
                <div className="flex gap-2 flex-shrink-0">
                  <a
                    href={`http://localhost:8000/api/v1/wideo/${od.sesja_id}/pobierz`}
                    target="_blank" rel="noopener noreferrer"
                    className="btn-ghost text-xs"
                    style={{ padding: "6px 10px" }}
                  >
                    ↓ MP4
                  </a>
                </div>
              )}

              {od.status === "oczekuje" && (
                <span className="text-xs" style={{ color: "var(--c-muted)" }}>Oczekuje</span>
              )}
              {od.status === "generacja" && (
                <span className="badge badge-purple text-xs">Generacja...</span>
              )}
            </div>

            {/* Cliffhanger hint */}
            {od.numer < seria.odcinki.length && od.gotowy && (
              <div className="mt-2 flex items-center gap-1.5 text-xs" style={{ color: "var(--c-muted)" }}>
                <span>→</span>
                <span className="italic">Prowadzi do odcinka {od.numer + 1}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Dodaj więcej odcinków */}
      {seria.status === "aktywna" && (
        <button
          onClick={kontynuuj}
          disabled={generujOdcinek}
          className="btn-secondary w-full mt-4 justify-center"
        >
          + Rozbuduj serię o kolejne odcinki
        </button>
      )}
    </div>
  );
}

// ── GŁÓWNY KOMPONENT ────────────────────────────────────────────────

function SerieInner() {
  const [serie] = useState<Seria[]>(MOCK_SERIE);
  const [aktywna, setAktywna] = useState<Seria | null>(MOCK_SERIE[0]);
  const [filtr, setFiltr] = useState<"wszystkie" | "aktywna" | "ukonczona">("wszystkie");

  const filtrowane = serie.filter(s => filtr === "wszystkie" || s.status === filtr);

  return (
    <div className="min-h-screen relative" style={{ background: "var(--c-bg)" }}>
      {/* Orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 left-0 w-[400px] h-[400px] rounded-full opacity-10"
          style={{ background: "radial-gradient(circle, #7c3aed 0%, transparent 70%)" }} />
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
          <span className="font-semibold text-sm">Serie</span>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/studio" className="btn-primary" style={{ padding: "8px 16px", fontSize: 13 }}>
            + Nowa seria
          </Link>
        </div>
      </nav>

      <div className="relative z-10 max-w-7xl mx-auto px-4 md:px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl md:text-3xl font-black mb-1">
              Moje <span className="gradient-text">Serie</span>
            </h1>
            <p className="text-sm" style={{ color: "var(--c-muted)" }}>
              {serie.length} serii · {serie.reduce((acc, s) => acc + s.odcinki.filter(o => o.gotowy).length, 0)} gotowych odcinków
            </p>
          </div>

          {/* Filtry */}
          <div className="glass p-1 inline-flex rounded-xl gap-1">
            {(["wszystkie", "aktywna", "ukonczona"] as const).map(f => (
              <button
                key={f}
                onClick={() => setFiltr(f)}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold transition-all capitalize"
                style={{
                  background: filtr === f ? "linear-gradient(135deg, #7c3aed, #4f46e5)" : "transparent",
                  color: filtr === f ? "#fff" : "var(--c-muted)",
                }}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6">
          {/* Lista serii */}
          <div className="space-y-3">
            {filtrowane.map(s => (
              <SeriaCard
                key={s.seria_id}
                seria={s}
                onClick={() => setAktywna(s)}
                aktywna={aktywna?.seria_id === s.seria_id}
              />
            ))}

            <Link href="/studio" className="btn-secondary w-full justify-center text-sm">
              + Utwórz nową serię
            </Link>
          </div>

          {/* Detail panel */}
          {aktywna ? (
            <SeriaDetail seria={aktywna} />
          ) : (
            <div className="glass p-10 text-center flex flex-col items-center justify-center">
              <div className="text-5xl mb-4">🎬</div>
              <h3 className="font-bold text-lg mb-2">Wybierz serię</h3>
              <p className="text-sm mb-6" style={{ color: "var(--c-muted)" }}>
                Kliknij na serię z listy aby zobaczyć odcinki i zarządzać produkcją
              </p>
              <Link href="/studio" className="btn-primary">
                + Stwórz pierwszą serię
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function SeriePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--c-bg)" }}>
        <div className="animate-spin w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full" />
      </div>
    }>
      <SerieInner />
    </Suspense>
  );
}
