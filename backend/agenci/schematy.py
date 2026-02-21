"""
NEXUS — Schematy Stanu Multi-Agentowego
========================================
Definicje TypedDict dla stanu przepływu LangGraph.
Każde pole dokumentuje, który agent je wypełnia.
"""

from typing import TypedDict, Optional, List, Dict, Any, Annotated
from operator import add


class ScenariuszScena(TypedDict):
    """Reprezentuje jedną scenę w wideo."""
    numer: int
    czas_start: float       # w sekundach
    czas_koniec: float
    opis_wizualny: str      # prompt dla DALL-E 3
    tekst_narracji: str     # tekst do synteza mowy
    tekst_na_ekranie: str   # napisy na wideo
    emocja: str             # radość | zaskoczenie | napięcie | inspiracja
    tempo: str              # wolne | normalne | szybkie


class PlanTresci(TypedDict):
    """Strategiczny plan treści — wypełnia Strateg Treści."""
    tytul: str
    temat: str
    platforma_docelowa: List[str]   # tiktok | youtube | instagram
    dlugosc_sekund: int
    typ_haka: str                   # wzorzec | ciekawość | szok | wartość | społeczny
    hak_wizualny: str
    hak_tekstowy: str
    hak_werbalny: str
    luk_emocjonalny: List[str]      # sekwencja emocji
    styl_wizualny: str
    ton_glosu: str
    hashtagi: List[str]
    przewidywane_zaangazowanie: float  # 0.0 - 1.0


class ScenariuszWideo(TypedDict):
    """Gotowy scenariusz — wypełnia Pisarz Scenariuszy."""
    tytul: str
    streszczenie: str
    sceny: List[ScenariuszScena]
    hook_otwierający: str
    cta: str                        # Call to Action
    calkowity_czas: float
    liczba_slow: int
    wynik_zaangazowania: float      # 0.0 - 1.0 przewidywany


class AudioWideo(TypedDict):
    """Wygenerowane audio — wypełnia Reżyser Głosu."""
    sciezka_pliku: str
    czas_trwania: float
    jezyk: str
    glos: str
    format: str                     # mp3 | opus
    transkrypcja: str
    segmenty: List[Dict]            # [{start, end, text}]


class ObrazSceny(TypedDict):
    """Pojedynczy obraz sceny — wypełnia Producent Wizualny."""
    numer_sceny: int
    sciezka_pliku: str
    prompt_uzyty: str
    rozdzielczosc: str
    format: str


class WizualiaWideo(TypedDict):
    """Wszystkie obrazy dla wideo — wypełnia Producent Wizualny."""
    obrazy: List[ObrazSceny]
    styl_wizualny: str
    paleta_kolorow: str
    liczba_obrazow: int


class OcenaJakosci(TypedDict):
    """Ocena jakości — wypełnia Recenzent Jakości."""
    wynik_ogolny: int               # 0-100
    wynik_haka: int                 # siła haka 0-100
    wynik_scenariusza: int          # jakość scenariusza 0-100
    wynik_wizualny: int             # jakość wizualna 0-100
    wynik_audio: int                # jakość audio 0-100
    slabe_punkty: List[str]         # co poprawić
    mocne_punkty: List[str]         # co jest dobre
    sugestie: List[str]             # propozycje poprawek
    zatwierdzone: bool


class OcenaWiralnosci(TypedDict):
    """Predykcja wiralności — wypełnia Silnik Wiralności."""
    wynik_nwv: int                  # NEXUS Viral Score 0-100
    wynik_haka: int
    wynik_zatrzymania: int
    wynik_udostepnialnosci: int
    wynik_platformy: Dict[str, int] # {tiktok: 85, youtube: 72, instagram: 68}
    odznaka: str                    # 🔥 Wysoki potencjał | ✅ Dobry | ⚠️ Przeciętny
    uzasadnienie: str
    wskazowki_optymalizacji: List[str]


class Wideo(TypedDict):
    """Finalny produkt — wypełnia Compositor."""
    sciezka_pliku: str
    miniatura_sciezka: str
    format: str                     # mp4
    rozdzielczosc: str
    czas_trwania: float
    rozmiar_mb: float
    wariant_tiktok: Optional[str]
    wariant_youtube: Optional[str]
    wariant_instagram: Optional[str]


# ====================================================================
# GŁÓWNY STAN PRZEPŁYWU NEXUS
# ====================================================================

class StanNEXUS(TypedDict):
    """
    Globalny stan przepływu LangGraph dla platformy NEXUS.

    Przepływ: Brief → Plan → Scenariusz → Audio+Wizualia → Recenzja → Wideo
    """
    # Wejście użytkownika
    brief: str                              # Opis wideo od użytkownika
    marka: Dict[str, Any]                   # Profil marki {nazwa, ton, styl}
    kontekst_marki: str                     # Kontekst RAG dla marki
    platforma: List[str]                    # Platformy docelowe

    # Wyjścia agentów
    plan_tresci: Optional[PlanTresci]
    scenariusz: Optional[ScenariuszWideo]
    audio: Optional[AudioWideo]
    wizualia: Optional[WizualiaWideo]
    ocena_jakosci: Optional[OcenaJakosci]
    ocena_wiralnosci: Optional[OcenaWiralnosci]
    wideo: Optional[Wideo]

    # Kontrola przepływu
    krok_aktualny: str                      # Aktualny krok
    iteracja: int                           # Liczba prób (max 3)
    bledy: Annotated[List[str], add]        # Akumulacja błędów
    metadane: Dict[str, Any]               # Metadane sesji

    # Koszt i czas
    koszt_calkowity_usd: float
    czas_generacji_s: float


# ====================================================================
# SCHEMATY SERYJNE — wieloodcinkowe narracje
# ====================================================================

class OdcinekSerii(TypedDict):
    """Metadane jednego odcinka w serii."""
    numer: int
    sesja_id: str
    tytul: str
    streszczenie: str
    haczyk_konca: str           # cliffhanger prowadzący do następnego odcinka
    status: str                 # oczekuje | generacja | gotowy | blad
    nwv: int                    # NEXUS Viral Score
    koszt_usd: float
    czas_generacji_s: float
    wideo: Optional[Wideo]
    ocena_wiralnosci: Optional[OcenaWiralnosci]


class SeriaNarracyjna(TypedDict):
    """Cała seria odcinków — wypełnia Historyk Serii."""
    seria_id: str
    tytul_serii: str
    temat: str
    gatunek: str                # historyczny | kryminalna | naukowy | biznesowy | etc.
    opis_serii: str
    platforma: List[str]
    styl_wizualny: str
    glos: str
    dlugosc_odcinka_s: int
    liczba_odcinkow: int
    luk_narracyjny: List[str]   # sekwencja motywów fabularnych
    odcinki: List[OdcinekSerii]
    status: str                 # planowanie | produkcja | ukonczona | wstrzymana
    data_utworzenia: str
    calkowity_koszt_usd: float


class StanSerii(TypedDict):
    """Stan przepływu dla generacji serii odcinków."""
    # Parametry serii
    temat: str
    tytul_serii: str
    liczba_odcinkow: int
    platforma: List[str]
    styl_wizualny: str
    glos: str
    dlugosc_odcinka_sekund: int

    # Rezultat planowania
    seria: Optional[SeriaNarracyjna]

    # Kontrola
    bledy: Annotated[List[str], add]
    metadane: Dict[str, Any]
