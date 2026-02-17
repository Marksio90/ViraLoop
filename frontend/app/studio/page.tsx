/**
 * ViraLoop – Studio Wideo
 *
 * Główna strona tworzenia wideo z:
 * - Formularzem generowania (DSPy-optymalizowane prompty)
 * - Podglądem w przeglądarce (Diffusion Studio + WebGPU)
 * - Edytorem osi czasu (Yjs CRDT dla współpracy)
 * - Panelem głosu i muzyki
 * - Podglądem zgodności C2PA
 *
 * WebGPU osiągnął masową dostępność w przeglądarkach w listopadzie 2025:
 * Chrome, Firefox (Windows/macOS), Safari – wszystkie z WebGPU.
 * Diffusion Studio: WebCodecs + WebGPU → renderowanie w czasie rzeczywistym.
 */

"use client";

import { useState } from "react";
import { FormularzGenerowania } from "@/components/studio/formularz-generowania";
import { PodgladWideo } from "@/components/studio/podglad-wideo";
import { EdytorOsiCzasu } from "@/components/studio/edytor-osi-czasu";
import { PanelAudio } from "@/components/studio/panel-audio";
import { PanelZgodnosci } from "@/components/studio/panel-zgodnosci";
import { PanelWspolpracy } from "@/components/studio/panel-wspolpracy";

type WidokStudia = "generuj" | "edytuj" | "audio" | "zgodnosc";

export default function StronaStudia() {
  const [aktywnyWidok, setAktywnyWidok] = useState<WidokStudia>("generuj");
  const [idGenerowanego, setIdGenerowanego] = useState<string | null>(null);

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      {/* Nagłówek studia */}
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div>
          <h1 className="text-xl font-semibold">Studio wideo</h1>
          <p className="text-sm text-muted-foreground">
            Twórz i edytuj treści wideo z pomocą AI
          </p>
        </div>

        {/* Panel współpracy w czasie rzeczywistym */}
        <PanelWspolpracy />
      </div>

      {/* Zakładki nawigacyjne */}
      <nav className="flex gap-1 px-6 py-2 border-b bg-muted/30">
        {(
          [
            { id: "generuj", etykieta: "Generuj" },
            { id: "edytuj", etykieta: "Edytor osi czasu" },
            { id: "audio", etykieta: "Głos i muzyka" },
            { id: "zgodnosc", etykieta: "Zgodność C2PA" },
          ] as const
        ).map((zakl) => (
          <button
            key={zakl.id}
            onClick={() => setAktywnyWidok(zakl.id)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              aktywnyWidok === zakl.id
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-muted"
            }`}
          >
            {zakl.etykieta}
          </button>
        ))}
      </nav>

      {/* Główna treść studia */}
      <div className="flex-1 flex overflow-hidden">
        {/* Panel lewy – formularz/edytor */}
        <div className="w-[420px] border-r overflow-y-auto p-6">
          {aktywnyWidok === "generuj" && (
            <FormularzGenerowania
              onGenerowanieDodane={(id) => setIdGenerowanego(id)}
            />
          )}
          {aktywnyWidok === "edytuj" && <EdytorOsiCzasu idWideo={idGenerowanego} />}
          {aktywnyWidok === "audio" && <PanelAudio idWideo={idGenerowanego} />}
          {aktywnyWidok === "zgodnosc" && (
            <PanelZgodnosci idWideo={idGenerowanego} />
          )}
        </div>

        {/* Panel prawy – podgląd wideo (WebGPU) */}
        <div className="flex-1 bg-black flex items-center justify-center">
          <PodgladWideo idWideo={idGenerowanego} />
        </div>
      </div>
    </div>
  );
}
