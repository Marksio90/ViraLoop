"""
ViraLoop — Trasy API: Serie Narracyjne
========================================
Endpointy do zarządzania serialami shortsy.

Endpointy:
- POST /api/v1/serie/generuj       — Zaplanuj i generuj serię odcinków
- GET  /api/v1/serie               — Lista wszystkich serii
- GET  /api/v1/serie/{seria_id}    — Szczegóły serii
- POST /api/v1/serie/{seria_id}/kontynuuj — Wygeneruj następny odcinek
- DELETE /api/v1/serie/{seria_id}  — Usuń serię
"""

import json
import asyncio
import structlog
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from konfiguracja import konf
from agenci.schematy import SeriaNarracyjna, StanSerii
from agenci.historyk_serii import zaplanuj_serie, generuj_brief_kontynuacji
from agenci.orkiestrator import pobierz_orkiestratora

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/serie", tags=["Serie"])

# Prosty cache serii w pliku JSON (production: Redis/PostgreSQL)
PLIK_SERII = Path(konf.SCIEZKA_TYMCZASOWA) / "serie.json"


def wczytaj_serie() -> dict[str, dict]:
    """Wczytuje bazę serii z pliku JSON."""
    if PLIK_SERII.exists():
        try:
            return json.loads(PLIK_SERII.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def zapisz_serie(serie: dict[str, dict]) -> None:
    """Zapisuje bazę serii do pliku JSON."""
    PLIK_SERII.parent.mkdir(parents=True, exist_ok=True)
    PLIK_SERII.write_text(
        json.dumps(serie, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ── SCHEMATY ŻĄDAŃ ──────────────────────────────────────────────────

class ZadanieGeneracjiSerii(BaseModel):
    """Żądanie wygenerowania nowej serii."""
    temat: str = Field(
        min_length=10,
        max_length=2000,
        description="Temat serii (np. 'Tajemnice Watykanu — ukryte archiwa')",
    )
    tytul_serii: str = Field(
        default="",
        max_length=200,
        description="Tytuł serii (opcjonalny — AI wygeneruje jeśli pusty)",
    )
    liczba_odcinkow: int = Field(
        default=5,
        ge=2,
        le=10,
        description="Liczba odcinków w serii (2-10)",
    )
    platforma: list[str] = Field(
        default=["tiktok", "youtube"],
        description="Platformy docelowe",
    )
    styl_wizualny: str = Field(
        default="kinowy",
        description="Styl wizualny: kinowy | dokumentalny | epicka | nowoczesny",
    )
    glos: str = Field(
        default="nova",
        description="Głos lektora: nova | alloy | echo | fable | onyx | shimmer",
    )
    dlugosc_odcinka_sekund: int = Field(
        default=60,
        ge=15,
        le=180,
        description="Długość odcinka w sekundach",
    )
    generuj_od_razu: bool = Field(
        default=True,
        description="Jeśli True: generuje pierwszy odcinek od razu",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "temat": "Sekrety Watykanu — co kryją archiwa papieskie",
                "liczba_odcinkow": 5,
                "platforma": ["tiktok", "youtube"],
                "styl_wizualny": "kinowy",
                "glos": "echo",
                "dlugosc_odcinka_sekund": 60,
                "generuj_od_razu": True,
            }
        }


class ZadanieKontynuacji(BaseModel):
    """Żądanie kontynuacji serii."""
    liczba_nowych_odcinkow: int = Field(default=1, ge=1, le=5)


# ── ENDPOINTY ───────────────────────────────────────────────────────

@router.post(
    "/generuj",
    summary="Generuj nową serię odcinków",
    description="""
Tworzy serię powiązanych odcinków shortsy.

Pipeline:
1. **Historyk Serii** planuje wszystkie odcinki z cliffhangerami
2. **Pierwszy odcinek** generowany od razu (jeśli generuj_od_razu=True)
3. Kolejne odcinki generowane przez endpoint /kontynuuj

Koszt: ~$0.001 za planowanie + ~$0.15 per odcinek
""",
)
async def generuj_serie(
    zadanie: ZadanieGeneracjiSerii,
    background_tasks: BackgroundTasks,
) -> dict:
    """Planuje i opcjonalnie generuje pierwszą serię odcinków."""
    log = logger.bind(endpoint="generuj_serie")
    log.info("Nowe zadanie serii", temat=zadanie.temat[:60])

    if not konf.OPENAI_API_KEY:
        raise HTTPException(503, detail="Brak klucza OPENAI_API_KEY")

    # Przygotuj stan
    stan: StanSerii = {
        "temat": zadanie.temat,
        "tytul_serii": zadanie.tytul_serii or zadanie.temat[:60],
        "liczba_odcinkow": zadanie.liczba_odcinkow,
        "platforma": zadanie.platforma,
        "styl_wizualny": zadanie.styl_wizualny,
        "glos": zadanie.glos,
        "dlugosc_odcinka_sekund": zadanie.dlugosc_odcinka_sekund,
        "seria": None,
        "bledy": [],
        "metadane": {"czas_start": datetime.now().isoformat()},
    }

    # Krok 1: Historyk Serii planuje serię
    wynik_planowania = await zaplanuj_serie(stan)

    if wynik_planowania.get("bledy"):
        raise HTTPException(500, detail=str(wynik_planowania["bledy"]))

    seria: SeriaNarracyjna = wynik_planowania["seria"]

    # Zapisz serię
    serie = wczytaj_serie()
    serie[seria["seria_id"]] = seria  # type: ignore[assignment]
    zapisz_serie(serie)

    # Krok 2 (opcjonalny): Generuj pierwszy odcinek
    pierwsze_wideo = None
    if zadanie.generuj_od_razu and seria["odcinki"]:
        pierwsza_sciezka = await _generuj_odcinek(seria, 1)
        if pierwsza_sciezka:
            pierwsze_wideo = pierwsza_sciezka

            # Aktualizuj status w bazie
            serie = wczytaj_serie()
            if seria["seria_id"] in serie:
                for od in serie[seria["seria_id"]]["odcinki"]:  # type: ignore[index]
                    if od["numer"] == 1:
                        od.update(pierwsze_wideo)
                        break
            zapisz_serie(serie)

    return {
        "seria_id": seria["seria_id"],
        "tytul_serii": seria["tytul_serii"],
        "gatunek": seria["gatunek"],
        "opis_serii": seria["opis_serii"],
        "liczba_odcinkow": seria["liczba_odcinkow"],
        "luk_narracyjny": seria["luk_narracyjny"],
        "odcinki": seria["odcinki"],
        "pierwszy_odcinek": pierwsze_wideo,
        "status": "produkcja" if zadanie.generuj_od_razu else "planowanie",
    }


async def _generuj_odcinek(seria: SeriaNarracyjna, numer: int) -> dict | None:
    """Wewnętrzna funkcja: generuje konkretny odcinek serii."""
    log = logger.bind(seria_id=seria["seria_id"], odcinek=numer)

    # Znajdź plan odcinka
    plan = next((od for od in seria["odcinki"] if od["numer"] == numer), None)
    if not plan:
        log.error("Brak planu odcinka")
        return None

    # Generuj brief kontynuacji
    brief = await generuj_brief_kontynuacji(seria, numer)

    # Uruchom główny pipeline
    orkiestrator = pobierz_orkiestratora()
    try:
        wynik = await orkiestrator.generuj_wideo(
            brief=brief,
            platforma=seria["platforma"],
            marka={
                "nazwa": seria["tytul_serii"],
                "ton": seria["gatunek"],
                "styl": seria["styl_wizualny"],
                "preferowany_glos": seria["glos"],
                "numer_odcinka": numer,
                "seria_id": seria["seria_id"],
            },
            kontekst_marki=seria["opis_serii"],
        )
    except Exception as e:
        log.error("Błąd generacji odcinka", blad=str(e))
        return None

    return {
        "sesja_id": wynik.get("sesja_id", ""),
        "status": "gotowy" if wynik.get("wideo") else "blad",
        "nwv": wynik.get("ocena_wiralnosci", {}).get("wynik_nwv", 0) if wynik.get("ocena_wiralnosci") else 0,
        "koszt_usd": wynik.get("koszt_usd", 0.0),
        "czas_generacji_s": wynik.get("czas_generacji_s", 0.0),
        "wideo": wynik.get("wideo"),
        "ocena_wiralnosci": wynik.get("ocena_wiralnosci"),
    }


@router.get(
    "",
    summary="Lista wszystkich serii",
)
async def lista_serii(
    status: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """Zwraca listę serii z opcjonalnym filtrem statusu."""
    serie = wczytaj_serie()

    wyniki = list(serie.values())

    if status:
        wyniki = [s for s in wyniki if s.get("status") == status]

    # Sortuj po dacie (najnowsze pierwsze)
    wyniki.sort(key=lambda s: s.get("data_utworzenia", ""), reverse=True)
    wyniki = wyniki[:limit]

    # Statystyki per seria
    for seria in wyniki:
        odcinki = seria.get("odcinki", [])
        seria["_stats"] = {
            "gotowych": sum(1 for o in odcinki if o.get("status") == "gotowy"),
            "wszystkich": len(odcinki),
            "avg_nwv": round(
                sum(o.get("nwv", 0) for o in odcinki if o.get("nwv", 0) > 0)
                / max(1, sum(1 for o in odcinki if o.get("nwv", 0) > 0)),
                1
            ),
        }

    return {
        "serie": wyniki,
        "total": len(serie),
    }


@router.get(
    "/{seria_id}",
    summary="Szczegóły serii",
)
async def pobierz_serie(seria_id: str) -> dict:
    """Pobiera pełne szczegóły serii wraz z odcinkami."""
    serie = wczytaj_serie()

    if seria_id not in serie:
        raise HTTPException(404, detail=f"Seria {seria_id} nie znaleziona")

    seria = serie[seria_id]

    # Sprawdź które wideo są dostępne
    for odcinek in seria.get("odcinki", []):
        sesja = odcinek.get("sesja_id", "")
        sciezka = Path(konf.SCIEZKA_WYJSCIOWA) / sesja / "wideo_glowne.mp4"
        odcinek["plik_dostepny"] = sciezka.exists() if sesja else False

    return seria


@router.post(
    "/{seria_id}/kontynuuj",
    summary="Generuj następny odcinek serii",
    description="Generuje kolejny nieukończony odcinek w serii.",
)
async def kontynuuj_serie(
    seria_id: str,
    zadanie: ZadanieKontynuacji,
    background_tasks: BackgroundTasks,
) -> dict:
    """Generuje następny odcinek (lub kilka) w istniejącej serii."""
    log = logger.bind(seria_id=seria_id)
    serie = wczytaj_serie()

    if seria_id not in serie:
        raise HTTPException(404, detail=f"Seria {seria_id} nie znaleziona")

    seria: SeriaNarracyjna = serie[seria_id]  # type: ignore[assignment]

    # Znajdź odcinki do wygenerowania
    oczekujace = [
        od for od in seria["odcinki"]
        if od["status"] in ("oczekuje", "blad")
    ][:zadanie.liczba_nowych_odcinkow]

    if not oczekujace:
        return {
            "wiadomosc": "Wszystkie odcinki już wygenerowane",
            "seria_id": seria_id,
            "wygenerowane": [],
        }

    wygenerowane = []

    for od in oczekujace:
        # Oznacz jako w trakcie
        od["status"] = "generacja"
        serie[seria_id] = seria  # type: ignore[index]
        zapisz_serie(serie)

        wynik = await _generuj_odcinek(seria, od["numer"])

        if wynik:
            od.update(wynik)
            wygenerowane.append({
                "numer": od["numer"],
                "tytul": od["tytul"],
                "sesja_id": wynik.get("sesja_id"),
                "status": "gotowy",
                "nwv": wynik.get("nwv", 0),
            })
        else:
            od["status"] = "blad"

        # Aktualizuj bazę po każdym odcinku
        serie = wczytaj_serie()
        seria = serie[seria_id]  # type: ignore[assignment]
        for idx, o in enumerate(seria["odcinki"]):
            if o["numer"] == od["numer"]:
                seria["odcinki"][idx] = od
                break
        serie[seria_id] = seria  # type: ignore[index]
        zapisz_serie(serie)

    # Aktualizuj status serii
    serie = wczytaj_serie()
    seria_aktualna = serie.get(seria_id, {})
    wszystkie_gotowe = all(
        o.get("status") == "gotowy"
        for o in seria_aktualna.get("odcinki", [])
    )
    if wszystkie_gotowe:
        seria_aktualna["status"] = "ukonczona"
        serie[seria_id] = seria_aktualna
        zapisz_serie(serie)

    log.info("Kontynuacja zakończona", wygenerowane=len(wygenerowane))
    return {
        "seria_id": seria_id,
        "wygenerowane": wygenerowane,
        "pozostale": len([o for o in seria_aktualna.get("odcinki", []) if o.get("status") == "oczekuje"]),
    }


@router.delete(
    "/{seria_id}",
    summary="Usuń serię",
)
async def usun_serie(seria_id: str) -> dict:
    """Usuwa serię z bazy (nie usuwa plików wideo)."""
    serie = wczytaj_serie()

    if seria_id not in serie:
        raise HTTPException(404, detail=f"Seria {seria_id} nie znaleziona")

    del serie[seria_id]
    zapisz_serie(serie)

    return {"wiadomosc": f"Seria {seria_id} usunięta", "seria_id": seria_id}


@router.get(
    "/{seria_id}/plan",
    summary="Plan narracyjny serii",
)
async def plan_serii(seria_id: str) -> dict:
    """Zwraca pełny plan narracyjny z cliffhangerami."""
    serie = wczytaj_serie()

    if seria_id not in serie:
        raise HTTPException(404, detail=f"Seria {seria_id} nie znaleziona")

    seria = serie[seria_id]

    return {
        "seria_id": seria_id,
        "tytul": seria.get("tytul_serii"),
        "gatunek": seria.get("gatunek"),
        "luk_narracyjny": seria.get("luk_narracyjny", []),
        "odcinki_plan": [
            {
                "numer": od["numer"],
                "tytul": od["tytul"],
                "streszczenie": od["streszczenie"],
                "haczyk_konca": od["haczyk_konca"],
                "status": od["status"],
            }
            for od in seria.get("odcinki", [])
        ],
    }
