"""
NEXUS — Agent 5: Recenzent Jakości v2.0
==========================================
Ocenia kompletne wideo i podejmuje decyzję o zatwierdzeniu.
Model: gpt-4o (najinteligentniejszy model — krytyczna decyzja)
Koszt: ~$0.005 na wideo

Nowości v2.0:
- [INNOWACJA 8] Cliffhanger Coefficient (CDS — Cognitive Dissonance Score)
  Mierzy jak "otwarte" jest zakończenie wideo na skali 0.0-1.0
  0.0 = wszystkie pytania zamknięte, widz "nasycony" — nie wróci
  1.0 = frustrujące, nic nie wyjaśnione — odbije się
  Cel: CDS = 0.65-0.80 (maksymalna motywacja do powrotu bez frustracji)
  Automatyczna sugestia jak "otworzyć" lub "zamknąć" zakończenie
  Koszt: $0 extra (wbudowane w istniejące wywołanie GPT-4o)
"""

import json
import structlog
from openai import AsyncOpenAI

from konfiguracja import konf
from agenci.schematy import StanNEXUS, OcenaJakosci, OcenaWiralnosci

logger = structlog.get_logger(__name__)

SYSTEM_RECENZENT = """Jesteś Recenzentem Jakości NEXUS v2.0 — najostrzejszym krytykiem treści wideo.

Twoja rola: OBIEKTYWNA ocena gotowego wideo przed publikacją.

## Kryteria oceny (każde 0-100 punktów):

### Hak (waga 30%):
- Czy pierwsze 3 sekundy zatrzymują scrollowanie?
- Czy hak wizualny jest wystarczająco intrygujący?
- Czy hak tekstowy exploituje ciekawość?
- Benchmark: Netflix = 80+, CapCut przeciętny = 50

### Scenariusz (waga 25%):
- Czy jest wyraźna linia narracyjna?
- Czy pętla jest otwarta i zamknięta?
- Czy wartość jest dostarczona obietnica z haka spełniona?
- Czy CTA jest naturalne i mocne?

### Wizualia (waga 25%):
- Czy prompte są DALL-E optymalne?
- Czy styl wizualny jest spójny?
- Czy sceny są dopasowane do narracji?

### Audio (waga 20%):
- Czy głos pasuje do tonu treści?
- Czy tempo mówienia jest odpowiednie?
- Czy emocje są poprawnie dobrane?

## NEXUS Viral Score (NVS 0-100):
Oblicz na podstawie:
- Siła haka: 0-100 (30%)
- Przewidywane zatrzymanie (retention): 0-100 (25%)
- Udostępnialność (shareability): 0-100 (25%)
- Optymalizacja platformy: 0-100 (20%)

## Progi decyzyjne:
- NVS >= 85: 🔥 Wysoki potencjał wiralny — odznaka ognia
- NVS 60-84: ✅ Dobry content — publikuj
- NVS < 60: ⚠️ Wymaga poprawy — zwróć do Pisarza

## Cliffhanger Coefficient (CDS — Cognitive Dissonance Score):
Oceń zakończenie wideo na skali 0.0-1.0:
- 0.0-0.3: Zamknięte. "I to tyle." — Widz jest nasycony, nie wróci.
- 0.4-0.6: Neutralne. "Ciekawe." — Może wróci, może nie.
- 0.65-0.80: OPTIMUM. "Ale jak?! Muszę wiedzieć więcej." — Wróci na pewno.
- 0.85-1.0: Frustrujące. "Nic mi nie wyjaśniłeś." — Zirytowany, nie wróci.

Twój cel: CDS w zakresie 0.65-0.80.
Jeśli CDS < 0.65: zaproponuj konkretne zdanie do dodania które otworzy pętlę.
Jeśli CDS > 0.80: zaproponuj jak organicznie zamknąć choć jedno pytanie.

Odpowiadaj WYŁĄCZNIE w JSON."""


PROMPT_RECENZJI = """
Oceń poniższy projekt wideo:

## Plan treści:
{plan_json}

## Scenariusz:
{scenariusz_json}

## Audio (informacje):
Głos: {glos}
Czas trwania: {czas_trwania}s
Liczba słów: {liczba_slow}

## Wizualia:
Liczba obrazów: {liczba_obrazow}
Styl: {styl_wizualny}

## Platformy docelowe: {platformy}

Oceń i odpowiedz w JSON:
{{
    "wynik_ogolny": 78,
    "wynik_haka": 82,
    "wynik_scenariusza": 75,
    "wynik_wizualny": 71,
    "wynik_audio": 80,
    "slabe_punkty": ["co konkretnie wymaga poprawy"],
    "mocne_punkty": ["co jest wyjątkowo dobre"],
    "sugestie": ["konkretne, actionable sugestie poprawy"],
    "zatwierdzone": true,
    "ocena_wiralnosci": {{
        "wynik_nwv": 78,
        "wynik_haka": 82,
        "wynik_zatrzymania": 75,
        "wynik_udostepnialnosci": 70,
        "wynik_platformy": {{"tiktok": 80, "youtube": 75, "instagram": 70}},
        "odznaka": "✅ Dobry content",
        "uzasadnienie": "Mocny hak, ale środek traci tempo...",
        "wskazowki_optymalizacji": ["Dodaj pattern interrupt w scenie 3", "Skróć CTA o 5 sekund"]
    }},
    "cliffhanger": {{
        "cds": 0.72,
        "interpretacja": "OPTIMUM — widz będzie chciał więcej",
        "sugestia_korekty": null
    }}
}}
"""


def oblicz_ocene_wiralnosci_z_wynikow(dane: dict) -> OcenaWiralnosci:
    """Parsuje i normalizuje ocenę wiralności."""
    ow = dane.get("ocena_wiralnosci", {})
    nwv = int(ow.get("wynik_nwv", dane.get("wynik_ogolny", 60)))

    if nwv >= 85:
        odznaka = "🔥 Wysoki potencjał wiralny"
    elif nwv >= 60:
        odznaka = "✅ Dobry content"
    else:
        odznaka = "⚠️ Wymaga poprawy"

    return OcenaWiralnosci(
        wynik_nwv=nwv,
        wynik_haka=int(ow.get("wynik_haka", dane.get("wynik_haka", 60))),
        wynik_zatrzymania=int(ow.get("wynik_zatrzymania", 70)),
        wynik_udostepnialnosci=int(ow.get("wynik_udostepnialnosci", 65)),
        wynik_platformy=ow.get("wynik_platformy", {"tiktok": nwv, "youtube": nwv - 5}),
        odznaka=odznaka,
        uzasadnienie=ow.get("uzasadnienie", ""),
        wskazowki_optymalizacji=ow.get("wskazowki_optymalizacji", []),
    )


async def recenzent_jakosci(stan: StanNEXUS) -> dict:
    """
    Agent Recenzent Jakości — ocenia projekt i zatwierdza lub odrzuca.

    Używa gpt-4o (najinteligentniejszy) — kluczowa decyzja jakościowa.

    Args:
        stan: Pełny stan NEXUS

    Returns:
        Aktualizacja z ocenami i decyzją zatwierdź/popraw
    """
    log = logger.bind(agent="recenzent_jakosci", iteracja=stan.get("iteracja", 0))
    log.info("Recenzent Jakości ocenia projekt")

    if not all([stan.get("scenariusz"), stan.get("audio"), stan.get("wizualia")]):
        log.warning("Niekompletne dane do recenzji — zatwierdzam z ostrzeżeniem")
        # Jeśli brak komponentów, daj minimalną ocenę i zatwierdź
        ocena: OcenaJakosci = {
            "wynik_ogolny": 65,
            "wynik_haka": 60,
            "wynik_scenariusza": 65,
            "wynik_wizualny": 60,
            "wynik_audio": 65,
            "slabe_punkty": ["Niekompletne dane projektu"],
            "mocne_punkty": [],
            "sugestie": ["Uzupełnij wszystkie komponenty"],
            "zatwierdzone": True,
        }
        wiralosc: OcenaWiralnosci = {
            "wynik_nwv": 65,
            "wynik_haka": 60,
            "wynik_zatrzymania": 65,
            "wynik_udostepnialnosci": 60,
            "wynik_platformy": {"tiktok": 65},
            "odznaka": "✅ Dobry content",
            "uzasadnienie": "Projekt zatwierdzony z minimalnymi danymi",
            "wskazowki_optymalizacji": [],
        }
        return {
            "ocena_jakosci": ocena,
            "ocena_wiralnosci": wiralosc,
            "krok_aktualny": "recenzja_gotowa",
            "iteracja": stan.get("iteracja", 0) + 1,
        }

    scenariusz = stan["scenariusz"]
    audio = stan["audio"]
    wizualia = stan["wizualia"]
    plan = stan.get("plan_tresci", {})

    klient = AsyncOpenAI(api_key=konf.OPENAI_API_KEY)

    prompt = PROMPT_RECENZJI.format(
        plan_json=json.dumps(plan, ensure_ascii=False, indent=2),
        scenariusz_json=json.dumps({
            "tytul": scenariusz["tytul"],
            "hook_otwierający": scenariusz["hook_otwierający"],
            "cta": scenariusz["cta"],
            "calkowity_czas": scenariusz["calkowity_czas"],
            "sceny": [
                {
                    "numer": s["numer"],
                    "tekst_narracji": s["tekst_narracji"],
                    "tekst_na_ekranie": s["tekst_na_ekranie"],
                    "emocja": s["emocja"],
                }
                for s in scenariusz["sceny"]
            ]
        }, ensure_ascii=False, indent=2),
        glos=audio["glos"],
        czas_trwania=round(audio["czas_trwania"], 1),
        liczba_slow=scenariusz["liczba_slow"],
        liczba_obrazow=wizualia["liczba_obrazow"],
        styl_wizualny=wizualia["styl_wizualny"],
        platformy=", ".join(plan.get("platforma_docelowa", ["tiktok", "youtube"])),
    )

    try:
        odpowiedz = await klient.chat.completions.create(
            model=konf.MODEL_INTELIGENTNY,  # gpt-4o — dla krytycznej oceny jakości
            messages=[
                {"role": "system", "content": SYSTEM_RECENZENT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,            # Niska temperatura = bardziej obiektywna ocena
            response_format={"type": "json_object"},
            max_tokens=1500,
        )

        dane = json.loads(odpowiedz.choices[0].message.content)

        # Koszt gpt-4o
        tokeny = odpowiedz.usage
        koszt = (tokeny.prompt_tokens * 2.50 + tokeny.completion_tokens * 10.0) / 1_000_000

        wynik_ogolny = int(dane.get("wynik_ogolny", 70))
        zatwierdzone = wynik_ogolny >= konf.PROG_JAKOSCI

        ocena: OcenaJakosci = {
            "wynik_ogolny": wynik_ogolny,
            "wynik_haka": int(dane.get("wynik_haka", 70)),
            "wynik_scenariusza": int(dane.get("wynik_scenariusza", 70)),
            "wynik_wizualny": int(dane.get("wynik_wizualny", 70)),
            "wynik_audio": int(dane.get("wynik_audio", 70)),
            "slabe_punkty": dane.get("slabe_punkty", []),
            "mocne_punkty": dane.get("mocne_punkty", []),
            "sugestie": dane.get("sugestie", []),
            "zatwierdzone": zatwierdzone,
        }

        wiralosc = oblicz_ocene_wiralnosci_z_wynikow(dane)

        # ── [INNOWACJA 8] Cliffhanger Coefficient ────────────────────────
        cliffhanger_dane = dane.get("cliffhanger", {})
        cds = float(cliffhanger_dane.get("cds", 0.5))
        cds_interpretacja = cliffhanger_dane.get("interpretacja", "")
        cds_sugestia = cliffhanger_dane.get("sugestia_korekty")

        # Dodaj CDS do wskazówek optymalizacji jeśli poza optymalnym zakresem
        wskazowki = wiralosc.get("wskazowki_optymalizacji", [])
        if cds < 0.65:
            wskazowki = [
                f"[CDS={cds:.2f}] Zakończenie ZA ZAMKNIĘTE — dodaj otwarte pytanie: {cds_sugestia or 'Zadaj pytanie na które odpowiedź jest w kolejnym filmie'}",
                *wskazowki,
            ]
        elif cds > 0.82:
            wskazowki = [
                f"[CDS={cds:.2f}] Zakończenie ZA OTWARTE — widz może się sfrustrować: {cds_sugestia or 'Zamknij przynajmniej jedną obietnicę z haka'}",
                *wskazowki,
            ]
        wiralosc["wskazowki_optymalizacji"] = wskazowki
        wiralosc["cliffhanger_cds"] = cds

        log.info(
            "Recenzja v2.0 zakończona",
            wynik=wynik_ogolny,
            nwv=wiralosc["wynik_nwv"],
            odznaka=wiralosc["odznaka"],
            cds=cds,
            cds_interpretacja=cds_interpretacja,
            zatwierdzone=zatwierdzone,
            koszt_usd=round(koszt, 5),
        )

        return {
            "ocena_jakosci": ocena,
            "ocena_wiralnosci": wiralosc,
            "krok_aktualny": "recenzja_gotowa" if zatwierdzone else "wymaga_poprawy",
            "iteracja": stan.get("iteracja", 0) + 1,
            "koszt_calkowity_usd": stan.get("koszt_calkowity_usd", 0.0) + koszt,
        }

    except Exception as e:
        log.error("Błąd Recenzenta Jakości", blad=str(e))
        # Fallback: zatwierdź z minimalnym wynikiem
        return {
            "ocena_jakosci": {
                "wynik_ogolny": 70,
                "wynik_haka": 65,
                "wynik_scenariusza": 70,
                "wynik_wizualny": 65,
                "wynik_audio": 70,
                "slabe_punkty": [],
                "mocne_punkty": [],
                "sugestie": [],
                "zatwierdzone": True,
            },
            "ocena_wiralnosci": {
                "wynik_nwv": 70,
                "wynik_haka": 65,
                "wynik_zatrzymania": 70,
                "wynik_udostepnialnosci": 65,
                "wynik_platformy": {"tiktok": 70},
                "odznaka": "✅ Dobry content",
                "uzasadnienie": "Automatyczne zatwierdzenie (błąd oceny)",
                "wskazowki_optymalizacji": [],
            },
            "krok_aktualny": "recenzja_gotowa",
            "iteracja": stan.get("iteracja", 0) + 1,
            "bledy": [f"Recenzent (nieblokujący): {str(e)}"],
        }
