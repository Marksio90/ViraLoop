"""
ViraLoop – Router API użytkownika

Zarządza kontami, uwierzytelnianiem, subskrypcjami i limitami kredytów.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr

router = APIRouter()


class DaneRejestracji(BaseModel):
    """Dane do rejestracji nowego konta."""

    email: EmailStr
    haslo: str = Field(..., min_length=8, description="Hasło (min. 8 znaków)")
    imie: str = Field(..., min_length=2, max_length=50)
    plan: str = Field(
        default="darmowy",
        description="Plan subskrypcji",
        examples=["darmowy", "tworca", "profesjonalny", "enterprise"],
    )


class ProfilUzytkownika(BaseModel):
    """Profil użytkownika."""

    id: str
    email: str
    imie: str
    plan: str
    kredyty_pozostale: int
    kredyty_lacznie: int
    data_odnowienia: str | None
    liczba_wideo: int


PLANY_SUBSKRYPCJI = {
    "darmowy": {
        "cena_pln": 0,
        "kredyty_miesiacznie": 10,
        "max_rozdzielczosc": "480p",
        "watermark": True,
        "uzycie_komercyjne": False,
    },
    "tworca": {
        "cena_pln": 29,
        "kredyty_miesiacznie": 100,
        "max_rozdzielczosc": "1080p",
        "watermark": False,
        "uzycie_komercyjne": True,
    },
    "profesjonalny": {
        "cena_pln": 99,
        "kredyty_miesiacznie": 500,
        "max_rozdzielczosc": "4K",
        "watermark": False,
        "uzycie_komercyjne": True,
    },
    "enterprise": {
        "cena_pln": 2000,
        "kredyty_miesiacznie": -1,  # nielimitowane
        "max_rozdzielczosc": "4K@60fps",
        "watermark": False,
        "uzycie_komercyjne": True,
        "api_access": True,
        "sso": True,
    },
}


@router.post("/rejestracja", response_model=ProfilUzytkownika, summary="Rejestracja konta")
async def rejestruj(dane: DaneRejestracji):
    """
    Rejestruje nowe konto użytkownika.

    Obsługiwane plany:
    - Darmowy: 0 zł/mies, 10 kredytów, 480p + watermark
    - Twórca: 29 zł/mies, 100 kredytów, 1080p
    - Profesjonalny: 99 zł/mies, 500 kredytów, 4K
    - Enterprise: od 2000 zł/mies, nielimitowane, 4K@60fps + API
    """
    if dane.plan not in PLANY_SUBSKRYPCJI:
        raise HTTPException(
            status_code=400,
            detail=f"Nieznany plan: {dane.plan}. Dostępne: {list(PLANY_SUBSKRYPCJI.keys())}",
        )

    plan = PLANY_SUBSKRYPCJI[dane.plan]

    # TODO: Zapisz użytkownika w bazie danych (z haszowaniem hasła bcrypt)
    return ProfilUzytkownika(
        id="usr_" + "x" * 20,
        email=dane.email,
        imie=dane.imie,
        plan=dane.plan,
        kredyty_pozostale=plan["kredyty_miesiacznie"],
        kredyty_lacznie=plan["kredyty_miesiacznie"],
        data_odnowienia=None,
        liczba_wideo=0,
    )


@router.get("/ja", response_model=ProfilUzytkownika, summary="Mój profil")
async def pobierz_profil():
    """Zwraca profil aktualnie zalogowanego użytkownika."""
    # TODO: Implementacja z JWT authentication
    raise HTTPException(status_code=401, detail="Wymagane uwierzytelnienie")


@router.get("/plany", summary="Lista planów subskrypcji")
async def lista_planow():
    """Zwraca szczegóły wszystkich dostępnych planów subskrypcji."""
    return {"plany": PLANY_SUBSKRYPCJI}
