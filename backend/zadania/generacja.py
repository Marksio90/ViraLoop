"""
NEXUS — Zadanie Celery: Generacja Wideo
========================================
Background task uruchamiający cały pipeline multi-agentowy.

Flow:
1. API przyjmuje brief → tworzy zadanie Celery → zwraca task_id
2. Celery uruchamia pipeline w tle
3. Na każdym etapie publikuje postęp do Redis pub/sub
4. Frontend czyta postęp przez WebSocket LUB polling

Kanał Redis dla postępu: nexus:progress:{sesja_id}
"""

import asyncio
import json
import time
import structlog
from celery import Task

from celery_app import celery_app

logger = structlog.get_logger(__name__)


class ZadanieZPostepem(Task):
    """Bazowa klasa zadania z obsługą postępu."""

    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("Zadanie Celery nie powiodło się", task_id=task_id, blad=str(exc))

    def on_success(self, retval, task_id, args, kwargs):
        logger.info("Zadanie Celery zakończone", task_id=task_id)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning("Ponawiam zadanie Celery", task_id=task_id, blad=str(exc))


def opublikuj_postep(redis_url: str, sesja_id: str, postep: dict) -> None:
    """Publikuje postęp do Redis pub/sub."""
    try:
        import redis
        r = redis.from_url(redis_url)
        kanal = f"nexus:progress:{sesja_id}"
        r.publish(kanal, json.dumps(postep, ensure_ascii=False))
        # Zapisz stan dla pollingu
        r.setex(f"nexus:stan:{sesja_id}", 86400, json.dumps(postep, ensure_ascii=False))
    except Exception as e:
        logger.warning("Błąd publikacji postępu", blad=str(e))


@celery_app.task(
    bind=True,
    base=ZadanieZPostepem,
    name="zadania.generacja.generuj_wideo_task",
    max_retries=2,
    default_retry_delay=15,
)
def generuj_wideo_task(
    self,
    sesja_id: str,
    brief: str,
    platforma: list,
    marka: dict,
    kontekst_marki: str = "",
) -> dict:
    """
    Główne zadanie Celery: pełny pipeline generacji wideo.

    Args:
        sesja_id: Unikalny ID sesji
        brief: Opis wideo
        platforma: Platformy docelowe
        marka: Profil marki
        kontekst_marki: Kontekst RAG

    Returns:
        Słownik z wynikami generacji
    """
    from konfiguracja import konf

    log = logger.bind(task_id=self.request.id, sesja_id=sesja_id)
    log.info("Celery: rozpoczynam generację wideo")

    def postep(krok: str, procent: int, wiadomosc: str):
        """Aktualizuje postęp i publikuje do Redis."""
        self.update_state(
            state="PROGRESS",
            meta={
                "sesja_id": sesja_id,
                "krok": krok,
                "procent": procent,
                "wiadomosc": wiadomosc,
            }
        )
        opublikuj_postep(konf.REDIS_URL, sesja_id, {
            "sesja_id": sesja_id,
            "krok": krok,
            "procent": procent,
            "wiadomosc": wiadomosc,
            "timestamp": time.time(),
        })
        log.info(f"[{procent}%] {krok}: {wiadomosc}")

    try:
        postep("start", 0, "Pipeline uruchomiony")

        # Import tutaj aby uniknąć circular imports
        from agenci.orkiestrator import OrkiestratorNEXUS

        orkiestrator = OrkiestratorNEXUS()

        # Uruchom async pipeline w pętli eventów Celery
        postep("strateg", 10, "Strateg Treści analizuje brief...")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Monkey-patch postęp do pipeline
            wynik = loop.run_until_complete(
                _uruchom_z_postepem(
                    orkiestrator,
                    sesja_id=sesja_id,
                    brief=brief,
                    platforma=platforma,
                    marka=marka,
                    kontekst_marki=kontekst_marki,
                    callback_postepu=postep,
                )
            )
        finally:
            loop.close()

        postep("gotowe", 100, "Wideo wygenerowane!")

        return wynik

    except Exception as exc:
        log.error("Błąd zadania Celery", blad=str(exc))
        opublikuj_postep(konf.REDIS_URL, sesja_id, {
            "sesja_id": sesja_id,
            "krok": "blad",
            "procent": 0,
            "wiadomosc": f"Błąd: {str(exc)}",
            "timestamp": time.time(),
        })
        raise self.retry(exc=exc, countdown=15)


async def _uruchom_z_postepem(
    orkiestrator,
    sesja_id: str,
    brief: str,
    platforma: list,
    marka: dict,
    kontekst_marki: str,
    callback_postepu,
) -> dict:
    """
    Uruchamia pipeline orkiestratora z callbackami postępu.
    """
    # Uruchom pipeline (orkiestrator streamuje zdarzenia)
    from konfiguracja import konf
    import redis as redis_sync

    r = redis_sync.from_url(konf.REDIS_URL)

    ETAPY_PIPELINE = {
        "strateg_tresci": (15, "Strateg Treści tworzy plan..."),
        "pisarz_scenariuszy": (30, "Pisarz Scenariuszy pisze scenariusz..."),
        "produkcja_rownolegla": (55, "Reżyser Głosu + Producent Wizualny pracują równolegle..."),
        "recenzent_jakosci": (80, "Recenzent Jakości ocenia wideo..."),
        "compositor": (92, "Compositor scala wideo MP4..."),
    }

    # Stream zdarzeń LangGraph
    config = {"configurable": {"thread_id": sesja_id}}
    stan_poczatkowy = {
        "brief": brief,
        "marka": marka,
        "kontekst_marki": kontekst_marki,
        "platforma": platforma,
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
        "metadane": {"sesja_id": sesja_id, "status": "w_trakcie"},
        "koszt_calkowity_usd": 0.0,
        "czas_generacji_s": 0.0,
    }

    wynik_koncowy = None
    async for zdarzenie in orkiestrator._app.astream(stan_poczatkowy, config=config):
        for wezel, dane in zdarzenie.items():
            if wezel in ETAPY_PIPELINE:
                procent, wiadomosc = ETAPY_PIPELINE[wezel]
                callback_postepu(wezel, procent, wiadomosc)
            wynik_koncowy = dane

    # Pobierz finalny stan
    stan_finalny = orkiestrator._app.get_state(config)
    stan_wartosci = stan_finalny.values if hasattr(stan_finalny, "values") else {}

    import time as t
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
        "czas_generacji_s": round(stan_wartosci.get("czas_generacji_s", 0.0), 1),
        "iteracje": stan_wartosci.get("iteracja", 1),
    }


@celery_app.task(
    name="zadania.generacja.analizuj_wiralnosc_task",
    max_retries=1,
)
def analizuj_wiralnosc_task(brief: str, platforma: list, dlugosc_sekund: int) -> dict:
    """Zadanie analizy wiralności (szybkie, ~5s)."""
    from analityka.silnik_wiralnosci import oblicz_nwv_heurystyczny

    plan_mock = {
        "temat": brief,
        "platforma_docelowa": platforma,
        "dlugosc_sekund": dlugosc_sekund,
        "hak_wizualny": "",
        "hak_tekstowy": "",
        "typ_haka": "luk_ciekawosci",
    }

    # Synchroniczna analiza (heurystyczna)
    nwv = oblicz_nwv_heurystyczny(plan_mock)

    return {
        "wynik_nwv": nwv,
        "odznaka": "🔥 Wysoki potencjał" if nwv >= 85 else "✅ Dobry content" if nwv >= 60 else "⚠️ Optymalizuj",
        "wynik_haka": nwv,
        "wynik_zatrzymania": nwv - 5,
        "wynik_udostepnialnosci": nwv - 8,
        "wynik_platformy": {p: nwv for p in platforma},
        "uzasadnienie": "Szybka analiza heurystyczna",
        "wskazowki_optymalizacji": [],
    }
