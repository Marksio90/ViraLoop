"""
ViraLoop – Router API projektów

Zarządza projektami wideo: tworzenie, edycja, współpraca i eksport.
"""

from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class NawyProjekt(BaseModel):
    """Dane do utworzenia nowego projektu."""

    nazwa: str = Field(..., min_length=3, max_length=100, description="Nazwa projektu")
    opis: str | None = Field(default=None, max_length=500, description="Opis projektu")
    platforma_docelowa: list[str] = Field(
        default=["youtube"],
        description="Platformy docelowe publikacji",
    )
    jezyki: list[str] = Field(
        default=["pl"],
        description="Języki treści (wielojęzyczny pipeline)",
    )


class Projekt(BaseModel):
    """Model projektu wideo."""

    id: UUID
    nazwa: str
    opis: str | None
    platforma_docelowa: list[str]
    jezyki: list[str]
    status: str
    liczba_wideo: int
    wspolpracownicy: list[str]


@router.post("/", response_model=Projekt, summary="Utwórz nowy projekt")
async def utworz_projekt(dane: NawyProjekt):
    """
    Tworzy nowy projekt wideo.

    Projekt grupuje powiązane wideo, udostępnia zasoby (głosy, szablony)
    i umożliwia współpracę w czasie rzeczywistym przez Liveblocks + Yjs.
    """
    return Projekt(
        id=uuid4(),
        nazwa=dane.nazwa,
        opis=dane.opis,
        platforma_docelowa=dane.platforma_docelowa,
        jezyki=dane.jezyki,
        status="aktywny",
        liczba_wideo=0,
        wspolpracownicy=[],
    )


@router.get("/", response_model=list[Projekt], summary="Lista projektów")
async def lista_projektow():
    """Zwraca listę projektów użytkownika."""
    # TODO: Implementacja z bazą danych
    return []


@router.get("/{id_projektu}", response_model=Projekt, summary="Szczegóły projektu")
async def pobierz_projekt(id_projektu: UUID):
    """Zwraca szczegóły projektu."""
    # TODO: Implementacja z bazą danych
    raise HTTPException(status_code=404, detail="Projekt nie znaleziony")


@router.delete("/{id_projektu}", summary="Usuń projekt")
async def usun_projekt(id_projektu: UUID):
    """Usuwa projekt i wszystkie powiązane zasoby."""
    return {"komunikat": f"Projekt {id_projektu} usunięty"}
