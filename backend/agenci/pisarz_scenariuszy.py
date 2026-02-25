"""
NEXUS — Agent 2: Pisarz Scenariuszy v2.0
==========================================
Tworzy gotowy scenariusz produkcyjny z podziałem na sceny.
Model: gpt-4o-mini (koszt ~$0.002 na wideo)

Nowości v2.0:
- [INNOWACJA 4] Micro-Hook Bifurcation — A/B test hooków przed renderem
  Generuje 3 różne wersje pierwszej sceny (różne archetypy haków)
  Ocenia je heurystycznym NVS i wybiera najlepszy ZANIM zleci DALL-E
  Oszczędność: $0.04 gdy hook jest słaby (nie generujemy obrazu dla słabego haka)
  Koszt: +$0.001 (1 dodatkowe wywołanie GPT-4o-mini)
- [INNOWACJA 5] Deterministyczne Operatory Mutacji dla retry
  Poprzedni retry: temperature=0.7 + tekstowy feedback → może wygenerować to samo
  Nowy retry: każda próba = konkretny OPERATOR TRANSFORMACJI
  Próba 1: FLIP_PERSPECTIVE (1os→3os, pytanie→twierdzenie, ogólne→konkretne)
  Próba 2: ADD_SOCIAL_PROOF (wstaw statystykę + źródło + konkretną liczbę)
  Próba 3: CHANGE_HOOK_ARCHETYPE (zmień typ haka na przeciwny)
  Efekt: każdy retry jest GWARANTOWANIE RÓŻNY od poprzedniego
"""

import json
import structlog
from openai import AsyncOpenAI

from konfiguracja import konf
from agenci.schematy import StanNEXUS, ScenariuszWideo, ScenariuszScena
from analityka.silnik_wiralnosci import oblicz_nwv_heurystyczny

logger = structlog.get_logger(__name__)

# ====================================================================
# SYSTEM PROMPT
# ====================================================================

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

# ====================================================================
# [INNOWACJA 4] Micro-Hook Bifurcation
# ====================================================================

PROMPT_BIFURKACJI_HOOKOW = """
Brief: "{brief}"
Plan treści: {plan_json}
Czas trwania: {dlugosc}s

Wygeneruj 3 RÓŻNE wersje pierwszej sceny (0-3s) — każda używa INNEGO archetypu haka.

Wersja A — "luk_ciekawosci": pytanie, które musi być odpowiedziane
Wersja B — "szok_humor" lub "pattern_interrupt": coś nieoczekiwanego/zaskakującego
Wersja C — "dowod_spoleczny" lub "wartosc_pierwsza": liczba/statystyka lub natychmiastowa wartość

Dla każdej wersji stwórz kompletną scenę 1 scenariusza.

Odpowiedz WYŁĄCZNIE JSON:
{{
  "warianty": [
    {{
      "archetyp": "luk_ciekawosci",
      "opis_wizualny": "DALL-E prompt in English...",
      "tekst_narracji": "Polska narracja...",
      "tekst_na_ekranie": "Krótki tekst",
      "emocja": "ciekawość",
      "tempo": "szybkie",
      "sila_haka_opis": "Dlaczego ten hak jest dobry (1 zdanie)"
    }},
    {{
      "archetyp": "pattern_interrupt",
      ...
    }},
    {{
      "archetyp": "dowod_spoleczny",
      ...
    }}
  ]
}}"""

# ====================================================================
# [INNOWACJA 5] Deterministyczne Operatory Mutacji
# ====================================================================

OPERATORY_MUTACJI = {
    1: {
        "nazwa": "FLIP_PERSPECTIVE",
        "opis": """OPERATOR MUTACJI: FLIP_PERSPECTIVE
Transformuj DOSŁOWNIE:
- Jeśli narracja jest w 1. osobie ("Ja", "mnie") → zmień na 2. osobę ("Ty", "ciebie")
- Jeśli hak jest pytaniem → zmień na szokujące twierdzenie
- Jeśli perspektywa jest ogólna → zmień na ultra-konkretną (imię, miasto, liczba)
- Przykład przed: "Jak zwiększyć energię rano?"
- Przykład po: "95% ludzi traci 3 godziny produktywności każdego ranka przez 1 błąd."
Zastosuj tę transformację do CAŁEGO scenariusza.""",
    },
    2: {
        "nazwa": "ADD_SOCIAL_PROOF",
        "opis": """OPERATOR MUTACJI: ADD_SOCIAL_PROOF
Wstaw KONKRETNĄ statystykę lub dowód społeczny do każdej sceny:
- Użyj PRAWDZIWYCH lub WIARYGODNYCH liczb (np. "94% użytkowników TikToka przewija bez dźwięku")
- Dodaj źródło lub autorytety (np. "Badania MIT pokazują...", "Elon Musk powiedział...")
- W hakie: liczba musi być ZASKAKUJĄCA (np. "98% ludzi myli się w tym...")
- Każda kluczowa scena powinna mieć co najmniej jedną statystykę
Przepisz scenariusz uwzględniając te dowody społeczne.""",
    },
    3: {
        "nazwa": "CHANGE_HOOK_ARCHETYPE",
        "opis": """OPERATOR MUTACJI: CHANGE_HOOK_ARCHETYPE
Obecny hak jest słaby. Zmień CAŁY typ haka na nowy archetyp:
- Jeśli poprzedni był "luk_ciekawosci" → użyj "szok_humor"
- Jeśli poprzedni był "szok_humor" → użyj "intryga_wizualna"
- Jeśli poprzedni był "wartosc_pierwsza" → użyj "pattern_interrupt"
Nowy hak musi być RADYKALNIE RÓŻNY wizualnie i tekstowo.
Pierwsza scena musi być kompletnie inna — inny obraz, inne pierwsze zdanie.
Przepisz scenariusz od nowa z nowym archetyp hakiem.""",
    },
}


def wybierz_operator_mutacji(iteracja: int) -> dict:
    """Zwraca deterministyczny operator mutacji dla danej iteracji retry."""
    return OPERATORY_MUTACJI.get(iteracja, OPERATORY_MUTACJI[1])


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


# ====================================================================
# GŁÓWNY AGENT
# ====================================================================

async def _wybierz_najlepszy_hook(
    klient: AsyncOpenAI,
    plan: dict,
    brief: str,
    dlugosc: int,
) -> dict | None:
    """
    [INNOWACJA 4] Generuje 3 warianty haka i wybiera najlepszy.

    Koszt: ~$0.001 (1 wywołanie GPT-4o-mini, ~300 tokenów)
    Wartość: zapobiega generowaniu $0.12 DALL-E dla słabego haka.

    Zwraca słownik z wybraną sceną 1 lub None jeśli błąd.
    """
    prompt = PROMPT_BIFURKACJI_HOOKOW.format(
        brief=brief[:200],
        plan_json=json.dumps(plan, ensure_ascii=False, indent=2)[:800],
        dlugosc=dlugosc,
    )

    try:
        resp = await klient.chat.completions.create(
            model=konf.MODEL_EKONOMICZNY,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            response_format={"type": "json_object"},
            max_tokens=1200,
        )

        dane = json.loads(resp.choices[0].message.content)
        warianty = dane.get("warianty", [])

        if not warianty:
            return None

        # Ocena heurystyczna każdego wariantu
        najlepszy = None
        najlepszy_nvs = -1

        for w in warianty:
            # Symuluj plan z parametrami wariantu
            plan_wariant = {
                **plan,
                "typ_haka": w.get("archetyp", plan.get("typ_haka", "")),
                "hak_tekstowy": w.get("tekst_narracji", ""),
                "hak_wizualny": w.get("opis_wizualny", ""),
            }
            nvs = oblicz_nwv_heurystyczny(plan_wariant)
            if nvs > najlepszy_nvs:
                najlepszy_nvs = nvs
                najlepszy = w

        if najlepszy:
            logger.info(
                "Micro-hook bifurcation — wybrano wariant",
                archetyp=najlepszy.get("archetyp"),
                nvs_heurystyczny=najlepszy_nvs,
                warianty_ocenione=len(warianty),
            )

        return najlepszy

    except Exception as e:
        logger.warning("Micro-hook bifurcation niedostępna", blad=str(e))
        return None


async def pisarz_scenariuszy(stan: StanNEXUS) -> dict:
    """
    Agent Pisarz Scenariuszy v2.0 — tworzy produkcyjny scenariusz.

    [v2.0 vs v1.0]:
    - Micro-Hook Bifurcation: 3 haki → wybierz najlepszy PRZED DALL-E
    - Deterministyczne mutacje: każdy retry = konkretna transformacja
    """
    log = logger.bind(
        agent="pisarz_scenariuszy_v2",
        iteracja=stan.get("iteracja", 0),
    )

    if not stan.get("plan_tresci"):
        return {
            "bledy": ["Pisarz Scenariuszy: brak planu treści"],
            "krok_aktualny": "blad_pisarza",
        }

    plan = stan["plan_tresci"]
    iteracja = stan.get("iteracja", 0)
    liczba_scen = oblicz_liczbe_scen(plan["dlugosc_sekund"])
    log.info("Pisarz Scenariuszy v2.0 tworzy scenariusz", sceny=liczba_scen, czas=plan["dlugosc_sekund"])

    klient = AsyncOpenAI(api_key=konf.OPENAI_API_KEY)

    # ── Kontekst retry ─────────────────────────────────────────────
    kontekst_poprawki = ""
    if iteracja > 0 and stan.get("ocena_jakosci"):
        ocena = stan["ocena_jakosci"]
        operator = wybierz_operator_mutacji(iteracja)

        # [INNOWACJA 5] Deterministyczny operator zamiast losowego retry
        kontekst_poprawki = f"""

FEEDBACK Z RECENZJI:
Słabe punkty: {ocena.get('slabe_punkty', [])}
Sugestie: {ocena.get('sugestie', [])}
NVS: {stan.get('ocena_wiralnosci', {}).get('wynik_nwv', '?')}

{operator['opis']}

WAŻNE: To jest iteracja {iteracja}. Zastosuj powyższy operator DOSŁOWNIE i BEZWZGLĘDNIE.
Poprzedni scenariusz był niewystarczający — ten musi być RADYKALNIE INNY w podanym kierunku."""

        log.info(
            "Retry z deterministycznym operatorem",
            operator=operator["nazwa"],
            iteracja=iteracja,
        )

    prompt = PROMPT_SCENARIUSZA.format(
        plan_json=json.dumps(plan, ensure_ascii=False, indent=2),
        brief=stan["brief"],
        liczba_scen=liczba_scen,
        dlugosc=plan["dlugosc_sekund"],
    ) + kontekst_poprawki

    try:
        # ── [INNOWACJA 4] Micro-Hook Bifurcation (tylko pierwsza próba) ─
        najlepszy_hook = None
        koszt_hook = 0.0
        if iteracja == 0:
            najlepszy_hook = await _wybierz_najlepszy_hook(
                klient, plan, stan["brief"], plan["dlugosc_sekund"]
            )
            if najlepszy_hook:
                # Wstrzyknij wybrany hook do promptu
                prompt += f"""

UWAGA: Użyj tej KONKRETNEJ pierwszej sceny (wygrano A/B test haków):
Pierwsza scena MUSI być dokładnie:
- opis_wizualny: "{najlepszy_hook.get('opis_wizualny', '')}"
- tekst_narracji: "{najlepszy_hook.get('tekst_narracji', '')}"
- tekst_na_ekranie: "{najlepszy_hook.get('tekst_na_ekranie', '')}"
- emocja: "{najlepszy_hook.get('emocja', '')}"
- tempo: "{najlepszy_hook.get('tempo', '')}"
Resztę scen wygeneruj normalnie."""
                koszt_hook = 0.001  # Szacunek kosztu bifurcation

        odpowiedz = await klient.chat.completions.create(
            model=konf.MODEL_EKONOMICZNY,
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

        tokeny = odpowiedz.usage
        koszt = (tokeny.prompt_tokens * 0.15 + tokeny.completion_tokens * 0.60) / 1_000_000
        koszt += koszt_hook

        log.info(
            "Scenariusz v2.0 gotowy",
            sceny=len(sceny),
            czas=calkowity_czas,
            hook_bifurkacja=bool(najlepszy_hook),
            operator_mutacji=wybierz_operator_mutacji(iteracja)["nazwa"] if iteracja > 0 else "brak",
            koszt_usd=round(koszt, 5),
        )

        return {
            "scenariusz": scenariusz,
            "krok_aktualny": "scenariusz_gotowy",
            "koszt_calkowity_usd": stan.get("koszt_calkowity_usd", 0.0) + koszt,
        }

    except Exception as e:
        log.error("Błąd Pisarza Scenariuszy v2.0", blad=str(e))
        return {
            "bledy": [f"Pisarz Scenariuszy: {str(e)}"],
            "krok_aktualny": "blad_pisarza",
        }
