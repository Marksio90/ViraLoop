"""
NEXUS — Agent 4: Producent Wizualny v2.0
==========================================
Generuje obrazy dla każdej sceny przy użyciu DALL-E 3.
Model: dall-e-3 (koszt $0.04/obraz = ~$0.12 na wideo za 3 obrazy)

Nowości v2.0:
- [INNOWACJA 3] Semantyczny wybór scen zamiast pozycyjnego
  Poprzednia logika: zawsze scena 1, 2, środkowa, n-1, n (hardcoded pozycje)
  Nowa logika: GPT-4o-mini ocenia każdą scenę pod kątem "wizualnej wagi narracyjnej"
  i generuje obrazy dla scen o NAJWYŻSZEJ sile wizualnej — nie tylko pozycyjnych.
  Efekt: scena 3 (kulminacja) dostaje obraz zamiast sceny 4 (rozbicie).
  Koszt: +$0.0003 (1 wywołanie GPT-4o-mini)
- [INNOWACJA 7] Guard spójności wizualnej przez embeddingi
  Embed opisy_wizualne wszystkich wygenerowanych scen przez text-embedding-3-small
  Wykryj "outliery" — sceny z cosine_similarity < 0.45 względem sąsiadów
  Automatycznie regeneruj outlierowe sceny z ujednoliconym stylem w prompcie
  Efekt: postać/styl nie "skacze" między scenami. Spójna narracja wizualna.
  Koszt: +$0.0001 (embeddingi) + ewentualne $0.04 per regeneracja
"""

import os
import asyncio
import json
import structlog
import httpx
from pathlib import Path
from openai import AsyncOpenAI

from konfiguracja import konf
from agenci.schematy import StanNEXUS, WizualiaWideo, ObrazSceny

logger = structlog.get_logger(__name__)

# ====================================================================
# STAŁE I MAPOWANIA
# ====================================================================

SZABLON_PROMPT_WIZUALY = """
{opis_sceny},
Style: {styl_wizualny},
Mood: {emocja},
Ultra-HD quality, cinematic lighting, professional photography,
vertical format 9:16, vibrant colors, social media optimized,
no text, no watermarks, photorealistic
"""

STYL_DO_DALL_E = {
    "nowoczesny": "modern minimalist, clean lines, bright colors",
    "kinowy": "cinematic, dramatic lighting, film noir",
    "estetyczny": "aesthetic, warm tones, soft light, instagram style",
    "dynamiczny": "dynamic, energetic, bold colors, action-packed",
    "profesjonalny": "professional, corporate, clean, polished",
    "artystyczny": "artistic, creative, unique composition",
}

EMOCJA_DO_WIZUALU = {
    "inspiracja": "uplifting, bright, hopeful atmosphere",
    "zaskoczenie": "unexpected angle, dramatic reveal",
    "napięcie": "suspenseful, moody lighting, tension",
    "radość": "joyful, colorful, energetic",
    "spokój": "calm, peaceful, serene",
    "ciekawość": "intriguing, mysterious, question-raising",
    "dramatyczny": "dramatic, high contrast, cinematic tension",
    "energia": "high energy, dynamic, explosive composition",
}

# Próg spójności wizualnej — poniżej: scena jest "outlierem" stylistycznym
PROG_SPOJNOSCI_WIZUALNEJ = 0.50


# ====================================================================
# OPTYMALIZACJA PROMPTÓW
# ====================================================================

def zoptymalizuj_prompt(
    opis_sceny: str,
    styl_wizualny: str,
    emocja: str,
    marka: dict,
    styl_referencyjny: str = "",
) -> str:
    """
    Tworzy zoptymalizowany prompt dla DALL-E 3.

    styl_referencyjny: opcjonalny prefix stylistyczny dla spójności wizualnej
    (używany przez INNOWACJĘ 7 przy regeneracji outlierów).
    """
    styl_dall_e = STYL_DO_DALL_E.get(
        styl_wizualny.split(",")[0].strip().lower(),
        "professional, high quality, vibrant"
    )
    emocja_wizualna = EMOCJA_DO_WIZUALU.get(emocja.lower(), "engaging, dynamic")

    kolory_marki = marka.get("kolory", "")
    prefix_marki = f"Brand colors: {kolory_marki}. " if kolory_marki else ""

    # Styl referencyjny dla spójności (dodawany gdy regenerujemy outlierów)
    prefix_spojnosci = f"{styl_referencyjny}. " if styl_referencyjny else ""

    prompt = (
        f"{prefix_spojnosci}{prefix_marki}{opis_sceny}. "
        f"{styl_dall_e}, {emocja_wizualna}, "
        f"ultra-HD quality, cinematic composition, professional photography, "
        f"vertical 9:16 format, no text overlays, no watermarks, photorealistic render"
    )

    # DALL-E 3 limit 4000 znaków
    return prompt[:4000]


# ====================================================================
# [INNOWACJA 3] Semantyczny wybór scen
# ====================================================================

async def ocen_waznosc_scen_semantycznie(
    klient: AsyncOpenAI,
    sceny: list[dict],
    maks: int,
    brief: str = "",
) -> list[int]:
    """
    Ocenia każdą scenę pod kątem wizualnej wagi narracyjnej.

    [INNOWACJA 3] Zastępuje hardcoded pozycyjny wybór (scena 1, 2, środkowa, n-1, n).

    GPT-4o-mini ocenia każdą scenę na skali 0-10:
    - Wizualna unikalność (jak bardzo różni się od sąsiadów)
    - Narracyjna waga (kulminacja, zwrot akcji, payoff obietnicy z haka)
    - Emocjonalna intensywność (szczyt emocji w łuku dramatycznym)

    Generuje obrazy dla scen o NAJWYŻSZEJ wadze, nie pozycyjnych.
    Koszt: ~$0.0003 na wywołanie (GPT-4o-mini, ~200 tokenów)
    """
    if len(sceny) <= maks:
        return list(range(len(sceny)))

    prompt = f"""Masz {len(sceny)} scen wideo. Brief: "{brief[:100]}"

Sceny:
{json.dumps([{
    "numer": i + 1,
    "opis_wizualny": s.get("opis_wizualny", "")[:100],
    "tekst_narracji": s.get("tekst_narracji", "")[:80],
    "emocja": s.get("emocja", ""),
    "tempo": s.get("tempo", ""),
} for i, s in enumerate(sceny)], ensure_ascii=False, indent=2)}

Wybierz dokładnie {maks} scen o NAJWYŻSZEJ wizualnej i narracyjnej wadze.
Kryteria (ważność malejąca):
1. Kulminacja / payoff obietnicy z haka (najważniejsza!)
2. Pattern interrupt / zwrot narracyjny
3. Emocjonalny szczyt łuku dramatycznego
4. Wizualna unikalność (scena wyglądająca inaczej niż poprzednia)

Zawsze uwzględnij scenę 1 (hak wizualny) i ostatnią scenę.

Odpowiedz TYLKO JSON:
{{"indeksy_scen": [0, 2, 4]}}
(indeksy 0-based, dokładnie {maks} wartości)"""

    try:
        resp = await klient.chat.completions.create(
            model=konf.MODEL_EKONOMICZNY,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
            max_tokens=100,
        )
        dane = json.loads(resp.choices[0].message.content)
        indeksy = dane.get("indeksy_scen", [])

        # Walidacja: muszą być prawidłowe indeksy
        indeksy = [i for i in indeksy if 0 <= i < len(sceny)]

        # Zawsze uwzględnij scenę 0 i ostatnią
        if 0 not in indeksy:
            indeksy.insert(0, 0)
        if len(sceny) - 1 not in indeksy:
            indeksy.append(len(sceny) - 1)

        indeksy = sorted(set(indeksy))[:maks]

        if len(indeksy) < maks:
            # Uzupełnij brakujące pozycje
            wszystkie = list(range(len(sceny)))
            for idx in wszystkie:
                if idx not in indeksy and len(indeksy) < maks:
                    indeksy.append(idx)
            indeksy = sorted(set(indeksy))[:maks]

        logger.info("Semantyczny wybór scen", indeksy=indeksy, maks=maks)
        return indeksy

    except Exception as e:
        logger.warning("Fallback do pozycyjnego wyboru scen", blad=str(e))
        # Fallback: pozycyjny wybór (stara logika)
        indeksy = list(range(min(2, len(sceny))))
        srodek = len(sceny) // 2
        if srodek not in indeksy:
            indeksy.append(srodek)
        for i in range(max(0, len(sceny) - 2), len(sceny)):
            if i not in indeksy:
                indeksy.append(i)
        return sorted(set(indeksy))[:maks]


# ====================================================================
# [INNOWACJA 7] Guard spójności wizualnej przez embeddingi
# ====================================================================

def _podobienstwo_cosinusowe(vec1: list[float], vec2: list[float]) -> float:
    """Szybkie cosine similarity."""
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = sum(a * a for a in vec1) ** 0.5
    mag2 = sum(b * b for b in vec2) ** 0.5
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


async def sprawdz_spojnosc_wizualna(
    klient: AsyncOpenAI,
    sceny_z_obrazami: list[dict],
) -> list[int]:
    """
    Wykrywa wizualnie niespójne sceny ("outliery") przez embeddingi opisów.

    [INNOWACJA 7] Semantic Visual Coherence Guard.

    Problem: DALL-E generuje każdy obraz niezależnie. Postać z sceny 1 może
    wyglądać inaczej w scenie 3. Tło może "skoczyć" ze studia do lasu.

    Metoda:
    1. Embed opis_wizualny każdej sceny przez text-embedding-3-small
    2. Oblicz cosine_similarity między kolejnymi scenami
    3. Scena z podobieństwem < PROG_SPOJNOSCI_WIZUALNEJ = outlier
    4. Zwróć indeksy outlierów do regeneracji

    Koszt: text-embedding-3-small = $0.020/1M tokenów ≈ $0.0001 per wideo
    """
    if len(sceny_z_obrazami) < 2:
        return []

    opisy = [s.get("opis_wizualny", "") for s in sceny_z_obrazami]

    try:
        resp = await klient.embeddings.create(
            model=konf.MODEL_EMBEDDINGI,
            input=opisy,
        )
        embeddingi = [e.embedding for e in resp.data]

        outliery = []
        for i in range(1, len(embeddingi)):
            sim = _podobienstwo_cosinusowe(embeddingi[i - 1], embeddingi[i])
            if sim < PROG_SPOJNOSCI_WIZUALNEJ:
                outliery.append(i)
                logger.info(
                    "Wykryto niespójność wizualną",
                    scena=i + 1,
                    poprzednia=i,
                    podobienstwo=round(sim, 3),
                )

        return outliery

    except Exception as e:
        logger.debug("Guard spójności wizualnej niedostępny", blad=str(e))
        return []


def ekstrakcja_stylu_dominujacego(sceny: list[dict]) -> str:
    """
    Wyciąga dominujący styl wizualny ze zbioru scen do spójnej regeneracji.
    Używany jako prefix w prompcie DALL-E dla outlierów.
    """
    opisy = [s.get("opis_wizualny", "") for s in sceny if s.get("opis_wizualny")]
    if not opisy:
        return ""
    # Użyj pierwszego opisu jako "anchora" stylu
    # (scena 1 = hak = najważniejszy styl wizualny)
    return f"Maintain visual style consistency with: {opisy[0][:100]}"


# ====================================================================
# GENERACJA OBRAZÓW
# ====================================================================

async def pobierz_i_zapisz_obraz(
    url: str,
    sciezka: Path,
    timeout: int = 60
) -> bool:
    """Pobiera obraz z URL i zapisuje lokalnie."""
    async with httpx.AsyncClient(timeout=timeout) as klient_http:
        odpowiedz = await klient_http.get(url)
        odpowiedz.raise_for_status()
        sciezka.parent.mkdir(parents=True, exist_ok=True)
        sciezka.write_bytes(odpowiedz.content)
    return True


async def generuj_obraz_sceny(
    klient: AsyncOpenAI,
    prompt: str,
    sciezka: Path,
    numer_sceny: int,
) -> tuple[bool, str]:
    """
    Generuje obraz dla jednej sceny.

    Returns:
        (sukces, ścieżka_pliku)
    """
    try:
        odpowiedz = await klient.images.generate(
            model=konf.MODEL_OBRAZY,
            prompt=prompt,
            size="1024x1792",
            quality="standard",
            n=1,
            style="vivid",
        )

        url_obrazu = odpowiedz.data[0].url
        await pobierz_i_zapisz_obraz(url_obrazu, sciezka)

        return True, str(sciezka)

    except Exception as e:
        logger.error("Błąd generacji obrazu", numer_sceny=numer_sceny, blad=str(e))
        return False, ""


# ====================================================================
# GŁÓWNY AGENT
# ====================================================================

async def producent_wizualny(stan: StanNEXUS) -> dict:
    """
    Agent Producent Wizualny v2.0 — generuje obrazy dla scen.

    [v2.0 vs v1.0]:
    - Semantyczny wybór scen (GPT-4o-mini ocenia wagę narracyjną)
    - Guard spójności wizualnej (wykrywa i regeneruje outlierowe sceny)
    - Zachowuje styl referencyjny pierwszej sceny dla spójności

    Strategia kosztowa:
    - Max 5 obrazów na wideo (konf.MAKS_OBRAZOW_NA_SCENA)
    - +1 sprawdzenie spójności przez embeddingi (~$0.0001)
    - Ewentualna regeneracja outlierów (+$0.04 per scena)
    """
    log = logger.bind(agent="producent_wizualny_v2")

    if not stan.get("scenariusz"):
        return {
            "bledy": ["Producent Wizualny: brak scenariusza"],
            "krok_aktualny": "blad_producenta",
        }

    scenariusz = stan["scenariusz"]
    plan = stan.get("plan_tresci", {})
    marka = stan.get("marka", {})

    wszystkie_sceny = scenariusz["sceny"]
    maks = konf.MAKS_OBRAZOW_NA_SCENA

    klient = AsyncOpenAI(api_key=konf.OPENAI_API_KEY)

    sesja_id = stan.get("metadane", {}).get("sesja_id", "domyslna")
    katalog_obrazy = Path(konf.SCIEZKA_TYMCZASOWA) / sesja_id / "obrazy"
    katalog_obrazy.mkdir(parents=True, exist_ok=True)

    styl_wizualny = plan.get("styl_wizualny", "nowoczesny")
    brief = stan.get("brief", "")

    # ── [INNOWACJA 3] Semantyczny wybór scen ──────────────────────
    if len(wszystkie_sceny) <= maks:
        sceny_do_generacji = wszystkie_sceny
    else:
        indeksy = await ocen_waznosc_scen_semantycznie(
            klient, wszystkie_sceny, maks, brief
        )
        sceny_do_generacji = [wszystkie_sceny[i] for i in indeksy]

    log.info("Producent Wizualny v2.0 generuje obrazy", liczba=len(sceny_do_generacji))

    obrazy: list[ObrazSceny] = []
    koszt_obrazy = 0.0

    # Generuj obrazy równolegle (max 3 naraz — limit API)
    for i in range(0, len(sceny_do_generacji), 3):
        partia = sceny_do_generacji[i:i + 3]
        zadania = []

        for scena in partia:
            prompt = zoptymalizuj_prompt(
                opis_sceny=scena["opis_wizualny"],
                styl_wizualny=styl_wizualny,
                emocja=scena["emocja"],
                marka=marka,
            )
            sciezka = katalog_obrazy / f"scena_{scena['numer']:02d}.png"
            zadanie = generuj_obraz_sceny(klient, prompt, sciezka, scena["numer"])
            zadania.append((scena, prompt, zadanie))

        wyniki = await asyncio.gather(*[z[2] for z in zadania], return_exceptions=True)

        for (scena, prompt, _), wynik in zip(zadania, wyniki):
            if isinstance(wynik, Exception):
                log.error("Błąd obrazu sceny", numer=scena["numer"], blad=str(wynik))
                continue

            sukces, sciezka_pliku = wynik
            if sukces:
                obrazy.append(ObrazSceny(
                    numer_sceny=scena["numer"],
                    sciezka_pliku=sciezka_pliku,
                    prompt_uzyty=prompt,
                    rozdzielczosc="1024x1792",
                    format="png",
                ))
                koszt_obrazy += 0.040

    # ── [INNOWACJA 7] Guard spójności wizualnej ────────────────────
    if len(sceny_do_generacji) >= 2:
        outliery = await sprawdz_spojnosc_wizualna(klient, sceny_do_generacji)

        if outliery:
            log.info("Regeneruję niespójne sceny", outliery=outliery)
            styl_ref = ekstrakcja_stylu_dominujacego(sceny_do_generacji)

            for idx_outliera in outliery:
                if idx_outliera >= len(sceny_do_generacji):
                    continue

                scena = sceny_do_generacji[idx_outliera]
                prompt_spojny = zoptymalizuj_prompt(
                    opis_sceny=scena["opis_wizualny"],
                    styl_wizualny=styl_wizualny,
                    emocja=scena["emocja"],
                    marka=marka,
                    styl_referencyjny=styl_ref,
                )

                sciezka = katalog_obrazy / f"scena_{scena['numer']:02d}_spojny.png"
                sukces, sciezka_pliku = await generuj_obraz_sceny(
                    klient, prompt_spojny, sciezka, scena["numer"]
                )

                if sukces:
                    koszt_obrazy += 0.040
                    # Zastąp stary obraz spójnym
                    for j, obr in enumerate(obrazy):
                        if obr["numer_sceny"] == scena["numer"]:
                            obrazy[j] = ObrazSceny(
                                numer_sceny=scena["numer"],
                                sciezka_pliku=sciezka_pliku,
                                prompt_uzyty=prompt_spojny,
                                rozdzielczosc="1024x1792",
                                format="png",
                            )
                            log.info("Scena regenerowana dla spójności", numer=scena["numer"])
                            break

    # Generuj miniaturkę
    if wszystkie_sceny:
        prompt_miniatury = zoptymalizuj_prompt(
            opis_sceny=plan.get("hak_wizualny", wszystkie_sceny[0]["opis_wizualny"]),
            styl_wizualny=styl_wizualny,
            emocja="zaskoczenie",
            marka=marka,
        )
        sciezka_miniatury = katalog_obrazy / "miniaturka.png"
        sukces_min, _ = await generuj_obraz_sceny(
            klient, prompt_miniatury, sciezka_miniatury, 0
        )
        if sukces_min:
            koszt_obrazy += 0.040

    wizualia: WizualiaWideo = {
        "obrazy": obrazy,
        "styl_wizualny": styl_wizualny,
        "paleta_kolorow": marka.get("kolory", "dynamiczne"),
        "liczba_obrazow": len(obrazy),
    }

    log.info(
        "Wizualia v2.0 gotowe",
        obrazy=len(obrazy),
        koszt_usd=round(koszt_obrazy, 3),
    )

    return {
        "wizualia": wizualia,
        "krok_aktualny": "wizualia_gotowe",
        "koszt_calkowity_usd": stan.get("koszt_calkowity_usd", 0.0) + koszt_obrazy,
    }
