"""
ViraLoop – Router API wideo

Obsługuje żądania generowania, zarządzania i renderowania wideo.
"""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.generation.video.silnik_generacji import SilnikGeneracjiWideo
from backend.orchestration.pipeline_wideo import PipelineWideo

router = APIRouter()


# ---- Modele danych ----


class ZadanieGeneracjiWideo(BaseModel):
    """Żądanie wygenerowania nowego wideo."""

    opis: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Opis treści wideo do wygenerowania",
        examples=["Dynamiczny film o wschodzie słońca nad Tatrami z epicką muzyką"],
    )
    model: str = Field(
        default="kling-3.0",
        description="Model generowania wideo",
        examples=["kling-3.0", "veo-3.1", "runway-gen-4.5", "wan2.2"],
    )
    rozdzielczosc: str = Field(
        default="1080p",
        description="Docelowa rozdzielczość wideo",
        examples=["480p", "720p", "1080p", "4K"],
    )
    czas_trwania: int = Field(
        default=8,
        ge=3,
        le=60,
        description="Czas trwania wideo w sekundach",
    )
    jezyk: str = Field(
        default="pl",
        description="Język treści (kod ISO 639-1)",
        examples=["pl", "en", "de", "fr"],
    )
    styl: str = Field(
        default="kinematograficzny",
        description="Styl wizualny wideo",
        examples=["kinematograficzny", "animacja", "dokumentalny", "reklamowy"],
    )
    audio: bool = Field(
        default=True,
        description="Czy generować zsynchronizowane audio",
    )
    priorytet: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Priorytet zadania (1=niski, 10=pilny)",
    )


class OdpowiedzGeneracji(BaseModel):
    """Odpowiedź po zleceniu generacji wideo."""

    id_zadania: UUID
    status: str
    szacowany_czas_sekund: int
    komunikat: str


class StatusWideo(BaseModel):
    """Status wygenerowanego wideo."""

    id_zadania: UUID
    status: str  # oczekiwanie | przetwarzanie | gotowe | blad
    postep_procent: float
    url_wideo: str | None
    url_miniatury: str | None
    metadane: dict | None
    blad: str | None


# ---- Endpointy ----


@router.post(
    "/generuj",
    response_model=OdpowiedzGeneracji,
    summary="Zlecenie generacji wideo",
    description=(
        "Zleca asynchroniczne wygenerowanie nowego wideo AI. "
        "Zwraca ID zadania, które można monitorować przez endpoint /status/{id}."
    ),
)
async def generuj_wideo(
    zadanie: ZadanieGeneracjiWideo,
    zadania_w_tle: BackgroundTasks,
    silnik: Annotated[SilnikGeneracjiWideo, Depends(SilnikGeneracjiWideo)],
):
    """
    Generuje wideo AI na podstawie opisu tekstowego.

    Pipeline:
    1. Walidacja żądania i limitu kredytów użytkownika
    2. Optymalizacja promptu przez DSPy/MIPROv2
    3. Wybór optymalnego modelu (koszt vs jakość)
    4. Generowanie wideo przez odpowiednie API
    5. Post-processing (kompresja, watermark, C2PA)
    6. Zapis w bibliotece użytkownika
    """
    id_zadania = uuid4()

    # Sprawdź dostępność modelu i szacowany koszt
    szacowany_czas = silnik.szacuj_czas(zadanie.model, zadanie.czas_trwania)

    # Uruchom pipeline w tle
    zadania_w_tle.add_task(
        PipelineWideo.uruchom,
        id_zadania=id_zadania,
        parametry=zadanie.model_dump(),
    )

    return OdpowiedzGeneracji(
        id_zadania=id_zadania,
        status="oczekiwanie",
        szacowany_czas_sekund=szacowany_czas,
        komunikat=f"Wideo zostało zlecone do generacji przez model {zadanie.model}",
    )


@router.get(
    "/status/{id_zadania}",
    response_model=StatusWideo,
    summary="Status generacji wideo",
)
async def pobierz_status_wideo(id_zadania: UUID):
    """Zwraca aktualny status generacji wideo."""
    status = await PipelineWideo.pobierz_status(id_zadania)
    if status is None:
        raise HTTPException(
            status_code=404,
            detail=f"Zadanie {id_zadania} nie zostało znalezione",
        )
    return status


@router.get(
    "/lista",
    summary="Lista wygenerowanych wideo",
    description="Zwraca paginowaną listę wideo użytkownika posortowanych według daty.",
)
async def lista_wideo(
    strona: int = Query(default=1, ge=1, description="Numer strony"),
    na_strone: int = Query(default=20, ge=1, le=100, description="Ilość wyników na stronę"),
    status: str | None = Query(default=None, description="Filtr po statusie"),
    model: str | None = Query(default=None, description="Filtr po modelu generacji"),
):
    """Zwraca paginowaną listę wideo użytkownika."""
    # TODO: Implementacja z bazą danych
    return {
        "strona": strona,
        "na_strone": na_strone,
        "lacznie": 0,
        "wideo": [],
    }


@router.delete(
    "/{id_wideo}",
    summary="Usuń wideo",
)
async def usun_wideo(id_wideo: UUID):
    """Usuwa wideo z biblioteki użytkownika."""
    # TODO: Implementacja usuwania z bazy i storage
    return {"komunikat": f"Wideo {id_wideo} zostało usunięte"}


@router.post(
    "/{id_wideo}/publikuj",
    summary="Publikuj wideo na platformach",
    description="Publikuje wygenerowane wideo na wskazanych platformach społecznościowych.",
)
async def publikuj_wideo(
    id_wideo: UUID,
    platformy: list[str] = Query(
        description="Platformy docelowe",
        examples=[["youtube", "tiktok", "instagram"]],
    ),
):
    """Publikuje wideo na wskazanych platformach z odpowiednimi metadanymi."""
    if not platformy:
        raise HTTPException(
            status_code=400,
            detail="Nie podano żadnej platformy docelowej",
        )

    dozwolone_platformy = {"youtube", "tiktok", "instagram", "facebook"}
    nieprawidlowe = set(platformy) - dozwolone_platformy
    if nieprawidlowe:
        raise HTTPException(
            status_code=400,
            detail=f"Nieznane platformy: {nieprawidlowe}. Dostępne: {dozwolone_platformy}",
        )

    # TODO: Implementacja publikacji przez API każdej platformy
    return {
        "komunikat": "Publikacja zainicjowana",
        "id_wideo": str(id_wideo),
        "platformy": platformy,
        "status": "w_kolejce",
    }
