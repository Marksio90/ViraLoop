/**
 * ViraLoop – Strona analityki
 *
 * Kompleksowy panel analityczny z danymi z:
 * - YouTube Data API v3 (10K darmowych jednostek/dzień)
 * - TikTok Research API (publiczne dane wideo/użytkownika)
 * - Instagram Graph API (Reels skip rate + repost counts od grudnia 2025)
 * - ClickHouse (sub-sekundowe zapytania nad miliardami metryk)
 *
 * Wykresy: Recharts (standardowe) + Tremor (biznesowe KPI + sparklines)
 */

"use cache";

import { Suspense } from "react";
import { PanelGlowny } from "@/components/analytics/panel-glowny";
import { WykresWydajnosci } from "@/components/analytics/wykres-wydajnosci";
import { TabelaTopWideo } from "@/components/analytics/tabela-top-wideo";
import { WykresOptymalizacji } from "@/components/analytics/wykres-optymalizacji";
import { TrendyPlatform } from "@/components/analytics/trendy-platform";
import { SkeletonKarty } from "@/components/ui/skeleton";

export default function StronaAnalityki() {
  return (
    <div className="przestrzen-tresc">
      {/* Nagłówek */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="tekst-naglowek-1">Analityka</h1>
          <p className="tekst-opis mt-2">
            Metryki wydajności, trendy platform i wyniki optymalizacji ewolucyjnej
          </p>
        </div>

        {/* Wybór zakresu dat */}
        <div className="flex gap-2">
          {["7 dni", "30 dni", "90 dni", "Rok"].map((okres) => (
            <button
              key={okres}
              className="px-3 py-1.5 text-sm rounded-md border hover:bg-muted transition-colors"
            >
              {okres}
            </button>
          ))}
        </div>
      </div>

      {/* KPI – panel główny z Tremor */}
      <Suspense fallback={<SkeletonKarty wysokosc="h-32" />}>
        <PanelGlowny />
      </Suspense>

      {/* Wykresy wydajności */}
      <div className="mt-8 grid grid-cols-2 gap-6">
        <Suspense fallback={<SkeletonKarty wysokosc="h-64" />}>
          <WykresWydajnosci />
        </Suspense>

        <Suspense fallback={<SkeletonKarty wysokosc="h-64" />}>
          <WykresOptymalizacji />
        </Suspense>
      </div>

      {/* Trendy platform */}
      <div className="mt-8">
        <Suspense fallback={<SkeletonKarty wysokosc="h-48" />}>
          <TrendyPlatform />
        </Suspense>
      </div>

      {/* Tabela top wideo */}
      <div className="mt-8">
        <Suspense fallback={<SkeletonKarty wysokosc="h-96" />}>
          <TabelaTopWideo />
        </Suspense>
      </div>
    </div>
  );
}
