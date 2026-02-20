"""
NEXUS — Agent 4: Producent Wizualny
=====================================
Generuje obrazy dla każdej sceny przy użyciu DALL-E 3.
Model: dall-e-3 (koszt $0.04/obraz = ~$0.12 na wideo za 3 obrazy)

Kompetencje:
- Optymalizacja promptów dla DALL-E 3
- Generacja spójnych wizualnie scen
- Adaptacja do stylu marki
- Generacja miniaturki wideo
"""

import os
import asyncio
import structlog
import httpx
from pathlib import Path
from openai import AsyncOpenAI

from konfiguracja import konf
from agenci.schematy import StanNEXUS, WizualiaWideo, ObrazSceny

logger = structlog.get_logger(__name__)

# Szablony promptów dla DALL-E 3 — optymalizowane dla wirusowych treści
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
}


def zoptymalizuj_prompt(
    opis_sceny: str,
    styl_wizualny: str,
    emocja: str,
    marka: dict
) -> str:
    """Tworzy zoptymalizowany prompt dla DALL-E 3."""
    styl_dall_e = STYL_DO_DALL_E.get(
        styl_wizualny.split(",")[0].strip().lower(),
        "professional, high quality, vibrant"
    )
    emocja_wizualna = EMOCJA_DO_WIZUALU.get(emocja.lower(), "engaging, dynamic")

    # Kontekst marki
    kolory_marki = marka.get("kolory", "")
    prefix_marki = f"Brand colors: {kolory_marki}. " if kolory_marki else ""

    prompt = f"""{prefix_marki}{opis_sceny}. {styl_dall_e}, {emocja_wizualna}, \
ultra-HD quality, cinematic composition, professional photography, \
vertical 9:16 format, no text overlays, no watermarks, photorealistic render"""

    # DALL-E 3 ma limit 4000 znaków
    return prompt[:4000]


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
    numer_sceny: int
) -> tuple[bool, str]:
    """
    Generuje obraz dla jednej sceny.

    Returns:
        (sukces, ścieżka_pliku)
    """
    try:
        odpowiedz = await klient.images.generate(
            model=konf.MODEL_OBRAZY,   # dall-e-3
            prompt=prompt,
            size="1024x1792",           # Pionowy format 9:16 (idealny dla short video)
            quality="standard",         # standard ($0.04) vs hd ($0.08)
            n=1,
            style="vivid",              # vivid = bardziej dramatyczny i angażujący
        )

        url_obrazu = odpowiedz.data[0].url
        await pobierz_i_zapisz_obraz(url_obrazu, sciezka)

        return True, str(sciezka)

    except Exception as e:
        logger.error("Błąd generacji obrazu", numer_sceny=numer_sceny, blad=str(e))
        return False, ""


async def producent_wizualny(stan: StanNEXUS) -> dict:
    """
    Agent Producent Wizualny — generuje obrazy dla scen.

    Strategia kosztowa:
    - Max 5 obrazów na wideo (konf.MAKS_OBRAZOW_NA_SCENA)
    - Priorytet: scena 1 (hak), kluczowe sceny, ostatnia
    - Koszt: $0.04 * liczba_obrazów

    Args:
        stan: Stan NEXUS ze scenariuszem

    Returns:
        Aktualizacja stanu z wizualiami
    """
    log = logger.bind(agent="producent_wizualny")

    if not stan.get("scenariusz"):
        return {
            "bledy": ["Producent Wizualny: brak scenariusza"],
            "krok_aktualny": "blad_producenta",
        }

    scenariusz = stan["scenariusz"]
    plan = stan.get("plan_tresci", {})
    marka = stan.get("marka", {})

    # Wybierz które sceny generować (max 5 dla optymalizacji kosztów)
    wszystkie_sceny = scenariusz["sceny"]
    maks = konf.MAKS_OBRAZOW_NA_SCENA

    if len(wszystkie_sceny) <= maks:
        sceny_do_generacji = wszystkie_sceny
    else:
        # Zawsze generuj: pierwsze 2, środkowe kluczowe, ostatnie 2
        indeksy = list(range(min(2, len(wszystkie_sceny))))  # Pierwsze 2
        srodek = len(wszystkie_sceny) // 2
        if srodek not in indeksy:
            indeksy.append(srodek)
        # Ostatnie 2
        for i in range(max(0, len(wszystkie_sceny) - 2), len(wszystkie_sceny)):
            if i not in indeksy:
                indeksy.append(i)
        indeksy = sorted(set(indeksy))[:maks]
        sceny_do_generacji = [wszystkie_sceny[i] for i in indeksy]

    log.info("Producent Wizualny generuje obrazy", liczba=len(sceny_do_generacji))

    klient = AsyncOpenAI(api_key=konf.OPENAI_API_KEY)

    # Ścieżki
    sesja_id = stan.get("metadane", {}).get("sesja_id", "domyslna")
    katalog_obrazy = Path(konf.SCIEZKA_TYMCZASOWA) / sesja_id / "obrazy"
    katalog_obrazy.mkdir(parents=True, exist_ok=True)

    styl_wizualny = plan.get("styl_wizualny", "nowoczesny")

    # Generuj obrazy równolegle (ale max 3 naraz — limit API)
    obrazy: list[ObrazSceny] = []
    koszt_obrazy = 0.0

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
                koszt_obrazy += 0.040  # $0.04 za standard DALL-E 3

    # Generuj miniaturkę (z pierwszej lub specjalnej sceny)
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
        "Wizualia gotowe",
        obrazy=len(obrazy),
        koszt_usd=round(koszt_obrazy, 3)
    )

    return {
        "wizualia": wizualia,
        "krok_aktualny": "wizualia_gotowe",
        "koszt_calkowity_usd": stan.get("koszt_calkowity_usd", 0.0) + koszt_obrazy,
    }
