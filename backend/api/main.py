"""
NEXUS — Główna Aplikacja FastAPI
==================================
Centralny serwer API dla platformy NEXUS AI Video Factory.

Architektura:
- FastAPI z async/await przez cały stack
- Middleware: CORS, GZip, strukturowane logi
- OpenAPI docs na /docs i /redoc
- Health check na /api/zdrowie

Uruchomienie:
    uvicorn api.main:app --reload --port 8000
"""

import os
import time
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from konfiguracja import pobierz_konfiguracje
from api.trasy.wideo import router as router_wideo

# Konfiguruj strukturowane logi
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
konf = pobierz_konfiguracje()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup i shutdown hooks."""
    # Startup
    logger.info(
        "NEXUS AI Video Factory uruchamia się",
        wersja=konf.WERSJA_API,
        srodowisko=konf.SRODOWISKO,
        openai_skonfigurowany=bool(konf.OPENAI_API_KEY),
    )

    # Utwórz katalogi
    for katalog in [konf.SCIEZKA_TYMCZASOWA, konf.SCIEZKA_WYJSCIOWA, konf.CHROMA_SCIEZKA]:
        os.makedirs(katalog, exist_ok=True)

    yield

    # Shutdown
    logger.info("NEXUS zamyka się")


# ====================================================================
# APLIKACJA
# ====================================================================

app = FastAPI(
    title="NEXUS — AI Video Factory",
    description="""
## Platforma NEXUS — Fabryka Wirusowych Wideo AI

Bezkonkurencyjna platforma multi-agentowa do tworzenia krótkich wideo na kluczu OpenAI.

### Architektura Multi-Agentowa:
1. **Strateg Treści** (GPT-4o-mini) — analizuje brief, tworzy plan
2. **Pisarz Scenariuszy** (GPT-4o-mini) — pisze scenariusz
3. **Reżyser Głosu** (OpenAI TTS) — syntezuje narrację
4. **Producent Wizualny** (DALL-E 3) — generuje obrazy scen
5. **Recenzent Jakości** (GPT-4o) — ocenia i zatwierdza

### Koszt: ~$0.14/wideo | Czas: ~90 sekund | Jakość: Profesjonalna

### NEXUS Viral Score (NVS):
- 🔥 85-100: Wysoki potencjał wiralny
- ✅ 60-84: Dobry content
- ⚠️ <60: Wymaga optymalizacji
""",
    version=konf.WERSJA_API,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ====================================================================
# MIDDLEWARE
# ====================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=konf.DOZWOLONE_ZRODLA,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip dla dużych odpowiedzi
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Middleware logowania czasu odpowiedzi
@app.middleware("http")
async def loguj_czas_odpowiedzi(request: Request, call_next):
    czas_start = time.perf_counter()
    odpowiedz = await call_next(request)
    czas_ms = int((time.perf_counter() - czas_start) * 1000)

    logger.debug(
        "Żądanie HTTP",
        metoda=request.method,
        sciezka=request.url.path,
        status=odpowiedz.status_code,
        czas_ms=czas_ms,
    )

    odpowiedz.headers["X-Response-Time"] = f"{czas_ms}ms"
    return odpowiedz


# ====================================================================
# ROUTERY
# ====================================================================

app.include_router(router_wideo)


# ====================================================================
# ENDPOINTY SPECJALNE
# ====================================================================

@app.get("/", summary="Informacje o API")
async def root():
    """Główny endpoint z informacjami o platformie NEXUS."""
    return {
        "platforma": "NEXUS AI Video Factory",
        "wersja": konf.WERSJA_API,
        "opis": "Bezkonkurencyjna platforma multi-agentowa do tworzenia wirusowych wideo",
        "modele": {
            "strategia": "GPT-4o-mini",
            "scenariusz": "GPT-4o-mini",
            "glos": "OpenAI TTS-1",
            "wizualia": "DALL-E 3",
            "recenzja": "GPT-4o",
        },
        "koszt_per_wideo": "~$0.14",
        "czas_generacji": "~90 sekund",
        "endpointy": {
            "docs": "/docs",
            "generuj": "POST /api/v1/wideo/generuj",
            "wiralnosc": "POST /api/v1/wideo/wiralnosc",
            "zdrowie": "/api/zdrowie",
        }
    }


@app.get("/api/zdrowie", summary="Health Check", tags=["System"])
async def zdrowie():
    """Sprawdza zdrowie wszystkich komponentów platformy."""
    import shutil

    komponenty = {
        "api": "ok",
        "openai": "ok" if konf.OPENAI_API_KEY else "brak_klucza",
        "ffmpeg": "ok" if shutil.which("ffmpeg") else "niedostepny",
        "katalogi": {
            "tymczasowy": os.path.exists(konf.SCIEZKA_TYMCZASOWA),
            "wyjsciowy": os.path.exists(konf.SCIEZKA_WYJSCIOWA),
        },
    }

    status_ogolny = "zdrowy" if all([
        komponenty["openai"] == "ok",
        komponenty["ffmpeg"] == "ok",
    ]) else "czesciowo_zdrowy"

    return {
        "status": status_ogolny,
        "platforma": "NEXUS",
        "wersja": konf.WERSJA_API,
        "srodowisko": konf.SRODOWISKO,
        "komponenty": komponenty,
    }


@app.get("/api/modele", summary="Lista dostępnych modeli", tags=["System"])
async def lista_modeli():
    """Lista modeli OpenAI używanych przez NEXUS z kosztami."""
    return {
        "modele": [
            {
                "id": "gpt-4o-mini",
                "zastosowanie": ["strategia", "scenariusz", "wiralnosc"],
                "koszt_input_1m": "$0.15",
                "koszt_output_1m": "$0.60",
                "optymalizacja": "90% zadań — najlepszy stosunek jakości do ceny",
            },
            {
                "id": "gpt-4o",
                "zastosowanie": ["recenzja_jakosci"],
                "koszt_input_1m": "$2.50",
                "koszt_output_1m": "$10.00",
                "optymalizacja": "10% zadań — tylko krytyczne decyzje jakości",
            },
            {
                "id": "dall-e-3",
                "zastosowanie": ["generacja_obrazow", "miniaturka"],
                "koszt_per_obraz": "$0.04 (standard) | $0.08 (HD)",
                "rozdzielczosc": "1024x1792 (9:16 pionowy)",
                "optymalizacja": "Max 5 obrazów/wideo dla optymalizacji kosztów",
            },
            {
                "id": "tts-1",
                "zastosowanie": ["narracja"],
                "koszt_1m_znakow": "$15.00",
                "glosy": ["nova", "alloy", "echo", "fable", "onyx", "shimmer"],
                "optymalizacja": "tts-1 vs tts-1-hd: 2x tańszy, minimalna różnica jakości",
            },
            {
                "id": "text-embedding-3-small",
                "zastosowanie": ["rag_marka", "podobienstwo"],
                "koszt_1m_tokenow": "$0.020",
                "wymiary": 1536,
                "optymalizacja": "Najtańszy embedding OpenAI, wystarczający dla RAG",
            },
        ],
        "szacowany_koszt_per_wideo": {
            "gpt_4o_mini_skrypty": "$0.001",
            "dall_e_3_3_obrazy": "$0.120",
            "tts_narracja": "$0.018",
            "gpt_4o_recenzja": "$0.005",
            "embeddingi_rag": "$0.001",
            "total": "~$0.145",
        }
    }
