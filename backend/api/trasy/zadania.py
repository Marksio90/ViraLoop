"""
NEXUS — Trasy API: Zadania (Async Job Queue)
=============================================
Zarządzanie asynchronicznymi zadaniami generacji wideo.

Endpointy:
- POST /api/v1/zadania/generuj   — Wyślij zadanie do kolejki (async)
- GET  /api/v1/zadania/{task_id} — Status zadania
- GET  /api/v1/zadania/{task_id}/stan — Stan z Redis (polling-friendly)
- DELETE /api/v1/zadania/{task_id} — Anuluj zadanie
- GET  /api/v1/zadania             — Lista aktywnych zadań
"""

import json
import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from celery.result import AsyncResult

from konfiguracja import konf, pobierz_konfiguracje
from celery_app import celery_app
from rag.baza_wiedzy import pobierz_baze_wiedzy
import uuid

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/zadania", tags=["Zadania Async"])


# ====================================================================
# SCHEMATY
# ====================================================================

class ZadanieAsync(BaseModel):
    """Żądanie asynchronicznej generacji wideo."""
    brief: str = Field(min_length=10, max_length=2000)
    platforma: list[str] = Field(default=["tiktok", "youtube"])
    marka: dict = Field(default={})
    styl_wizualny: str = Field(default="nowoczesny")
    dlugosc_sekund: int = Field(default=60, ge=15, le=180)
    glos: str = Field(default="nova")
    priorytet: int = Field(default=5, ge=1, le=10, description="Priorytet zadania (10=najwyższy)")

    class Config:
        json_schema_extra = {
            "example": {
                "brief": "Pokaż jak cold shower boost testosteron i energię",
                "platforma": ["tiktok", "youtube"],
                "dlugosc_sekund": 60,
                "priorytet": 5,
            }
        }


class OdpowiedzAsync(BaseModel):
    """Odpowiedź po przyjęciu zadania do kolejki."""
    task_id: str
    sesja_id: str
    status: str = "w_kolejce"
    wiadomosc: str
    ws_url: str
    polling_url: str


class StatusZadania(BaseModel):
    """Status zadania Celery."""
    task_id: str
    sesja_id: str
    status: str
    procent: int = 0
    krok: str = ""
    wiadomosc: str = ""
    wynik: dict | None = None
    blad: str | None = None


# ====================================================================
# MAPOWANIE STATUSÓW CELERY → POLSKI
# ====================================================================

STATUSY_PL = {
    "PENDING": "w_kolejce",
    "RECEIVED": "odebrane",
    "STARTED": "w_trakcie",
    "PROGRESS": "w_trakcie",
    "SUCCESS": "sukces",
    "FAILURE": "blad",
    "RETRY": "ponawiane",
    "REVOKED": "anulowane",
}


# ====================================================================
# ENDPOINTY
# ====================================================================

@router.post(
    "/generuj",
    response_model=OdpowiedzAsync,
    summary="Generuj wideo asynchronicznie",
    description="""
Wysyła zadanie generacji wideo do kolejki Celery i **natychmiast zwraca** task_id.
Generacja dzieje się w tle — śledź postęp przez WebSocket lub polling.

**WebSocket (zalecany):** `ws://localhost/ws/wideo/{sesja_id}`
**Polling:** `GET /api/v1/zadania/{task_id}`

Koszt: ~$0.14/wideo | Czas: ~90s
""",
)
async def wyslij_zadanie(
    zadanie: ZadanieAsync,
    konfiguracja: pobierz_konfiguracje = Depends(pobierz_konfiguracje),
) -> OdpowiedzAsync:
    """Asynchroniczny endpoint generacji — zwraca natychmiast."""
    log = logger.bind(endpoint="wyslij_zadanie")

    if not konfiguracja.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="Brak klucza OPENAI_API_KEY")

    sesja_id = str(uuid.uuid4())[:8]
    log.info("Wysyłam zadanie do kolejki", sesja_id=sesja_id)

    # Pobierz kontekst RAG
    nazwa_marki = zadanie.marka.get("nazwa", "nexus").lower().replace(" ", "_")
    baza = pobierz_baze_wiedzy(nazwa_marki)
    try:
        kontekst_rag = await baza.pobierz_kontekst(zadanie.brief)
    except Exception:
        kontekst_rag = ""

    # Przygotuj profil marki
    marka = {**zadanie.marka, "styl": zadanie.styl_wizualny, "preferowany_glos": zadanie.glos}

    # Wyślij do Celery
    from zadania.generacja import generuj_wideo_task

    task = generuj_wideo_task.apply_async(
        kwargs={
            "sesja_id": sesja_id,
            "brief": zadanie.brief,
            "platforma": zadanie.platforma,
            "marka": marka,
            "kontekst_marki": kontekst_rag,
        },
        priority=zadanie.priorytet,
        task_id=f"nexus-{sesja_id}",
    )

    log.info("Zadanie w kolejce", task_id=task.id, sesja_id=sesja_id)

    return OdpowiedzAsync(
        task_id=task.id,
        sesja_id=sesja_id,
        status="w_kolejce",
        wiadomosc="Zadanie przyjęte! Pipeline NEXUS uruchomi się za chwilę.",
        ws_url=f"/ws/wideo/{sesja_id}",
        polling_url=f"/api/v1/zadania/{task.id}",
    )


@router.get(
    "/{task_id}",
    response_model=StatusZadania,
    summary="Status zadania",
)
async def pobierz_status_zadania(task_id: str) -> StatusZadania:
    """Sprawdza status zadania Celery (do pollingu)."""
    result = AsyncResult(task_id, app=celery_app)

    status_pl = STATUSY_PL.get(result.state, result.state.lower())
    sesja_id = task_id.replace("nexus-", "")

    if result.state == "PENDING":
        return StatusZadania(
            task_id=task_id, sesja_id=sesja_id,
            status=status_pl, procent=0, wiadomosc="Oczekuję na wolnego workera...",
        )

    elif result.state == "PROGRESS":
        meta = result.info or {}
        return StatusZadania(
            task_id=task_id, sesja_id=sesja_id,
            status=status_pl,
            procent=meta.get("procent", 0),
            krok=meta.get("krok", ""),
            wiadomosc=meta.get("wiadomosc", ""),
        )

    elif result.state == "SUCCESS":
        return StatusZadania(
            task_id=task_id, sesja_id=sesja_id,
            status=status_pl, procent=100,
            wiadomosc="Wideo gotowe!",
            wynik=result.result,
        )

    elif result.state == "FAILURE":
        return StatusZadania(
            task_id=task_id, sesja_id=sesja_id,
            status=status_pl, procent=0,
            wiadomosc="Generacja nie powiodła się",
            blad=str(result.info),
        )

    else:
        return StatusZadania(
            task_id=task_id, sesja_id=sesja_id,
            status=status_pl, procent=0,
            wiadomosc=f"Status: {result.state}",
        )


@router.get(
    "/{task_id}/stan",
    summary="Stan z Redis (polling-friendly)",
)
async def pobierz_stan_redis(task_id: str) -> dict:
    """Pobiera ostatni znany stan z Redis pub/sub (szybszy niż polling Celery)."""
    sesja_id = task_id.replace("nexus-", "")

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(konf.REDIS_URL, decode_responses=True)
        stan_json = await r.get(f"nexus:stan:{sesja_id}")
        await r.aclose()

        if stan_json:
            return json.loads(stan_json)
        else:
            return {"sesja_id": sesja_id, "krok": "oczekiwanie", "procent": 0, "wiadomosc": "Oczekuję..."}
    except Exception as e:
        return {"sesja_id": sesja_id, "blad": str(e)}


@router.delete(
    "/{task_id}",
    summary="Anuluj zadanie",
)
async def anuluj_zadanie(task_id: str) -> dict:
    """Anuluje oczekujące lub aktywne zadanie Celery."""
    result = AsyncResult(task_id, app=celery_app)

    if result.state in ["SUCCESS", "FAILURE"]:
        raise HTTPException(
            status_code=409,
            detail=f"Nie można anulować zadania ze statusem: {result.state}"
        )

    celery_app.control.revoke(task_id, terminate=True)
    logger.info("Zadanie anulowane", task_id=task_id)

    return {"task_id": task_id, "status": "anulowane", "wiadomosc": "Zadanie zostało anulowane"}


@router.get(
    "",
    summary="Aktywne zadania",
)
async def lista_zadan() -> dict:
    """Lista aktywnych zadań Celery (wymaga połączenia z brokerem)."""
    try:
        inspect = celery_app.control.inspect(timeout=2)
        aktywne = inspect.active() or {}
        zarezerwowane = inspect.reserved() or {}

        zadania_aktywne = []
        for worker, zadania in aktywne.items():
            for z in zadania:
                zadania_aktywne.append({
                    "task_id": z.get("id"),
                    "worker": worker,
                    "status": "w_trakcie",
                    "czas_start": z.get("time_start"),
                })

        zadania_zarezerwowane = []
        for worker, zadania in zarezerwowane.items():
            for z in zadania:
                zadania_zarezerwowane.append({
                    "task_id": z.get("id"),
                    "worker": worker,
                    "status": "zarezerwowane",
                })

        return {
            "aktywne": zadania_aktywne,
            "zarezerwowane": zadania_zarezerwowane,
            "total_aktywne": len(zadania_aktywne),
            "total_w_kolejce": len(zadania_zarezerwowane),
        }
    except Exception as e:
        return {"blad": f"Nie można pobrać listy: {str(e)}", "aktywne": [], "zarezerwowane": []}
