"""
NEXUS — Trasy API: Wideo
=========================
Endpointy do generacji i zarządzania wideo.

Endpointy:
- POST /api/v1/wideo/generuj — Uruchom pipeline generacji
- GET  /api/v1/wideo/{sesja_id}/status — Sprawdź status sesji
- GET  /api/v1/wideo/{sesja_id}/pobierz — Pobierz gotowe wideo
- POST /api/v1/wideo/wiralnosc — Szybka analiza wiralności (bez generacji)
- GET  /api/v1/wideo/historia — Historia generacji (mock)
"""

import os
import structlog
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from konfiguracja import konf, pobierz_konfiguracje
from agenci.orkiestrator import pobierz_orkiestratora
from analityka.silnik_wiralnosci import analizuj_wiralnosc, oblicz_nwv_heurystyczny
from rag.baza_wiedzy import pobierz_baze_wiedzy

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/wideo", tags=["Wideo"])

# Cache aktywnych sesji
_aktywne_sesje: dict[str, dict] = {}


# ====================================================================
# SCHEMATY ŻĄDAŃ / ODPOWIEDZI
# ====================================================================

class ZadanieGeneracji(BaseModel):
    """Żądanie generacji wideo."""
    brief: str = Field(
        min_length=10,
        max_length=2000,
        description="Opis wideo (np. 'Wideo o zaletach zimnych pryszniców')",
        example="Pokaż mi, jak zimne prysznice mogą zmienić Twoje życie w 30 dni"
    )
    platforma: list[str] = Field(
        default=["tiktok", "youtube"],
        description="Platformy docelowe"
    )
    marka: dict = Field(
        default={},
        description="Profil marki {'nazwa': '...', 'ton': '...', 'styl': '...'}"
    )
    styl_wizualny: str = Field(
        default="nowoczesny",
        description="Styl wizualny: nowoczesny | kinowy | estetyczny | dynamiczny"
    )
    dlugosc_sekund: int = Field(
        default=60,
        ge=15,
        le=180,
        description="Docelowa długość wideo w sekundach (15-180)"
    )
    glos: str = Field(
        default="nova",
        description="Głos lektora: nova | alloy | echo | fable | onyx | shimmer"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "brief": "Pokaż mi, jak 10-minutowa medytacja rano zmienia produktywność całego dnia",
                "platforma": ["tiktok", "youtube"],
                "marka": {"nazwa": "MindfulLife", "ton": "spokojny", "styl": "estetyczny"},
                "styl_wizualny": "estetyczny",
                "dlugosc_sekund": 60,
                "glos": "nova"
            }
        }


class ZadanieAnalizyWiralnosci(BaseModel):
    """Żądanie analizy wiralności (bez generacji wideo)."""
    brief: str = Field(min_length=10, max_length=1000)
    platforma: list[str] = Field(default=["tiktok", "youtube"])
    hak_wizualny: str = Field(default="")
    hak_tekstowy: str = Field(default="")
    dlugosc_sekund: int = Field(default=60, ge=15, le=180)


class OdpowiedzGeneracji(BaseModel):
    """Odpowiedź z wynikami generacji."""
    sesja_id: str
    status: str
    wideo: dict | None = None
    ocena_wiralnosci: dict | None = None
    ocena_jakosci: dict | None = None
    plan_tresci: dict | None = None
    scenariusz: dict | None = None
    koszt_usd: float
    czas_generacji_s: float
    bledy: list[str] = []


# ====================================================================
# ENDPOINTY
# ====================================================================

@router.post(
    "/generuj",
    response_model=OdpowiedzGeneracji,
    summary="Generuj wideo AI",
    description="""
Uruchamia kompletny pipeline multi-agentowy NEXUS:

1. **Strateg Treści** — analizuje brief i tworzy plan (GPT-4o-mini)
2. **Pisarz Scenariuszy** — pisze scenariusz scena po scenie (GPT-4o-mini)
3. **Reżyser Głosu** — syntezuje narrację audio (OpenAI TTS)
4. **Producent Wizualny** — generuje obrazy scen (DALL-E 3)
5. **Recenzent Jakości** — ocenia i zatwierdza (GPT-4o)
6. **Compositor** — scala w gotowe MP4 (FFmpeg)

Koszt szacunkowy: ~$0.14/wideo | Czas: ~90 sekund
""",
)
async def generuj_wideo(
    zadanie: ZadanieGeneracji,
    konfiguracja: pobierz_konfiguracje = Depends(pobierz_konfiguracje),
) -> OdpowiedzGeneracji:
    """Główny endpoint generacji wideo NEXUS."""
    log = logger.bind(endpoint="generuj_wideo")
    log.info("Nowe zadanie generacji", brief_dl=len(zadanie.brief))

    if not konfiguracja.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Brak klucza OPENAI_API_KEY w konfiguracji"
        )

    # Wzbogac profil marki o styl i głos
    marka = {
        **zadanie.marka,
        "styl": zadanie.styl_wizualny,
        "preferowany_glos": zadanie.glos,
    }

    # Pobierz kontekst RAG dla marki
    nazwa_marki = zadanie.marka.get("nazwa", "nexus").lower().replace(" ", "_")
    baza = pobierz_baze_wiedzy(nazwa_marki)

    try:
        kontekst_rag = await baza.pobierz_kontekst(zadanie.brief)
    except Exception:
        kontekst_rag = ""

    # Uruchom orkiestrator
    orkiestrator = pobierz_orkiestratora()

    try:
        wynik = await orkiestrator.generuj_wideo(
            brief=zadanie.brief,
            platforma=zadanie.platforma,
            marka=marka,
            kontekst_marki=kontekst_rag,
        )
    except Exception as e:
        log.error("Błąd orkiestratora", blad=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Błąd generacji: {str(e)}"
        )

    return OdpowiedzGeneracji(
        sesja_id=wynik.get("sesja_id", ""),
        status=wynik.get("status", "nieznany"),
        wideo=wynik.get("wideo"),
        ocena_wiralnosci=wynik.get("ocena_wiralnosci"),
        ocena_jakosci=wynik.get("ocena_jakosci"),
        plan_tresci=wynik.get("plan_tresci"),
        scenariusz=wynik.get("scenariusz"),
        koszt_usd=wynik.get("koszt_usd", 0.0),
        czas_generacji_s=wynik.get("czas_generacji_s", 0.0),
        bledy=wynik.get("bledy", []),
    )


@router.get(
    "/{sesja_id}/status",
    summary="Status sesji generacji",
)
async def pobierz_status(sesja_id: str) -> dict:
    """Sprawdza aktualny status sesji generacji."""
    orkiestrator = pobierz_orkiestratora()
    return orkiestrator.pobierz_stan_sesji(sesja_id)


@router.get(
    "/{sesja_id}/pobierz",
    summary="Pobierz gotowe wideo",
)
async def pobierz_wideo(sesja_id: str):
    """Pobiera gotowy plik MP4."""
    sciezka = Path(konf.SCIEZKA_WYJSCIOWA) / sesja_id / "wideo_glowne.mp4"

    if not sciezka.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Wideo dla sesji {sesja_id} nie znalezione"
        )

    return FileResponse(
        path=str(sciezka),
        media_type="video/mp4",
        filename=f"nexus_{sesja_id}.mp4",
    )


@router.get(
    "/{sesja_id}/miniaturka",
    summary="Pobierz miniaturkę wideo",
)
async def pobierz_miniaturke(sesja_id: str):
    """Pobiera miniaturkę JPG."""
    sciezka = Path(konf.SCIEZKA_WYJSCIOWA) / sesja_id / "miniaturka.jpg"

    if not sciezka.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Miniaturka dla sesji {sesja_id} nie znaleziona"
        )

    return FileResponse(
        path=str(sciezka),
        media_type="image/jpeg",
        filename=f"nexus_{sesja_id}_miniaturka.jpg",
    )


@router.post(
    "/wiralnosc",
    summary="Analiza wiralności (bez generacji)",
    description="Szybka predykcja wiralności wideo na podstawie briefu. Koszt: ~$0.001"
)
async def analizuj(zadanie: ZadanieAnalizyWiralnosci) -> dict:
    """Analizuje wiralność briefu bez generacji pełnego wideo."""
    plan_mock = {
        "temat": zadanie.brief,
        "platforma_docelowa": zadanie.platforma,
        "dlugosc_sekund": zadanie.dlugosc_sekund,
        "hak_wizualny": zadanie.hak_wizualny,
        "hak_tekstowy": zadanie.hak_tekstowy,
        "hak_werbalny": "",
        "typ_haka": "luk_ciekawosci",
    }

    # Szybka ocena heurystyczna (bez API)
    nwv_heurystyczny = oblicz_nwv_heurystyczny(plan_mock)

    try:
        # Pełna analiza AI
        wynik = await analizuj_wiralnosc(plan_mock)
        return wynik
    except Exception:
        # Fallback: heurystyka
        return {
            "wynik_nwv": nwv_heurystyczny,
            "wynik_haka": nwv_heurystyczny,
            "wynik_zatrzymania": nwv_heurystyczny - 5,
            "wynik_udostepnialnosci": nwv_heurystyczny - 10,
            "wynik_platformy": {p: nwv_heurystyczny for p in zadanie.platforma},
            "odznaka": "✅ Dobry content" if nwv_heurystyczny >= 70 else "⚠️ Wymaga optymalizacji",
            "uzasadnienie": "Ocena heurystyczna",
            "wskazowki_optymalizacji": [],
        }


@router.get(
    "/historia",
    summary="Historia generacji",
)
async def historia_generacji(limit: int = 10) -> dict:
    """Zwraca historię ostatnich generacji (z pliku lokalnego)."""
    katalog = Path(konf.SCIEZKA_WYJSCIOWA)
    sesje = []

    if katalog.exists():
        for katalog_sesji in sorted(katalog.iterdir(), reverse=True)[:limit]:
            if katalog_sesji.is_dir():
                wideo = katalog_sesji / "wideo_glowne.mp4"
                sesje.append({
                    "sesja_id": katalog_sesji.name,
                    "gotowe": wideo.exists(),
                    "rozmiar_mb": round(wideo.stat().st_size / 1024 / 1024, 2) if wideo.exists() else 0,
                })

    return {"sesje": sesje, "total": len(sesje)}
