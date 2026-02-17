"""
ViraLoop – Główny moduł API (FastAPI)

Inicjalizuje aplikację FastAPI, konfiguruje middleware,
rejestruje routery i zarządza cyklem życia aplikacji.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog

from backend.api.routes import (
    router_wideo,
    router_audio,
    router_analityka,
    router_projekty,
    router_uzytkownik,
    router_zgodnosc,
)
from backend.utils.konfiguracja import ustawienia
from backend.utils.baza_danych import inicjalizuj_polaczenia, zamknij_polaczenia

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def zarzadca_cyklu_zycia(aplikacja: FastAPI) -> AsyncGenerator:
    """Inicjalizuje i zamyka zasoby przy starcie/zatrzymaniu aplikacji."""
    logger.info("Uruchamianie ViraLoop API...", wersja=ustawienia.WERSJA_API)

    # Nawiąż połączenia z bazami danych
    await inicjalizuj_polaczenia()
    logger.info("Połączenia z bazami danych nawiązane")

    yield  # Aplikacja działa

    # Zamknij połączenia przy wyłączeniu
    await zamknij_polaczenia()
    logger.info("ViraLoop API zatrzymane")


aplikacja = FastAPI(
    title="ViraLoop API",
    description=(
        "API platformy ViraLoop do generowania i optymalizacji wirusowych treści wideo. "
        "Obsługuje generowanie wideo, syntezę głosu, analizę trendów i dystrybucję na platformy społecznościowe."
    ),
    version=ustawienia.WERSJA_API,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=zarzadca_cyklu_zycia,
)

# ---- Middleware ----

aplikacja.add_middleware(GZipMiddleware, minimum_size=1000)

aplikacja.add_middleware(
    CORSMiddleware,
    allow_origins=ustawienia.DOZWOLONE_ZRODLA,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@aplikacja.middleware("http")
async def middleware_logowania(zadanie: Request, wywolaj_nastepny):
    """Loguje każde żądanie HTTP z czasem odpowiedzi."""
    import time

    czas_start = time.perf_counter()
    odpowiedz = await wywolaj_nastepny(zadanie)
    czas_trwania = time.perf_counter() - czas_start

    logger.info(
        "Żądanie HTTP",
        metoda=zadanie.method,
        url=str(zadanie.url),
        kod_statusu=odpowiedz.status_code,
        czas_ms=round(czas_trwania * 1000, 2),
    )
    return odpowiedz


# ---- Obsługa błędów ----


@aplikacja.exception_handler(ValueError)
async def obsluga_bledu_walidacji(zadanie: Request, blad: ValueError):
    return JSONResponse(
        status_code=422,
        content={"blad": "Błąd walidacji danych", "szczegoly": str(blad)},
    )


@aplikacja.exception_handler(PermissionError)
async def obsluga_bledu_uprawnien(zadanie: Request, blad: PermissionError):
    return JSONResponse(
        status_code=403,
        content={"blad": "Brak uprawnień", "szczegoly": str(blad)},
    )


# ---- Rejestracja routerów ----

aplikacja.include_router(router_wideo, prefix="/api/v1/wideo", tags=["Wideo"])
aplikacja.include_router(router_audio, prefix="/api/v1/audio", tags=["Audio"])
aplikacja.include_router(router_analityka, prefix="/api/v1/analityka", tags=["Analityka"])
aplikacja.include_router(router_projekty, prefix="/api/v1/projekty", tags=["Projekty"])
aplikacja.include_router(router_uzytkownik, prefix="/api/v1/uzytkownik", tags=["Użytkownik"])
aplikacja.include_router(router_zgodnosc, prefix="/api/v1/zgodnosc", tags=["Zgodność C2PA"])


# ---- Endpoint zdrowia ----


@aplikacja.get("/api/zdrowie", tags=["System"])
async def sprawdz_zdrowie():
    """Sprawdza stan zdrowia aplikacji."""
    return {
        "status": "działa",
        "wersja": ustawienia.WERSJA_API,
        "srodowisko": ustawienia.SRODOWISKO,
    }


@aplikacja.get("/", tags=["System"])
async def glowna():
    """Strona główna API."""
    return {
        "platforma": "ViraLoop",
        "opis": "Platforma AI do generowania wirusowych treści wideo",
        "docs": "/api/docs",
    }
