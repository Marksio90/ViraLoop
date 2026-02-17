"""
ViraLoop – Zarządzanie połączeniami z bazami danych

Inicjalizuje i zamyka połączenia z ClickHouse, Qdrant i Redis
przy starcie/zatrzymaniu aplikacji FastAPI.
"""

import structlog

from backend.analytics.clickhouse.klient_clickhouse import KlientClickHouse
from backend.analytics.qdrant.dna_wideo import BazaDnaWideo
from backend.utils.konfiguracja import ustawienia

logger = structlog.get_logger(__name__)

# Globalne instancje klientów
_clickhouse: KlientClickHouse | None = None
_qdrant: BazaDnaWideo | None = None


async def inicjalizuj_polaczenia() -> None:
    """Inicjalizuje wszystkie połączenia z bazami danych."""
    global _clickhouse, _qdrant

    # ClickHouse
    _clickhouse = KlientClickHouse(
        host=ustawienia.CLICKHOUSE_HOST,
        port=ustawienia.CLICKHOUSE_PORT,
        baza_danych=ustawienia.CLICKHOUSE_DB,
        uzytkownik=ustawienia.CLICKHOUSE_USER,
        haslo=ustawienia.CLICKHOUSE_PASSWORD,
    )
    await _clickhouse.polacz()
    await _clickhouse.inicjalizuj_schemat()

    # Qdrant
    _qdrant = BazaDnaWideo(url=ustawienia.QDRANT_URL)
    await _qdrant.polacz()

    logger.info("Wszystkie połączenia z bazami danych nawiązane")


async def zamknij_polaczenia() -> None:
    """Zamyka wszystkie połączenia z bazami danych."""
    global _clickhouse, _qdrant

    if _clickhouse and _clickhouse._klient:
        try:
            _clickhouse._klient.close()
        except Exception:
            pass

    if _qdrant and _qdrant._klient:
        try:
            await _qdrant._klient.close()
        except Exception:
            pass

    logger.info("Połączenia z bazami danych zamknięte")


def pobierz_clickhouse() -> KlientClickHouse:
    """Dependency injection dla FastAPI – zwraca klienta ClickHouse."""
    if _clickhouse is None:
        raise RuntimeError("ClickHouse nie został zainicjalizowany")
    return _clickhouse


def pobierz_qdrant() -> BazaDnaWideo:
    """Dependency injection dla FastAPI – zwraca klienta Qdrant."""
    if _qdrant is None:
        raise RuntimeError("Qdrant nie został zainicjalizowany")
    return _qdrant
