/**
 * ViraLoop – Typy TypeScript dla modułu wideo
 */

export interface ZlecenieGeneracji {
  opis: string;
  model: string;
  rozdzielczosc: string;
  czas_trwania: number;
  jezyk: string;
  styl: string;
  audio: boolean;
  priorytet?: number;
}

export interface OdpowiedzGeneracji {
  id_zadania: string;
  status: "oczekiwanie" | "przetwarzanie" | "gotowe" | "blad";
  szacowany_czas_sekund: number;
  komunikat: string;
}

export interface StatusWideo {
  id_zadania: string;
  status: "oczekiwanie" | "przetwarzanie" | "gotowe" | "blad";
  postep_procent: number;
  url_wideo: string | null;
  url_miniatury: string | null;
  metadane: Record<string, unknown> | null;
  blad: string | null;
}

export interface MetrykaWideo {
  id_wideo: string;
  platforma: string;
  wyswietlenia: number;
  polubienia: number;
  komentarze: number;
  udostepnienia: number;
  wskaznik_klikniecia: number;
  sredni_czas_ogladania: number;
  zasieg: number;
  data_aktualizacji: string;
}

export interface TrendPlatformy {
  platforma: string;
  hashtag: string;
  liczba_filmow: number;
  wzrost_24h_procent: number;
  kategoria: string;
  popularnosc: number;
}

export type PlatformaWideo = "youtube" | "tiktok" | "instagram" | "facebook";

export type TierModelu =
  | "tier1"
  | "tier1.5"
  | "tier2"
  | "open";

export interface KonfiguracjaModelu {
  id: string;
  nazwa: string;
  tier: TierModelu;
  koszt_za_sekunde_usd: number;
  max_rozdzielczosc: string;
  natywne_audio: boolean;
  obsluguje_4k60: boolean;
  opis: string;
}
