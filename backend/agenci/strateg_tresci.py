"""
NEXUS — Agent 1: Strateg Treści
================================
Analizuje brief użytkownika i tworzy strategiczny plan treści.
Model: gpt-4o-mini (koszt ~$0.001 na wideo)

Kompetencje:
- Analiza briefa i kontekstu marki
- Wybór optymalnego haka narracyjnego
- Planowanie łuku emocjonalnego
- Predykcja zaangażowania
"""

import json
import structlog
from openai import AsyncOpenAI

from konfiguracja import konf
from agenci.schematy import StanNEXUS, PlanTresci

logger = structlog.get_logger(__name__)

# Systemowy prompt Stratega — zakotwiczony w nauce o retencji
SYSTEM_STRATEG = """Jesteś Strategiem Treści NEXUS — ekspertem od wirusowych krótkich wideo.

Twoja misja: transformować dowolny brief w precyzyjny plan treści oparty na nauce.

## Nauka o retencji (stosuj zawsze):
- Strefa 1 (0-3s): Pattern interrupt — musi złapać NATYCHMIAST
- Strefa 2 (3-15s): Otwórz pętlę ciekawości — widz musi chcieć wiedzieć "co dalej"
- Strefa 3 (15-80%): Dostarczaj wartość z zmianą wizualną co 2 sekundy
- Strefa 4 (ostatnie 10%): Zamknięcie pętli LUB CTA prowadzące do kolejnego wideo

## 7 archetypów haków:
1. pattern_interrupt — coś nieoczekiwanego wizualnie lub audio
2. luk_ciekawosci — "Tego nie wiedziałeś o..."
3. szok_humor — szokujące stwierdzenie lub absurd
4. intryga_wizualna — intrygujący obraz bez kontekstu
5. relatywnosc — "Jeśli robisz X, zatrzymaj się..."
6. wartosc_pierwsza — "Oto jak X w 60 sekund"
7. dowod_spoleczny — "95% ludzi nie wie, że..."

## Platformy i ich algorytmy:
- TikTok: mierzy prędkość zaangażowania w 1. godzinie, faworyzuje udostępnienia DM
- YouTube Shorts: liczy każde odtworzenie jako wyświetlenie, nagradza pętle
- Instagram Reels: "sends per reach" to najsilniejszy sygnał dotarcia

Odpowiadaj WYŁĄCZNIE w formacie JSON. Bądź precyzyjny i kreatywny."""


PROMPT_PLANU = """
Brief użytkownika: {brief}

Kontekst marki: {kontekst_marki}
Profil marki: {marka}
Platformy docelowe: {platforma}

Stwórz strategiczny plan treści. Odpowiedz w JSON:
{{
    "tytul": "chwytliwy tytuł koncepcji",
    "temat": "główny temat wideo",
    "platforma_docelowa": ["tiktok", "youtube"],
    "dlugosc_sekund": 60,
    "typ_haka": "luk_ciekawosci",
    "hak_wizualny": "opis pierwszej klatki — co widz widzi w 0 sekundzie",
    "hak_tekstowy": "tekst na ekranie w 0-2s (75%+ scrolluje bez dźwięku!)",
    "hak_werbalny": "pierwsze zdanie narracji (pewne, bezpośrednie)",
    "luk_emocjonalny": ["ciekawość", "napięcie", "zaskoczenie", "inspiracja"],
    "styl_wizualny": "opis stylu wizualnego (kolory, nastrój, estetyka)",
    "ton_glosu": "energiczny | spokojny | ekspercki | przyjacielski",
    "hashtagi": ["#hashtag1", "#hashtag2"],
    "przewidywane_zaangazowanie": 0.82
}}
"""


async def strateg_tresci(stan: StanNEXUS) -> dict:
    """
    Agent Strateg Treści — analizuje brief i tworzy plan.

    Args:
        stan: Aktualny stan przepływu NEXUS

    Returns:
        Aktualizacja stanu z plan_tresci
    """
    log = logger.bind(agent="strateg_tresci", iteracja=stan.get("iteracja", 0))
    log.info("Strateg Treści analizuje brief", brief_dl=len(stan["brief"]))

    klient = AsyncOpenAI(api_key=konf.OPENAI_API_KEY)

    prompt = PROMPT_PLANU.format(
        brief=stan["brief"],
        kontekst_marki=stan.get("kontekst_marki", "Brak profilu marki — twórz neutralnie"),
        marka=json.dumps(stan.get("marka", {}), ensure_ascii=False),
        platforma=", ".join(stan.get("platforma", ["tiktok", "youtube"]))
    )

    try:
        odpowiedz = await klient.chat.completions.create(
            model=konf.MODEL_EKONOMICZNY,  # gpt-4o-mini — wystarczający dla planu
            messages=[
                {"role": "system", "content": SYSTEM_STRATEG},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,            # Kreatywność przy planowaniu
            response_format={"type": "json_object"},
            max_tokens=1000,
        )

        dane = json.loads(odpowiedz.choices[0].message.content)

        # Policz koszt
        tokeny = odpowiedz.usage
        koszt = (tokeny.prompt_tokens * 0.15 + tokeny.completion_tokens * 0.60) / 1_000_000
        log.info("Plan treści wygenerowany", koszt_usd=round(koszt, 5))

        plan: PlanTresci = {
            "tytul": dane.get("tytul", "Wideo NEXUS"),
            "temat": dane.get("temat", stan["brief"][:100]),
            "platforma_docelowa": dane.get("platforma_docelowa", ["tiktok", "youtube"]),
            "dlugosc_sekund": min(int(dane.get("dlugosc_sekund", 60)), konf.MAKS_DLUGOSC_WIDEO),
            "typ_haka": dane.get("typ_haka", "luk_ciekawosci"),
            "hak_wizualny": dane.get("hak_wizualny", ""),
            "hak_tekstowy": dane.get("hak_tekstowy", ""),
            "hak_werbalny": dane.get("hak_werbalny", ""),
            "luk_emocjonalny": dane.get("luk_emocjonalny", ["ciekawość", "inspiracja"]),
            "styl_wizualny": dane.get("styl_wizualny", "nowoczesny, minimalistyczny"),
            "ton_glosu": dane.get("ton_glosu", "energiczny"),
            "hashtagi": dane.get("hashtagi", []),
            "przewidywane_zaangazowanie": float(dane.get("przewidywane_zaangazowanie", 0.7)),
        }

        return {
            "plan_tresci": plan,
            "krok_aktualny": "plan_gotowy",
            "koszt_calkowity_usd": stan.get("koszt_calkowity_usd", 0.0) + koszt,
        }

    except Exception as e:
        log.error("Błąd Stratega Treści", blad=str(e))
        return {
            "bledy": [f"Strateg Treści: {str(e)}"],
            "krok_aktualny": "blad_stratega",
        }
