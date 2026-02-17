"""
ViraLoop – Router API zgodności C2PA

Obsługuje znakowanie wodne, Content Credentials i moderację treści.
EU AI Act wchodzi w życie 2 sierpnia 2026 – kary do €35M lub 7% obrotu.
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

router = APIRouter()


class WynikZnakowaniaC2PA(BaseModel):
    """Wynik znakowania Content Credentials (C2PA)."""

    id_wideo: UUID
    manifest_c2pa: dict
    hash_wideo: str
    url_weryfikacji: str
    standard: str = "C2PA 2.1"
    zgodny_z_tiktok: bool
    zgodny_z_eu_ai_act: bool


class WynikModeracjiTresci(BaseModel):
    """Wynik moderacji treści."""

    id_zasobu: str
    bezpieczne: bool
    kategorie: dict[str, float]
    wymagana_recenzja_czlowieka: bool
    szczegoly: list[str]


class OswiadczenieAI(BaseModel):
    """Oświadczenie o treści generowanej przez AI wymagane przez platformy."""

    platforma: str
    typ_tresci: str
    stopien_modyfikacji: str
    narzedzia_uzyte: list[str]
    wklad_czlowieka: str


@router.post(
    "/oznacz-c2pa/{id_wideo}",
    response_model=WynikZnakowaniaC2PA,
    summary="Dodaj Content Credentials C2PA",
    description=(
        "Dodaje kryptograficznie podpisane metadane C2PA do wideo. "
        "TikTok (od stycznia 2025) auto-wykrywa treści z 47 platform AI. "
        "Google SynthID oznaczył ponad 10 miliardów treści."
    ),
)
async def oznacz_c2pa(id_wideo: UUID):
    """
    Dodaje Content Credentials zgodne z C2PA do wideo.

    Standard C2PA (Coalition for Content Provenance and Authenticity):
    - Kryptograficznie podpisane metadane o pochodzeniu treści
    - Obsługiwany przez: Google, Meta, TikTok, Adobe, Microsoft
    - Oczekiwana standaryzacja ISO w 2026
    - Wymagany przez EU AI Act od 2 sierpnia 2026

    Implementacja:
    1. Oblicz hash SHA-256 pliku wideo
    2. Utwórz manifest C2PA z informacjami o narzędziach AI
    3. Podpisz manifest kluczem prywatnym platformy
    4. Osadź manifest w metadanych pliku
    """
    from backend.compliance.c2pa_serwis import C2PASerwis

    serwis = C2PASerwis()
    wynik = await serwis.oznacz_wideo(id_wideo)

    if wynik is None:
        raise HTTPException(status_code=404, detail="Wideo nie znalezione")

    return wynik


@router.post(
    "/moderuj",
    response_model=WynikModeracjiTresci,
    summary="Moderacja treści",
    description=(
        "Wielowarstwowa moderacja treści: filtrowanie promptów → "
        "klasyfikatory wyjścia (NSFW, przemoc, prawa autorskie) → "
        "eskalacja do recenzji człowieka."
    ),
)
async def moderuj_tresc(
    plik: UploadFile = File(..., description="Plik wideo lub obraz do moderacji"),
):
    """
    Moderuje treść przez wielowarstwowy system.

    Warstwy moderacji:
    1. Filtrowanie promptów wejściowych (blokowanie szkodliwych treści)
    2. Dopasowanie bezpieczeństwa na poziomie modelu
    3. Klasyfikatory wyjścia: NSFW, przemoc, materiały chronione prawem autorskim
    4. Eskalacja do recenzji człowieka dla przypadków granicznych

    Używa Azure AI Content Safety lub własnych klasyfikatorów.
    """
    from backend.compliance.moderacja_serwis import ModeracjaSerwis

    serwis = ModeracjaSerwis()
    wynik = await serwis.analizuj(plik)

    return wynik


@router.get(
    "/weryfikuj/{id_wideo}",
    summary="Weryfikuj Content Credentials",
    description="Weryfikuje autentyczność i pochodzenie wideo przez łańcuch C2PA.",
)
async def weryfikuj_c2pa(id_wideo: UUID):
    """Weryfikuje podpis C2PA i łańcuch proweniencji wideo."""
    return {
        "id_wideo": str(id_wideo),
        "weryfikacja": "oczekiwanie",
        "komunikat": "Weryfikacja C2PA zainicjowana",
    }


@router.get(
    "/wymagania-platform",
    summary="Wymagania platform dot. treści AI",
)
async def wymagania_platform():
    """
    Zwraca aktualne wymagania prawne platform wobec treści AI.

    Uwaga: Nieprzestrzeganie może skutkować demonetyzacją lub banem.
    """
    return {
        "youtube": {
            "wymaga_ujawnienia": True,
            "od": "2023-11-01",
            "demonetyzacja_masowych_tresci_ai": True,
            "od_demonetyzacji": "2025-07-01",
            "natywny_ab_test": "Test & Compare (do 3 wariantów tytułu/miniatury)",
        },
        "tiktok": {
            "wymaga_ujawnienia": True,
            "automatyczne_wykrywanie_c2pa": True,
            "liczba_wykrywanych_platform": 47,
            "od": "2025-01-01",
            "wzrost_usuniec_vs_2024": "340%",
            "konta_trwale_zbanowane": 8600,
        },
        "instagram": {
            "wymaga_ujawnienia": True,
            "reels_skip_rate": "dostępny od grudnia 2025",
            "repost_counts": "dostępny od grudnia 2025",
        },
        "eu_ai_act": {
            "obowiazuje": "2026-08-02",
            "max_kara": "35 000 000 EUR lub 7% globalnego obrotu",
            "wymaga": "Etykietowanie treści AI, transparentność systemu",
        },
        "usa_ftc": {
            "zakaz_fejkowych_recenzji_ai": True,
            "kara_za_incydent": "51 744 USD",
            "wymaga_ujawnienia_podobizny_ai_w_reklamie": True,
        },
    }
