"""
ViraLoop — Agent: Historyk Serii (Series Story Historian)
==========================================================
Masterowy agent odpowiedzialny za projektowanie wieloodcinkowych narracji.

Rola:
- Analizuje temat i projektuje pełen łuk narracyjny serii
- Tworzy plan wszystkich odcinków z cliffhangerami
- Zapewnia spójność wizualną i narracyjną między odcinkami
- Optymalizuje kolejność pod kątem uzależnienia widza

Model: GPT-4o (złożone planowanie narracyjne wymaga najlepszego modelu)
"""

import uuid
import asyncio
import structlog
from datetime import datetime
from openai import AsyncOpenAI

from konfiguracja import konf
from agenci.schematy import SeriaNarracyjna, OdcinekSerii, StanSerii

logger = structlog.get_logger(__name__)


PROMPT_PLANOWANIA_SERII = """Jesteś mistrzowskim twórcą seriali dokumentalnych shortsy, który tworzy uzależniające serie na YouTube Shorts, TikTok i Instagram Reels.

Twoje zadanie: Zaprojektuj KOMPLETNĄ SERIĘ {liczba_odcinkow} odcinków na temat: "{temat}"

Gatunek docelowy: {gatunek}
Styl wizualny: {styl_wizualny}
Długość odcinka: {dlugosc_s} sekund
Platformy: {platformy}

ZASADY PROJEKTOWANIA SERII:
1. CLIFFHANGER: każdy odcinek MUSI kończyć się nierozwiązaną tajemnicą lub dramatycznym zwrotem
2. ŁUK NARRACYJNY: cała seria buduje ku finałowemu objawieniu
3. SPÓJNOŚĆ: ta sama estetyka, ten sam ton, powiązane postacie/miejsca
4. HOOK 3 sekundy: każdy odcinek zaczyna się od pytania lub szokującego faktu
5. PROGRESJA: każdy odcinek musi dawać wartość, ale zostawiać widza z pytaniem

FORMATY SKUTECZNYCH SERII:
- "3 fakty które ZMIENIĄ twoje spojrzenie na..." (każdy odcinek = nowy fakt)
- "Jak X doprowadziło do Y?" (odcinki = kroki do kulminacji)
- "Kto stoi za..." (odcinki = odkrywanie kolejnej warstwy)
- "Dzień kiedy..." (odcinki = różne perspektywy tego samego zdarzenia)

Odpowiedz WYŁĄCZNIE w formacie JSON:
{{
  "tytul_serii": "Chwytliwy tytuł całej serii",
  "opis_serii": "2-3 zdania opisujące o czym jest seria",
  "gatunek": "historyczny|naukowy|kryminalna|biznesowy|psychologiczny|geopolityczny",
  "luk_narracyjny": ["Motyw 1 (odcinek 1-2)", "Motyw 2 (odcinek 3-4)", "Kulminacja (ostatni)"],
  "odcinki": [
    {{
      "numer": 1,
      "tytul": "Tytuł odcinka 1 — chwytliwy, zaczynający od cyfry lub pytania",
      "streszczenie": "Co będzie pokazane w tym odcinku (2-3 zdania)",
      "hook_otwierajacy": "Pierwsze zdanie które zahookuje widza w 3 sekundy",
      "kluczowe_fakty": ["fakt 1", "fakt 2", "fakt 3"],
      "haczyk_konca": "Cliffhanger kończący odcinek — pozostawia pytanie bez odpowiedzi",
      "brief_dla_ai": "Szczegółowy brief dla pipeline'u AI do wygenerowania wideo"
    }}
  ]
}}
"""

GATUNKI_AUTO = {
    "histor": "historyczny",
    "war": "historyczny",
    "imper": "historyczny",
    "cywiliz": "historyczny",
    "nauk": "naukowy",
    "ewolucj": "naukowy",
    "fizyk": "naukowy",
    "krymin": "kryminalna",
    "morder": "kryminalna",
    "zbrodnia": "kryminalna",
    "biznes": "biznesowy",
    "fortun": "biznesowy",
    "startup": "biznesowy",
    "pieniadz": "biznesowy",
    "psych": "psychologiczny",
    "kult": "psychologiczny",
    "manipul": "psychologiczny",
}


def wykryj_gatunek(temat: str) -> str:
    """Automatycznie wykrywa gatunek serii na podstawie tematu."""
    temat_lower = temat.lower()
    for klucz, gatunek in GATUNKI_AUTO.items():
        if klucz in temat_lower:
            return gatunek
    return "historyczny"  # domyślny


async def zaplanuj_serie(stan: StanSerii) -> dict:
    """
    Agent Historyk Serii — planuje kompletną serię odcinków.

    Wejście: temat, liczba odcinków, parametry produkcji
    Wyjście: pełny plan serii z cliffhangerami dla każdego odcinka
    """
    log = logger.bind(agent="historyk_serii")
    log.info("Historyk Serii planuje serię", temat=stan["temat"][:60])

    klient = AsyncOpenAI(api_key=konf.OPENAI_API_KEY)

    temat = stan["temat"]
    liczba = stan["liczba_odcinkow"]
    styl = stan.get("styl_wizualny", "kinowy")
    platformy = ", ".join(stan.get("platforma", ["tiktok", "youtube"]))
    dlugosc_s = stan.get("dlugosc_odcinka_sekund", 60)

    gatunek = wykryj_gatunek(temat)

    prompt = PROMPT_PLANOWANIA_SERII.format(
        liczba_odcinkow=liczba,
        temat=temat,
        gatunek=gatunek,
        styl_wizualny=styl,
        dlugosc_s=dlugosc_s,
        platformy=platformy,
    )

    try:
        odpowiedz = await klient.chat.completions.create(
            model=konf.MODEL_INTELIGENTNY,  # GPT-4o — złożone planowanie narracyjne
            messages=[
                {
                    "role": "system",
                    "content": "Jesteś ekspertem od tworzenia wirusowych serii wideo na social media. Zawsze odpowiadasz w formacie JSON."
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.85,  # Wyższa kreatywność
            max_tokens=4000,
        )

        import json
        dane = json.loads(odpowiedz.choices[0].message.content)

    except Exception as e:
        log.error("Błąd planowania serii", blad=str(e))
        return {
            "bledy": [f"Historyk Serii: {str(e)}"],
            "seria": None,
        }

    # Buduj schemat serii
    seria_id = f"ser_{uuid.uuid4().hex[:8]}"

    odcinki_zaplanowane: list[OdcinekSerii] = []
    for od_dane in dane.get("odcinki", []):
        odcinek: OdcinekSerii = {
            "numer": od_dane.get("numer", 1),
            "sesja_id": f"ep_{seria_id}_{od_dane.get('numer', 1):02d}",
            "tytul": od_dane.get("tytul", f"Odcinek {od_dane.get('numer', 1)}"),
            "streszczenie": od_dane.get("streszczenie", ""),
            "haczyk_konca": od_dane.get("haczyk_konca", ""),
            "status": "oczekuje",
            "nwv": 0,
            "koszt_usd": 0.0,
            "czas_generacji_s": 0.0,
            "wideo": None,
            "ocena_wiralnosci": None,
        }
        odcinki_zaplanowane.append(odcinek)

    seria: SeriaNarracyjna = {
        "seria_id": seria_id,
        "tytul_serii": dane.get("tytul_serii", temat[:60]),
        "temat": temat,
        "gatunek": dane.get("gatunek", gatunek),
        "opis_serii": dane.get("opis_serii", ""),
        "platforma": stan.get("platforma", ["tiktok", "youtube"]),
        "styl_wizualny": styl,
        "glos": stan.get("glos", "nova"),
        "dlugosc_odcinka_s": dlugosc_s,
        "liczba_odcinkow": len(odcinki_zaplanowane),
        "luk_narracyjny": dane.get("luk_narracyjny", []),
        "odcinki": odcinki_zaplanowane,
        "status": "planowanie",
        "data_utworzenia": datetime.now().isoformat(),
        "calkowity_koszt_usd": 0.0,
    }

    log.info(
        "Seria zaplanowana",
        seria_id=seria_id,
        tytul=seria["tytul_serii"],
        odcinki=len(odcinki_zaplanowane),
    )

    return {"seria": seria}


async def generuj_brief_kontynuacji(
    seria: SeriaNarracyjna,
    numer_odcinka: int,
) -> str:
    """
    Generuje brief dla kolejnego odcinka serii (kontynuacja).
    Uwzględnia poprzednie odcinki jako kontekst.
    """
    log = logger.bind(agent="historyk_serii", akcja="kontynuacja")

    poprzednie = [od for od in seria["odcinki"] if od["numer"] < numer_odcinka and od["status"] == "gotowy"]
    nastepny_plan = next((od for od in seria["odcinki"] if od["numer"] == numer_odcinka), None)

    if not nastepny_plan:
        # Generuj nowy odcinek jeśli nie ma planu
        return f"Kontynuacja serii '{seria['tytul_serii']}': odcinek {numer_odcinka}"

    kontekst = ""
    if poprzednie:
        ostatni = poprzednie[-1]
        kontekst = f"""
Poprzedni odcinek ({ostatni['numer']}): "{ostatni['tytul']}"
Cliffhanger z poprzedniego: {ostatni['haczyk_konca']}
        """

    brief = f"""
Seria: {seria['tytul_serii']} (odcinek {numer_odcinka}/{seria['liczba_odcinkow']})
Gatunek: {seria['gatunek']}
{kontekst}
Ten odcinek:
Tytuł: {nastepny_plan['tytul']}
Streszczenie: {nastepny_plan['streszczenie']}
Cliffhanger na końcu: {nastepny_plan['haczyk_konca']}
Styl wizualny: {seria['styl_wizualny']}
Długość: {seria['dlugosc_odcinka_s']} sekund
    """.strip()

    log.info("Brief kontynuacji wygenerowany", numer=numer_odcinka)
    return brief
