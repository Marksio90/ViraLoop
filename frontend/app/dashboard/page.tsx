/**
 * ViraLoop – Panel główny (Dashboard)
 *
 * Wyświetla kluczowe metryki, ostatnie wideo i aktywne kampanie.
 * Dane pobierane z ClickHouse przez FastAPI.
 *
 * Używa dyrektywy "use cache" (Next.js 16) zamiast niejawnego cachowania.
 */

"use cache";

import { Suspense } from "react";
import { KartyMetryk } from "@/components/dashboard/karty-metryk";
import { WykresTrendow } from "@/components/dashboard/wykres-trendow";
import { TabeaOstatnichWideo } from "@/components/dashboard/tabela-ostatnich-wideo";
import { StatusOptymalizacji } from "@/components/dashboard/status-optymalizacji";
import { SzybkieGenerowanie } from "@/components/dashboard/szybkie-generowanie";
import { SkeletonKarty } from "@/components/ui/skeleton";

export default function StronaPanelu() {
  return (
    <div className="przestrzen-tresc">
      {/* Nagłówek strony */}
      <div className="mb-8">
        <h1 className="tekst-naglowek-1">Panel główny</h1>
        <p className="tekst-opis mt-2">
          Przegląd wydajności Twoich treści wideo na wszystkich platformach
        </p>
      </div>

      {/* Karty z kluczowymi metrykami (KPI) */}
      <Suspense
        fallback={
          <div className="siatka-4-kolumny">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonKarty key={i} />
            ))}
          </div>
        }
      >
        <KartyMetryk />
      </Suspense>

      {/* Wykres trendów + Szybkie generowanie */}
      <div className="mt-8 siatka-2-kolumny">
        <Suspense fallback={<SkeletonKarty wysokosc="h-80" />}>
          <WykresTrendow />
        </Suspense>

        <Suspense fallback={<SkeletonKarty wysokosc="h-80" />}>
          <StatusOptymalizacji />
        </Suspense>
      </div>

      {/* Szybkie generowanie wideo */}
      <div className="mt-8">
        <SzybkieGenerowanie />
      </div>

      {/* Tabela ostatnich wideo */}
      <div className="mt-8">
        <Suspense fallback={<SkeletonKarty wysokosc="h-96" />}>
          <TabeaOstatnichWideo />
        </Suspense>
      </div>
    </div>
  );
}
