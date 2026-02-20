"""
NEXUS — Agent 3: Reżyser Głosu
================================
Generuje profesjonalną narrację audio dla wideo.
Model: OpenAI TTS-1 (koszt ~$0.018 na wideo)

Kompetencje:
- Dobór optymalnego głosu do treści
- Synteza mowy z modulacją emocjonalną
- Segmentacja audio per scena
- Walidacja jakości dźwięku
"""

import os
import json
import asyncio
import structlog
from pathlib import Path
from openai import AsyncOpenAI

from konfiguracja import konf
from agenci.schematy import StanNEXUS, AudioWideo

logger = structlog.get_logger(__name__)

# Mapowanie emocji do głosów OpenAI
# nova: ciepły, angażujący (dobry do storytellingu)
# alloy: neutralny, profesjonalny
# echo: głęboki, pewny (dobry do edukacji)
# fable: wyrazisty, dramatyczny
# onyx: mocny, autorytatywny
# shimmer: delikatny, przyjemny

GLOSY_PER_EMOCJE = {
    "inspiracja": "nova",
    "energia": "echo",
    "profesjonalizm": "onyx",
    "przyjazny": "nova",
    "dramatyczny": "fable",
    "spokojny": "shimmer",
    "autorytatywny": "onyx",
    "ciekawość": "alloy",
}

GLOSY_PER_PLATORMA = {
    "tiktok": "nova",       # Młody, energiczny
    "youtube": "echo",      # Profesjonalny
    "instagram": "shimmer", # Estetyczny
}


def wybierz_glos(plan_tresci: dict) -> str:
    """Dobiera optymalny głos na podstawie tonu i platformy."""
    ton = plan_tresci.get("ton_glosu", "energiczny").lower()
    platforma = plan_tresci.get("platforma_docelowa", ["tiktok"])[0]

    # Ton ma pierwszeństwo
    for emocja, glos in GLOSY_PER_EMOCJE.items():
        if emocja in ton:
            return glos

    # Jeśli nie pasuje emocja, użyj platformy
    return GLOSY_PER_PLATORMA.get(platforma, konf.DOMYSLNY_GLOS)


async def generuj_audio_sceny(
    klient: AsyncOpenAI,
    tekst: str,
    glos: str,
    sciezka: Path,
    hd: bool = False
) -> bool:
    """
    Generuje audio dla jednej sceny.

    Args:
        klient: Klient OpenAI
        tekst: Tekst do syntezy
        glos: Nazwa głosu
        sciezka: Ścieżka wyjściowa
        hd: Czy używać TTS-HD (droższego)

    Returns:
        True jeśli sukces
    """
    if not tekst.strip():
        return False

    model_tts = konf.MODEL_GLOS_HD if hd else konf.MODEL_GLOS

    odpowiedz = await klient.audio.speech.create(
        model=model_tts,
        voice=glos,
        input=tekst,
        response_format="mp3",
        speed=1.0,
    )

    sciezka.parent.mkdir(parents=True, exist_ok=True)
    with open(sciezka, "wb") as plik:
        plik.write(odpowiedz.content)

    return True


async def rezyser_glosu(stan: StanNEXUS) -> dict:
    """
    Agent Reżyser Głosu — generuje narrację audio.

    Args:
        stan: Stan NEXUS ze scenariuszem

    Returns:
        Aktualizacja stanu z audio
    """
    log = logger.bind(agent="rezyser_glosu")

    if not stan.get("scenariusz"):
        return {
            "bledy": ["Reżyser Głosu: brak scenariusza"],
            "krok_aktualny": "blad_rezysera",
        }

    scenariusz = stan["scenariusz"]
    plan = stan.get("plan_tresci", {})
    log.info("Reżyser Głosu generuje narrację", sceny=len(scenariusz["sceny"]))

    klient = AsyncOpenAI(api_key=konf.OPENAI_API_KEY)

    # Wybierz głos
    glos = wybierz_glos(plan)

    # Utwórz katalog tymczasowy
    sesja_id = stan.get("metadane", {}).get("sesja_id", "domyslna")
    katalog_audio = Path(konf.SCIEZKA_TYMCZASOWA) / sesja_id / "audio"
    katalog_audio.mkdir(parents=True, exist_ok=True)

    # Zbuduj pełny tekst narracji (łączymy wszystkie sceny)
    pelny_tekst = " ".join(
        s["tekst_narracji"]
        for s in scenariusz["sceny"]
        if s["tekst_narracji"].strip()
    )

    # Koszt TTS: $15/1M znaków
    liczba_znakow = len(pelny_tekst)
    koszt_tts = liczba_znakow * 15 / 1_000_000

    sciezka_pelne = katalog_audio / "narracja_pelna.mp3"

    try:
        # Generuj pełną narrację
        sukces = await generuj_audio_sceny(
            klient=klient,
            tekst=pelny_tekst,
            glos=glos,
            sciezka=sciezka_pelne,
        )

        if not sukces:
            return {
                "bledy": ["Reżyser Głosu: błąd generacji audio"],
                "krok_aktualny": "blad_rezysera",
            }

        # Szacuj czas trwania (150 słów/min to standardowe tempo TTS)
        liczba_slow = len(pelny_tekst.split())
        czas_trwania = liczba_slow / 150 * 60  # w sekundach

        # Generuj segmenty per scena (równolegle)
        zadania = []
        for scena in scenariusz["sceny"]:
            if scena["tekst_narracji"].strip():
                sciezka_sceny = katalog_audio / f"scena_{scena['numer']:02d}.mp3"
                zadanie = generuj_audio_sceny(
                    klient=klient,
                    tekst=scena["tekst_narracji"],
                    glos=glos,
                    sciezka=sciezka_sceny,
                )
                zadania.append(zadanie)

        if zadania:
            await asyncio.gather(*zadania, return_exceptions=True)
            # Dodatkowy koszt za segmenty (dla timingu)
            koszt_tts += liczba_znakow * 0.3 * 15 / 1_000_000  # ~30% dodatkowy tekst

        # Segmenty z synchronizacją
        segmenty = []
        czas_aktualny = 0.0
        for scena in scenariusz["sceny"]:
            liczba_slow_sceny = len(scena["tekst_narracji"].split())
            czas_sceny = liczba_slow_sceny / 150 * 60
            segmenty.append({
                "numer": scena["numer"],
                "start": czas_aktualny,
                "end": czas_aktualny + czas_sceny,
                "tekst": scena["tekst_narracji"],
            })
            czas_aktualny += czas_sceny

        audio: AudioWideo = {
            "sciezka_pliku": str(sciezka_pelne),
            "czas_trwania": czas_trwania,
            "jezyk": "pl",
            "glos": glos,
            "format": "mp3",
            "transkrypcja": pelny_tekst,
            "segmenty": segmenty,
        }

        log.info(
            "Audio wygenerowane",
            glos=glos,
            czas_s=round(czas_trwania, 1),
            znaki=liczba_znakow,
            koszt_usd=round(koszt_tts, 5)
        )

        return {
            "audio": audio,
            "krok_aktualny": "audio_gotowe",
            "koszt_calkowity_usd": stan.get("koszt_calkowity_usd", 0.0) + koszt_tts,
        }

    except Exception as e:
        log.error("Błąd Reżysera Głosu", blad=str(e))
        return {
            "bledy": [f"Reżyser Głosu: {str(e)}"],
            "krok_aktualny": "blad_rezysera",
        }
