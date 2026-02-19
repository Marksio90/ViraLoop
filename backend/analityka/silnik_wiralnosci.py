"""
NEXUS — Silnik Wiralności
==========================
Predykcja wiralności przed publikacją wideo.
Łączy heurystyki naukowe z analizą GPT-4o-mini.

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
from openai import AsyncOpenAI

from konfiguracja import konf

logger = structlog.get_logger(__name__)

# Wagi komponentów NVS
WAGI_NVS = {
    "sila_haka": 0.30,
    "retencja": 0.25,
    "udostepnialnosc": 0.25,
    "optymalizacja_platformy": 0.20,
}

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

        # Oblicz NVS ważony (jeśli nie podany)
        nwv = dane.get("wynik_nwv")
        if not nwv:
            nwv = int(
                dane.get("sila_haka", 70) * WAGI_NVS["sila_haka"] +
                dane.get("retencja", 70) * WAGI_NVS["retencja"] +
                dane.get("udostepnialnosc", 70) * WAGI_NVS["udostepnialnosc"] +
                (
                    (dane.get("optymalizacja_tiktok", 70) + dane.get("optymalizacja_youtube", 70)) / 2
                ) * WAGI_NVS["optymalizacja_platformy"]
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
