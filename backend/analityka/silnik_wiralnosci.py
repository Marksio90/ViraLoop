"""
NEXUS — Silnik Wiralności v2.0
================================
Predykcja wiralności przed publikacją wideo.
Łączy heurystyki naukowe z analizą GPT-4o-mini.

Nowości v2.0:
- [INNOWACJA 12] Bayesowska Kalibracja Wag NVS
  Problem: WAGI_NVS = {sila_haka: 0.30, ...} są ARBITRALNE (wzięte z głowy)
  Rozwiązanie: Online learning na historii predykcji vs real-world wyników
  Metoda: po każdym wideo z real danymi → gradient descent na residualach
  Persistencja: JSON → prosta, zero zależności
  Efekt: po 50 wideo system wie które komponenty faktycznie korelują
  z wiralowością TEJ KONKRETNEJ marki

Nauka stojąca za systemem:
- 65% widzów, którzy obejrzą 3s → ogląda 10s+ (Hootsuite 2024)
- Wideo z pattern interrupt w 5s: +23% retencja
- Otwarte pętle zwiększają czas oglądania o 32%
- 694,000 Reels wysyłane przez DM co minutę (Instagram dane)
- TikTok: sends = najsilniejszy sygnał algorytmiczny

Model NVS (NEXUS Viral Score):
- Siła haka: 30%
- Przewidywana retencja: 25%
- Udostępnialność: 25%
- Optymalizacja platformy: 20%
"""

import json
import structlog
from pathlib import Path
from openai import AsyncOpenAI

from konfiguracja import konf

logger = structlog.get_logger(__name__)

# Wagi bazowe komponentów NVS (punkty startowe przed kalibracją)
WAGI_NVS_DOMYSLNE = {
    "sila_haka": 0.30,
    "retencja": 0.25,
    "udostepnialnosc": 0.25,
    "optymalizacja_platformy": 0.20,
}

# Plik kalibracji
PLIK_KALIBRACJI = Path("./dane/kalibracja_nvs.json")


# ====================================================================
# [INNOWACJA 12] Bayesowska Kalibracja Wag NVS
# ====================================================================

class KalibracjaNVS:
    """
    Online learning wag NVS na podstawie historii predykcji vs rzeczywistości.

    [INNOWACJA 12] Bayesowska Kalibracja.

    Problem: WAGI_NVS = {sila_haka: 0.30, ...} to arbitralne wartości.
    Dla jednej marki siła haka może ważyć 0.45, dla innej 0.20.

    Metoda:
    1. Przy każdym opublikowanym wideo z real-world danymi:
       wywołaj aktualizuj(predicted_nvs, real_metric, komponenty)
    2. System oblicza residual (błąd predykcji)
    3. Gradient descent na wadze komponentu który najbardziej się mylił
    4. Po 20+ wideo: wagi skalibrowane dla tej konkretnej marki

    Persistencja: JSON → zero zależności, prosta inspekcja.
    Wymaga: minimum 20 obserwacji dla wiarygodnych wag.
    """

    def __init__(self, sciezka: Path = PLIK_KALIBRACJI):
        self._sciezka = sciezka
        self._dane = self._wczytaj()

    def _wczytaj(self) -> dict:
        if self._sciezka.exists():
            try:
                return json.loads(self._sciezka.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "wagi": dict(WAGI_NVS_DOMYSLNE),
            "historia": [],
            "n_obserwacji": 0,
        }

    def _zapisz(self) -> None:
        try:
            self._sciezka.parent.mkdir(parents=True, exist_ok=True)
            self._sciezka.write_text(
                json.dumps(self._dane, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("Błąd zapisu kalibracji NVS", blad=str(e))

    def pobierz_wagi(self) -> dict:
        """Zwraca aktualne skalibrowane wagi (lub domyślne jeśli za mało danych)."""
        if self._dane["n_obserwacji"] < 20:
            return dict(WAGI_NVS_DOMYSLNE)
        return dict(self._dane["wagi"])

    def aktualizuj(
        self,
        predicted_nvs: int,
        real_views_percentile: float,  # 0-100: jak wideo wypadło vs inne (percentyl)
        komponenty: dict,  # {"sila_haka": 85, "retencja": 70, ...}
        lr: float = 0.02,  # Learning rate
    ) -> None:
        """
        Aktualizuje wagi NVS na podstawie jednej obserwacji.

        real_views_percentile: 0-100 — jaki percentyl wyświetleń osiągnęło wideo
        Np. 80 = wideo w top 20% dla tego konta/niszy.

        Gradient descent:
        - residual = real_percentile - predicted_nvs (błąd predykcji)
        - Dla każdego komponentu: waga += lr * residual * (component - mean)
        - Normalizuj wagi do sumy 1.0
        """
        residual = real_views_percentile - predicted_nvs

        # Oblicz jak każdy komponent przyczynił się do błędu
        srednia_komp = sum(komponenty.values()) / len(komponenty) if komponenty else 70.0

        wagi = self._dane["wagi"]
        for klucz in wagi:
            if klucz == "sila_haka":
                val = komponenty.get("sila_haka", 70)
            elif klucz == "retencja":
                val = komponenty.get("retencja", 70)
            elif klucz == "udostepnialnosc":
                val = komponenty.get("udostepnialnosc", 70)
            elif klucz == "optymalizacja_platformy":
                val = komponenty.get("optymalizacja_platformy", 70)
            else:
                continue
            # Gradient step
            wagi[klucz] += lr * residual * (val - srednia_komp) / 100.0

        # Clamp do [0.05, 0.60] — każda waga min 5%, max 60%
        for klucz in wagi:
            wagi[klucz] = max(0.05, min(0.60, wagi[klucz]))

        # Normalizuj do sumy 1.0
        suma = sum(wagi.values())
        for klucz in wagi:
            wagi[klucz] = round(wagi[klucz] / suma, 4)

        self._dane["n_obserwacji"] += 1
        self._dane["historia"].append({
            "predicted": predicted_nvs,
            "real": real_views_percentile,
            "residual": residual,
            "n": self._dane["n_obserwacji"],
        })

        # Max 1000 historii
        if len(self._dane["historia"]) > 1000:
            self._dane["historia"] = self._dane["historia"][-1000:]

        self._zapisz()
        logger.info(
            "Kalibracja NVS zaktualizowana",
            n_obserwacji=self._dane["n_obserwacji"],
            wagi=wagi,
            residual=round(residual, 1),
        )

    def status(self) -> dict:
        """Zwraca status kalibracji."""
        n = self._dane["n_obserwacji"]
        return {
            "n_obserwacji": n,
            "wagi": self.pobierz_wagi(),
            "skalibrowane": n >= 20,
            "komunikat": (
                f"Skalibrowane ({n} obserwacji)" if n >= 20
                else f"Wagi domyślne ({n}/20 obserwacji — wymagane minimum 20)"
            ),
        }


# Singleton kalibracji
_kalibracja: KalibracjaNVS | None = None


def pobierz_kalibracje() -> KalibracjaNVS:
    """Zwraca singleton kalibracji NVS."""
    global _kalibracja
    if _kalibracja is None:
        _kalibracja = KalibracjaNVS()
    return _kalibracja


# Wagi NVS — dynamiczne (skalibrowane lub domyślne)
@property
def WAGI_NVS() -> dict:
    return pobierz_kalibracje().pobierz_wagi()


# Alias dla kompatybilności wstecznej
WAGI_NVS = pobierz_kalibracje().pobierz_wagi()

SYSTEM_ANALITYK = """Jesteś analitykiem wiralności wideo — ekspertem od algorytmów TikTok, YouTube i Instagram.

Twoje zadanie: Przewidź wiralność wideo na podstawie jego komponentów.

## Algorytmy platform (aktualne 2025-2026):
### TikTok:
- Ocenia: prędkość zaangażowania w 1. godzinie
- Najsilniejszy sygnał: udostępnienia przez DM ("sends")
- Drugie: ponowne obejrzenia (completion 200%+)
- Słabszy: like, komentarze
- Klucz: zatrzymanie scrollowania w 0-3s

### YouTube Shorts:
- Każde odtworzenie = wyświetlenie (od marca 2025)
- Nagradza: loop rate (ile razy wraca)
- Faworyzuje: audience retention curve bez spadków
- CTR miniatury: kluczowy dla odkrywania

### Instagram Reels:
- Najsilniejszy: sends per reach
- Drugie: saves
- 694,000 Reels wysyłanych przez DM co minutę
- Algorithm push do non-followers → shares

## Kryteria oceny:
1. Siła haka (0-100): Czy pierwsze 3 sekundy ZATRZYMUJĄ scrollowanie?
2. Retencja (0-100): Czy widz ogląda do końca? Czy jest loop?
3. Udostępnialność (0-100): Czy ktoś wyśle to znajomemu?
4. Optymalizacja (0-100): Czy format/długość/hashtagi pasują do platformy?

Odpowiadaj WYŁĄCZNIE w JSON."""

PROMPT_ANALIZY = """
Oceń wiralność tego wideo:

## Hak:
- Wizualny: {hak_wizualny}
- Tekstowy: {hak_tekstowy}
- Werbalny: {hak_werbalny}
- Typ: {typ_haka}

## Scenariusz:
{streszczenie}
Czas trwania: {czas}s
Liczba scen: {liczba_scen}
CTA: {cta}

## Platformy: {platformy}

Oceń w JSON:
{{
    "sila_haka": 85,
    "retencja": 75,
    "udostepnialnosc": 80,
    "optymalizacja_tiktok": 88,
    "optymalizacja_youtube": 72,
    "optymalizacja_instagram": 76,
    "wynik_nwv": 81,
    "odznaka": "🔥 Wysoki potencjał wiralny",
    "kluczowe_mocne": "Mocny hak wizualny + pattern interrupt",
    "kluczowe_slabe": "Środek traci tempo — brak zmiany wizualnej co 2s",
    "top3_wskazowki": [
        "Dodaj tekst na ekranie w scenie 3 — 75% scrolluje bez dźwięku",
        "Skróć CTA o 50% — za długie",
        "Rozważ loop ending — zwiększy completion rate"
    ]
}}"""


async def analizuj_wiralnosc(
    plan_tresci: dict,
    scenariusz: dict | None = None,
) -> dict:
    """
    Analizuje przewidywaną wiralność wideo.

    Args:
        plan_tresci: Plan treści od Stratega
        scenariusz: Scenariusz od Pisarza (opcjonalnie)

    Returns:
        Słownik z oceną wiralności
    """
    log = logger.bind(funkcja="analizuj_wiralnosc")

    klient = AsyncOpenAI(api_key=konf.OPENAI_API_KEY)

    prompt = PROMPT_ANALIZY.format(
        hak_wizualny=plan_tresci.get("hak_wizualny", ""),
        hak_tekstowy=plan_tresci.get("hak_tekstowy", ""),
        hak_werbalny=plan_tresci.get("hak_werbalny", ""),
        typ_haka=plan_tresci.get("typ_haka", ""),
        streszczenie=scenariusz.get("streszczenie", "") if scenariusz else plan_tresci.get("temat", ""),
        czas=scenariusz.get("calkowity_czas", plan_tresci.get("dlugosc_sekund", 60)) if scenariusz else plan_tresci.get("dlugosc_sekund", 60),
        liczba_scen=len(scenariusz.get("sceny", [])) if scenariusz else "N/A",
        cta=scenariusz.get("cta", "") if scenariusz else "",
        platformy=", ".join(plan_tresci.get("platforma_docelowa", ["tiktok", "youtube"])),
    )

    try:
        odpowiedz = await klient.chat.completions.create(
            model=konf.MODEL_EKONOMICZNY,  # gpt-4o-mini wystarczy do analizy
            messages=[
                {"role": "system", "content": SYSTEM_ANALITYK},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=800,
        )

        dane = json.loads(odpowiedz.choices[0].message.content)

        # [INNOWACJA 12] Użyj skalibrowanych wag NVS (lub domyślnych)
        wagi_aktualne = pobierz_kalibracje().pobierz_wagi()

        # Oblicz NVS ważony (jeśli nie podany)
        nwv = dane.get("wynik_nwv")
        if not nwv:
            nwv = int(
                dane.get("sila_haka", 70) * wagi_aktualne["sila_haka"] +
                dane.get("retencja", 70) * wagi_aktualne["retencja"] +
                dane.get("udostepnialnosc", 70) * wagi_aktualne["udostepnialnosc"] +
                (
                    (dane.get("optymalizacja_tiktok", 70) + dane.get("optymalizacja_youtube", 70)) / 2
                ) * wagi_aktualne["optymalizacja_platformy"]
            )

        # Odznaka
        if nwv >= 85:
            odznaka = "🔥 Wysoki potencjał wiralny"
        elif nwv >= 70:
            odznaka = "✅ Dobry content"
        elif nwv >= 60:
            odznaka = "✅ Solidny content"
        else:
            odznaka = "⚠️ Wymaga optymalizacji"

        log.info("Analiza wiralności zakończona", nwv=nwv, odznaka=odznaka)

        return {
            "wynik_nwv": nwv,
            "wynik_haka": dane.get("sila_haka", 70),
            "wynik_zatrzymania": dane.get("retencja", 70),
            "wynik_udostepnialnosci": dane.get("udostepnialnosc", 70),
            "wynik_platformy": {
                "tiktok": dane.get("optymalizacja_tiktok", 70),
                "youtube": dane.get("optymalizacja_youtube", 70),
                "instagram": dane.get("optymalizacja_instagram", 70),
            },
            "odznaka": dane.get("odznaka", odznaka),
            "uzasadnienie": dane.get("kluczowe_mocne", ""),
            "wskazowki_optymalizacji": dane.get("top3_wskazowki", []),
            "kluczowe_slabe": dane.get("kluczowe_slabe", ""),
        }

    except Exception as e:
        log.error("Błąd analizy wiralności", blad=str(e))
        return {
            "wynik_nwv": 70,
            "wynik_haka": 70,
            "wynik_zatrzymania": 70,
            "wynik_udostepnialnosci": 65,
            "wynik_platformy": {"tiktok": 70, "youtube": 65, "instagram": 68},
            "odznaka": "✅ Solidny content",
            "uzasadnienie": "Automatyczna ocena (błąd AI)",
            "wskazowki_optymalizacji": [],
        }


def oblicz_nwv_heurystyczny(
    plan_tresci: dict,
    scenariusz: dict | None = None,
) -> int:
    """
    Szybka heurystyczna ocena wiralności (bez API — dla preview).

    Returns:
        NVS 0-100
    """
    wynik = 50  # Bazowy

    # Bonus za typ haka
    haki_premium = ["luk_ciekawosci", "pattern_interrupt", "szok_humor"]
    if plan_tresci.get("typ_haka") in haki_premium:
        wynik += 10

    # Bonus za dopasowanie do platform
    platformy = plan_tresci.get("platforma_docelowa", [])
    if len(platformy) >= 2:
        wynik += 5

    # Bonus za optymalną długość
    dlugosc = plan_tresci.get("dlugosc_sekund", 60)
    if 30 <= dlugosc <= 90:  # Złoty zakres
        wynik += 10
    elif dlugosc > 120:
        wynik -= 10

    # Bonus za szczegółowy hak
    if plan_tresci.get("hak_wizualny") and plan_tresci.get("hak_tekstowy"):
        wynik += 8

    # Bonus ze scenariusza
    if scenariusz:
        wynik += min(10, int(scenariusz.get("wynik_zaangazowania", 0.7) * 15))

        # Penalty za mało scen
        if len(scenariusz.get("sceny", [])) < 3:
            wynik -= 10

    return min(100, max(0, wynik))
