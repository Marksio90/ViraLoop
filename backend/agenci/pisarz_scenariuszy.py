"""
NEXUS — Agent 2: Pisarz Scenariuszy
=====================================
Tworzy gotowy scenariusz produkcyjny z podziałem na sceny.
Model: gpt-4o-mini (koszt ~$0.002 na wideo)

Kompetencje:
- Pisanie scenariusza scena po scenie
- Optymalizacja pod platformy docelowe
- Anotacje wizualne i timingowe
- Scoring zaangażowania
"""

import json
import structlog
from openai import AsyncOpenAI

from konfiguracja import konf
from agenci.schematy import StanNEXUS, ScenariuszWideo, ScenariuszScena

logger = structlog.get_logger(__name__)

SYSTEM_PISARZ = """Jesteś Pisarzem Scenariuszy NEXUS — tworzysz angażujące scenariusze wideo.

## Twoje zasady:
1. HAKI: Pierwsze 3 sekundy decydują o wszystkim. 65% widzów, którzy obejrzą 3 sekundy, zostanie na 10+.
2. PĘTLE: Otwieraj pytania, które musisz zamknąć. Widz musi chcieć wiedzieć "co dalej".
3. RYTM: Zmiana wizualna co 2 sekundy w środkowej sekcji.
4. PROSTOTA: Maks. jedna myśl na scenę. Jasne, proste zdania.
5. EMOCJE: Każda scena powinna wywołać konkretną emocję.
6. CTA: Koniec musi prowadzić do działania (komentarz, udostępnienie, kolejne wideo).

## Format sceny:
- opis_wizualny: szczegółowy prompt dla DALL-E 3 (po angielsku dla lepszych wyników)
- tekst_narracji: to, co mówi lektor
- tekst_na_ekranie: napisy/tytuły (krótkie! max 5-7 słów)
- emocja: dominująca emocja sceny
- tempo: wolne | normalne | szybkie

Odpowiadaj WYŁĄCZNIE w JSON."""


PROMPT_SCENARIUSZA = """
Plan treści od Stratega:
{plan_json}

Brief użytkownika: {brief}

Stwórz gotowy scenariusz z {liczba_scen} scenami.
Łączny czas: {dlugosc} sekund.

Odpowiedz w JSON:
{{
    "tytul": "ostateczny tytuł wideo",
    "streszczenie": "1-2 zdania o czym jest wideo",
    "hook_otwierający": "dosłowny tekst pierwszego zdania narracji",
    "cta": "Call to Action na końcu wideo",
    "calkowity_czas": {dlugosc},
    "liczba_slow": 150,
    "wynik_zaangazowania": 0.83,
    "sceny": [
        {{
            "numer": 1,
            "czas_start": 0.0,
            "czas_koniec": 3.0,
            "opis_wizualny": "DALL-E prompt in English: extreme close-up of...",
            "tekst_narracji": "Polski tekst narracji dla tej sceny",
            "tekst_na_ekranie": "Krótki tekst",
            "emocja": "zaskoczenie",
            "tempo": "szybkie"
        }}
    ]
}}

WAŻNE:
- opis_wizualny ZAWSZE po angielsku (lepsze wyniki DALL-E)
- tekst_narracji ZAWSZE po polsku
- Pierwsza scena (0-3s): TYLKO hak — nic więcej
- Każda scena max 15-20 sekund
"""


def oblicz_liczbe_scen(dlugosc_s: int) -> int:
    """Oblicza optymalną liczbę scen na podstawie długości wideo."""
    if dlugosc_s <= 30:
        return 3
    elif dlugosc_s <= 60:
        return 5
    elif dlugosc_s <= 90:
        return 7
    else:
        return min(10, dlugosc_s // 15)


async def pisarz_scenariuszy(stan: StanNEXUS) -> dict:
    """
    Agent Pisarz Scenariuszy — tworzy produkcyjny scenariusz.

    Args:
        stan: Stan NEXUS z plan_tresci

    Returns:
        Aktualizacja stanu ze scenariuszem
    """
    log = logger.bind(agent="pisarz_scenariuszy", iteracja=stan.get("iteracja", 0))

    if not stan.get("plan_tresci"):
        return {
            "bledy": ["Pisarz Scenariuszy: brak planu treści"],
            "krok_aktualny": "blad_pisarza",
        }

    plan = stan["plan_tresci"]
    liczba_scen = oblicz_liczbe_scen(plan["dlugosc_sekund"])
    log.info("Pisarz Scenariuszy tworzy scenariusz", sceny=liczba_scen, czas=plan["dlugosc_sekund"])

    klient = AsyncOpenAI(api_key=konf.OPENAI_API_KEY)

    # Jeśli to ponowna próba, dodaj feedback z recenzji
    kontekst_poprawki = ""
    if stan.get("iteracja", 0) > 0 and stan.get("ocena_jakosci"):
        ocena = stan["ocena_jakosci"]
        kontekst_poprawki = f"\n\nFEEDBACK DO POPRAWY:\nSłabe punkty: {ocena.get('slabe_punkty', [])}\nSugestie: {ocena.get('sugestie', [])}"

    prompt = PROMPT_SCENARIUSZA.format(
        plan_json=json.dumps(plan, ensure_ascii=False, indent=2),
        brief=stan["brief"],
        liczba_scen=liczba_scen,
        dlugosc=plan["dlugosc_sekund"],
    ) + kontekst_poprawki

    try:
        odpowiedz = await klient.chat.completions.create(
            model=konf.MODEL_EKONOMICZNY,  # gpt-4o-mini
            messages=[
                {"role": "system", "content": SYSTEM_PISARZ},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
            max_tokens=2500,
        )

        dane = json.loads(odpowiedz.choices[0].message.content)

        # Walidacja i normalizacja scen
        sceny_surowe = dane.get("sceny", [])
        sceny: list[ScenariuszScena] = []
        czas_aktualny = 0.0

        for i, scena_s in enumerate(sceny_surowe):
            czas_koniec = float(scena_s.get("czas_koniec", czas_aktualny + 10))
            sceny.append(ScenariuszScena(
                numer=i + 1,
                czas_start=float(scena_s.get("czas_start", czas_aktualny)),
                czas_koniec=czas_koniec,
                opis_wizualny=scena_s.get("opis_wizualny", ""),
                tekst_narracji=scena_s.get("tekst_narracji", ""),
                tekst_na_ekranie=scena_s.get("tekst_na_ekranie", ""),
                emocja=scena_s.get("emocja", "neutralna"),
                tempo=scena_s.get("tempo", "normalne"),
            ))
            czas_aktualny = czas_koniec

        calkowity_czas = sceny[-1]["czas_koniec"] if sceny else plan["dlugosc_sekund"]

        scenariusz: ScenariuszWideo = {
            "tytul": dane.get("tytul", plan["tytul"]),
            "streszczenie": dane.get("streszczenie", ""),
            "sceny": sceny,
            "hook_otwierający": dane.get("hook_otwierający", sceny[0]["tekst_narracji"] if sceny else ""),
            "cta": dane.get("cta", "Obserwuj, aby nie przegapić!"),
            "calkowity_czas": calkowity_czas,
            "liczba_slow": dane.get("liczba_slow", sum(len(s["tekst_narracji"].split()) for s in sceny)),
            "wynik_zaangazowania": float(dane.get("wynik_zaangazowania", 0.75)),
        }

        # Koszt
        tokeny = odpowiedz.usage
        koszt = (tokeny.prompt_tokens * 0.15 + tokeny.completion_tokens * 0.60) / 1_000_000

        log.info("Scenariusz gotowy", sceny=len(sceny), czas=calkowity_czas, koszt_usd=round(koszt, 5))

        return {
            "scenariusz": scenariusz,
            "krok_aktualny": "scenariusz_gotowy",
            "koszt_calkowity_usd": stan.get("koszt_calkowity_usd", 0.0) + koszt,
        }

    except Exception as e:
        log.error("Błąd Pisarza Scenariuszy", blad=str(e))
        return {
            "bledy": [f"Pisarz Scenariuszy: {str(e)}"],
            "krok_aktualny": "blad_pisarza",
        }
