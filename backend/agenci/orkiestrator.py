"""
NEXUS — Orkiestrator Multi-Agentowy (LangGraph)
================================================
Centralny mózg platformy NEXUS. Zarządza przepływem 5 agentów AI
w deterministycznym state machine z automatycznym retry i fallback.

Przepływ:
   Brief → Strateg → Pisarz → [Reżyser Głosu + Producent Wizualny] → Recenzent → Compositor

Specjalne właściwości:
- Równoległe wykonanie agentów Audio i Wizualia
- Auto-retry: jeśli wynik < 60, wróć do Pisarza (max 3 próby)
- Checkpoint: każdy krok zapisany — wznów po awarii
- Pełne śledzenie kosztów OpenAI
"""

import asyncio
import uuid
import time
import structlog
from typing import Literal
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from agenci.schematy import StanNEXUS
from agenci.strateg_tresci import strateg_tresci
from agenci.pisarz_scenariuszy import pisarz_scenariuszy
from agenci.rezyser_glosu import rezyser_glosu
from agenci.producent_wizualny import producent_wizualny
from agenci.recenzent_jakosci import recenzent_jakosci
from generacja.compositor import kompozytor
from konfiguracja import konf

logger = structlog.get_logger(__name__)


# ====================================================================
# WĘZEŁ: Równoległe wykonanie Audio + Wizualia
# ====================================================================

async def producja_rownolegle(stan: StanNEXUS) -> dict:
    """
    Węzeł równoległy: uruchamia Reżysera Głosu i Producenta Wizualnego
    jednocześnie (oszczędność czasu ~50%).
    """
    log = logger.bind(wezel="produkcja_rownolegla")
    log.info("Uruchamiam równoległą produkcję audio + wizualia")

    wyniki = await asyncio.gather(
        rezyser_glosu(stan),
        producent_wizualny(stan),
        return_exceptions=True
    )

    scalony = {}
    for wynik in wyniki:
        if isinstance(wynik, Exception):
            log.error("Błąd w równoległej produkcji", blad=str(wynik))
            scalony.setdefault("bledy", []).append(str(wynik))
        elif isinstance(wynik, dict):
            for klucz, wartosc in wynik.items():
                if klucz == "bledy":
                    scalony.setdefault("bledy", []).extend(wartosc if isinstance(wartosc, list) else [wartosc])
                elif klucz == "koszt_calkowity_usd":
                    scalony[klucz] = scalony.get(klucz, 0.0) + wartosc
                else:
                    scalony[klucz] = wartosc

    return scalony


# ====================================================================
# ROUTING — Decyzje warunkowe
# ====================================================================

def routing_po_recenzji(
    stan: StanNEXUS,
) -> Literal["compositor", "pisarz_scenariuszy", "koniec_z_bledem"]:
    """
    Routing po recenzji jakości:
    - zatwierdzone + iteracje OK → compositor
    - nie zatwierdzone + < maks prób → pisarz_scenariuszy (retry)
    - za dużo iteracji → koniec_z_bledem
    """
    ocena = stan.get("ocena_jakosci")
    iteracja = stan.get("iteracja", 0)

    if ocena and ocena.get("zatwierdzone", False):
        logger.info("Routing → compositor", wynik=ocena.get("wynik_ogolny"))
        return "compositor"
    elif iteracja >= konf.MAKS_PONOWNYCH_PROB:
        logger.warning("Routing → koniec (za dużo prób)", iteracja=iteracja)
        return "koniec_z_bledem"
    else:
        logger.info("Routing → pisarz (retry)", iteracja=iteracja)
        return "pisarz_scenariuszy"


def routing_po_strategii(
    stan: StanNEXUS,
) -> Literal["pisarz_scenariuszy", "koniec_z_bledem"]:
    """Routing po strategii: sukces → pisarz, błąd → koniec."""
    if stan.get("plan_tresci"):
        return "pisarz_scenariuszy"
    return "koniec_z_bledem"


# ====================================================================
# WĘZEŁ: Koniec z błędem (fallback)
# ====================================================================

async def koniec_z_bledem(stan: StanNEXUS) -> dict:
    """Węzeł końcowy gdy przekroczono limity lub wystąpił krytyczny błąd."""
    logger.error("Pipeline zakończony z błędem", bledy=stan.get("bledy", []))
    return {
        "krok_aktualny": "blad_krytyczny",
        "metadane": {
            **stan.get("metadane", {}),
            "status": "blad",
            "komunikat": "Nie udało się wygenerować wideo po 3 próbach",
        }
    }


# ====================================================================
# BUDOWA GRAFU LANGGRAPH
# ====================================================================

def zbuduj_graf_nexus() -> StateGraph:
    """
    Buduje i zwraca skompilowany graf LangGraph dla NEXUS.

    Graf reprezentuje cały pipeline produkcji wideo:
    START → strateg → pisarz → [audio + wizualia] → recenzent → compositor → END
    """
    graf = StateGraph(StanNEXUS)

    # Dodaj wszystkie węzły
    graf.add_node("strateg_tresci", strateg_tresci)
    graf.add_node("pisarz_scenariuszy", pisarz_scenariuszy)
    graf.add_node("produkcja_rownolegla", producja_rownolegle)
    graf.add_node("recenzent_jakosci", recenzent_jakosci)
    graf.add_node("compositor", kompozytor)
    graf.add_node("koniec_z_bledem", koniec_z_bledem)

    # Punkt startowy
    graf.add_edge(START, "strateg_tresci")

    # Routing po strategii
    graf.add_conditional_edges(
        "strateg_tresci",
        routing_po_strategii,
        {
            "pisarz_scenariuszy": "pisarz_scenariuszy",
            "koniec_z_bledem": "koniec_z_bledem",
        }
    )

    # Pisarz → Równoległa produkcja
    graf.add_edge("pisarz_scenariuszy", "produkcja_rownolegla")

    # Równoległa produkcja → Recenzent
    graf.add_edge("produkcja_rownolegla", "recenzent_jakosci")

    # Recenzent → Routing (zatwierdź / popraw / błąd)
    graf.add_conditional_edges(
        "recenzent_jakosci",
        routing_po_recenzji,
        {
            "compositor": "compositor",
            "pisarz_scenariuszy": "pisarz_scenariuszy",
            "koniec_z_bledem": "koniec_z_bledem",
        }
    )

    # Compositor → Koniec
    graf.add_edge("compositor", END)

    # Koniec z błędem → END
    graf.add_edge("koniec_z_bledem", END)

    return graf


# ====================================================================
# GŁÓWNA KLASA ORKIESTRATORA
# ====================================================================

class OrkiestratorNEXUS:
    """
    Główny orkiestrator pipeline'u wideo NEXUS.

    Przykład użycia:
        ork = OrkiestratorNEXUS()
        wynik = await ork.generuj_wideo(
            brief="Wideo o tym, jak zimne prysznice zwiększają testosteron",
            platforma=["tiktok", "youtube"],
            marka={"nazwa": "FitLife", "ton": "energiczny", "kolory": "niebieski, biały"}
        )
    """

    def __init__(self):
        self._saver = MemorySaver()
        self._graf = zbuduj_graf_nexus()
        self._app = self._graf.compile(checkpointer=self._saver)
        self._log = logger.bind(komponent="OrkiestratorNEXUS")
        self._log.info("Orkiestrator NEXUS zainicjalizowany")

    async def generuj_wideo(
        self,
        brief: str,
        platforma: list[str] | None = None,
        marka: dict | None = None,
        kontekst_marki: str = "",
    ) -> dict:
        """
        Główna metoda — generuje pełne wideo od briefu do gotowego pliku.

        Args:
            brief: Opis wideo (np. "Wideo o zaletach medytacji")
            platforma: Lista platform ["tiktok", "youtube", "instagram"]
            marka: Profil marki {"nazwa": "...", "ton": "...", "styl": "..."}
            kontekst_marki: Dodatkowy kontekst RAG marki

        Returns:
            Słownik z wynikami: wideo, oceny, koszty, czas
        """
        sesja_id = str(uuid.uuid4())[:8]
        czas_start = time.time()

        self._log.info(
            "Rozpoczynam generację wideo",
            sesja_id=sesja_id,
            brief_dl=len(brief),
            platforma=platforma or ["tiktok", "youtube"],
        )

        # Stan początkowy
        stan_poczatkowy: StanNEXUS = {
            "brief": brief,
            "marka": marka or {},
            "kontekst_marki": kontekst_marki,
            "platforma": platforma or ["tiktok", "youtube"],
            "plan_tresci": None,
            "scenariusz": None,
            "audio": None,
            "wizualia": None,
            "ocena_jakosci": None,
            "ocena_wiralnosci": None,
            "wideo": None,
            "krok_aktualny": "start",
            "iteracja": 0,
            "bledy": [],
            "metadane": {
                "sesja_id": sesja_id,
                "status": "w_trakcie",
                "czas_start": czas_start,
            },
            "koszt_calkowity_usd": 0.0,
            "czas_generacji_s": 0.0,
        }

        config = {"configurable": {"thread_id": sesja_id}}

        try:
            # Uruchom pipeline
            wynik_koncowy = None
            async for zdarzenie in self._app.astream(stan_poczatkowy, config=config):
                for wezel, dane in zdarzenie.items():
                    self._log.info(
                        "Postęp pipeline",
                        wezel=wezel,
                        krok=dane.get("krok_aktualny", "?"),
                        koszt=round(dane.get("koszt_calkowity_usd", 0), 4)
                    )
                    wynik_koncowy = dane

            czas_calkowity = time.time() - czas_start

            # Pobierz finalny stan
            stan_finalny = self._app.get_state(config)
            stan_wartosci = stan_finalny.values if hasattr(stan_finalny, 'values') else {}

            self._log.info(
                "Generacja zakończona",
                sesja_id=sesja_id,
                czas_s=round(czas_calkowity, 1),
                koszt_usd=round(stan_wartosci.get("koszt_calkowity_usd", 0.0), 4),
                nwv=stan_wartosci.get("ocena_wiralnosci", {}).get("wynik_nwv", "?"),
            )

            return {
                "sesja_id": sesja_id,
                "status": "sukces" if stan_wartosci.get("wideo") else "czesciowy",
                "wideo": stan_wartosci.get("wideo"),
                "scenariusz": stan_wartosci.get("scenariusz"),
                "audio": stan_wartosci.get("audio"),
                "wizualia": stan_wartosci.get("wizualia"),
                "ocena_jakosci": stan_wartosci.get("ocena_jakosci"),
                "ocena_wiralnosci": stan_wartosci.get("ocena_wiralnosci"),
                "plan_tresci": stan_wartosci.get("plan_tresci"),
                "bledy": stan_wartosci.get("bledy", []),
                "koszt_usd": round(stan_wartosci.get("koszt_calkowity_usd", 0.0), 4),
                "czas_generacji_s": round(czas_calkowity, 1),
                "iteracje": stan_wartosci.get("iteracja", 1),
            }

        except Exception as e:
            czas_calkowity = time.time() - czas_start
            self._log.error("Krytyczny błąd orkiestratora", blad=str(e), sesja_id=sesja_id)
            return {
                "sesja_id": sesja_id,
                "status": "blad",
                "blad": str(e),
                "koszt_usd": 0.0,
                "czas_generacji_s": round(czas_calkowity, 1),
            }

    def pobierz_stan_sesji(self, sesja_id: str) -> dict:
        """Pobiera aktualny stan sesji (do monitorowania postępu)."""
        config = {"configurable": {"thread_id": sesja_id}}
        try:
            stan = self._app.get_state(config)
            return {
                "sesja_id": sesja_id,
                "krok": stan.values.get("krok_aktualny", "nieznany"),
                "iteracja": stan.values.get("iteracja", 0),
                "koszt_usd": round(stan.values.get("koszt_calkowity_usd", 0.0), 4),
                "bledy": stan.values.get("bledy", []),
            }
        except Exception:
            return {"sesja_id": sesja_id, "status": "nie_znaleziono"}


# Singleton orkiestratora
_orkiestrator_instancja: OrkiestratorNEXUS | None = None


def pobierz_orkiestratora() -> OrkiestratorNEXUS:
    """Zwraca singleton orkiestratora."""
    global _orkiestrator_instancja
    if _orkiestrator_instancja is None:
        _orkiestrator_instancja = OrkiestratorNEXUS()
    return _orkiestrator_instancja
