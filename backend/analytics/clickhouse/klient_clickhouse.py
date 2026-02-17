"""
ViraLoop – Klient ClickHouse

ClickHouse v26.1 ($6.35B wycena) przetwarza setki milionów wierszy/sekundę
z sub-sekundowymi zapytaniami nad miliardami metryk wideo.

Konfiguracja tabel:
- MergeTree ORDER BY (video_id, timestamp) – wydajne zapytania po wideo/czasie
- AggregatingMergeTree materialized views – wstępnie obliczone metryki
- LowCardinality(String) – kompresja dla pól kategorycznych (platforma, model, status)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# Schematy tabel ClickHouse
SCHEMATY_TABEL = {
    "metryki_wideo": """
        CREATE TABLE IF NOT EXISTS metryki_wideo (
            id_wideo       UUID,
            platforma      LowCardinality(String),
            timestamp      DateTime,
            wyswietlenia   UInt64,
            polubienia     UInt32,
            komentarze     UInt32,
            udostepnienia  UInt32,
            ctr_procent    Float32,   -- Click-Through Rate
            watch_time_s   Float32,   -- Średni czas oglądania w sekundach
            zasieg         UInt64,
            -- Metryki specyficzne dla platform (od grudnia 2025)
            skip_rate      Float32,   -- TikTok/Reels skip rate
            repost_count   UInt32,    -- Instagram repost counts
            -- Metadane
            model_ai       LowCardinality(String),
            jezyk          LowCardinality(String),
            rozdzielczosc  LowCardinality(String)
        )
        ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (id_wideo, timestamp)
        TTL timestamp + INTERVAL 2 YEAR
        SETTINGS index_granularity = 8192
    """,

    "metryki_kampanii": """
        CREATE TABLE IF NOT EXISTS metryki_kampanii (
            id_kampanii    UUID,
            id_wideo       UUID,
            timestamp      DateTime,
            ctr_procent    Float32,
            roas           Float32,   -- Return on Ad Spend
            koszt_usd      Float32,
            konwersje      UInt32
        )
        ENGINE = MergeTree()
        ORDER BY (id_kampanii, timestamp)
        SETTINGS index_granularity = 8192
    """,

    "zdarzenia_uzytkownikow": """
        CREATE TABLE IF NOT EXISTS zdarzenia_uzytkownikow (
            id_uzytkownika UUID,
            id_wideo       UUID,
            typ_zdarzenia  LowCardinality(String),  -- klik, obejrzenie, share
            timestamp      DateTime,
            czas_ogladania_s Float32,
            platforma      LowCardinality(String),
            kraj           LowCardinality(String)
        )
        ENGINE = MergeTree()
        PARTITION BY toYYYYMMDD(timestamp)
        ORDER BY (id_uzytkownika, timestamp)
        TTL timestamp + INTERVAL 1 YEAR
    """,

    # Materialized view dla szybkich agregatów (AggregatingMergeTree)
    "metryki_dzienny_agregat": """
        CREATE MATERIALIZED VIEW IF NOT EXISTS metryki_dzienny_agregat
        ENGINE = AggregatingMergeTree()
        ORDER BY (id_wideo, platforma, data)
        AS SELECT
            id_wideo,
            platforma,
            toDate(timestamp) AS data,
            sumState(wyswietlenia)  AS wyswietlenia_total,
            avgState(ctr_procent)   AS ctr_sredni,
            avgState(watch_time_s)  AS watch_time_sredni,
            maxState(zasieg)        AS zasieg_max
        FROM metryki_wideo
        GROUP BY id_wideo, platforma, data
    """,
}


class KlientClickHouse:
    """
    Klient do operacji na bazie ClickHouse.

    Przykłady zapytań:
    - Metryki wideo: SELECT sum(wyswietlenia), avg(ctr) FROM metryki_wideo WHERE id_wideo = ?
    - Panel 30 dni: SELECT toDate(timestamp), sum(wyswietlenia) GROUP BY toDate(timestamp)
    - Top wideo: SELECT id_wideo, sum(wyswietlenia) GROUP BY id_wideo ORDER BY 2 DESC LIMIT 10
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8123,
        baza_danych: str = "viraloop",
        uzytkownik: str = "default",
        haslo: str = "",
    ):
        self.host = host
        self.port = port
        self.baza_danych = baza_danych
        self.uzytkownik = uzytkownik
        self.haslo = haslo
        self._klient = None

    async def polacz(self) -> None:
        """Nawiązuje połączenie z ClickHouse."""
        try:
            import clickhouse_connect

            self._klient = clickhouse_connect.get_async_client(
                host=self.host,
                port=self.port,
                database=self.baza_danych,
                username=self.uzytkownik,
                password=self.haslo,
                compress=True,  # Kompresja LZ4 dla lepszej wydajności
            )
            logger.info("Połączono z ClickHouse", host=self.host, baza=self.baza_danych)

        except ImportError:
            logger.warning("clickhouse_connect niedostępny – tryb offline")

    async def inicjalizuj_schemat(self) -> None:
        """Tworzy tabele i materialized views jeśli nie istnieją."""
        if self._klient is None:
            logger.warning("Klient ClickHouse niedostępny – pomijam inicjalizację schematu")
            return

        for nazwa_tabeli, zapytanie in SCHEMATY_TABEL.items():
            try:
                await self._klient.command(zapytanie)
                logger.info("Tabela ClickHouse gotowa", tabela=nazwa_tabeli)
            except Exception as e:
                logger.error("Błąd tworzenia tabeli", tabela=nazwa_tabeli, blad=str(e))

    async def zapisz_metryki(self, metryki: list[dict[str, Any]]) -> None:
        """
        Zapisuje metryki wideo do ClickHouse (wsadowo).

        Optymalny rozmiar wsadu: 1000-10000 wierszy.
        ClickHouse jest zoptymalizowany pod zapis wsadowy, nie jednostkowy.
        """
        if self._klient is None:
            logger.debug("Symulacja zapisu metryk", liczba=len(metryki))
            return

        try:
            await self._klient.insert(
                table="metryki_wideo",
                data=metryki,
                column_names=list(metryki[0].keys()) if metryki else [],
            )
            logger.info("Zapisano metryki", liczba=len(metryki))
        except Exception as e:
            logger.error("Błąd zapisu metryk", blad=str(e))
            raise

    async def pobierz_metryki_wideo(
        self,
        id_wideo: str,
        od: datetime | None = None,
        do: datetime | None = None,
        platforma: str | None = None,
    ) -> list[dict[str, Any]]:
        """Pobiera metryki konkretnego wideo."""
        if self._klient is None:
            return []

        warunki = ["id_wideo = {id_wideo:UUID}"]
        parametry: dict[str, Any] = {"id_wideo": id_wideo}

        if od:
            warunki.append("timestamp >= {od:DateTime}")
            parametry["od"] = od
        if do:
            warunki.append("timestamp <= {do:DateTime}")
            parametry["do"] = do
        if platforma:
            warunki.append("platforma = {platforma:String}")
            parametry["platforma"] = platforma

        zapytanie = f"""
            SELECT
                id_wideo,
                platforma,
                timestamp,
                wyswietlenia,
                polubienia,
                ctr_procent,
                watch_time_s,
                zasieg
            FROM metryki_wideo
            WHERE {' AND '.join(warunki)}
            ORDER BY timestamp DESC
            LIMIT 1000
        """

        try:
            wynik = await self._klient.query(zapytanie, parameters=parametry)
            return wynik.named_results()
        except Exception as e:
            logger.error("Błąd zapytania ClickHouse", blad=str(e))
            return []

    async def pobierz_panel_dzienny(
        self,
        od: datetime,
        do: datetime,
    ) -> list[dict[str, Any]]:
        """
        Pobiera dzienny panel metryk z materialized view.

        Używa AggregatingMergeTree + mergeFunctions dla szybkich agregatów.
        Sub-sekundowe odpowiedzi nawet dla miliardów wierszy.
        """
        if self._klient is None:
            return []

        zapytanie = """
            SELECT
                data,
                sumMerge(wyswietlenia_total)  AS wyswietlenia,
                avgMerge(ctr_sredni)          AS ctr_procent,
                avgMerge(watch_time_sredni)   AS watch_time_s,
                maxMerge(zasieg_max)          AS zasieg
            FROM metryki_dzienny_agregat
            WHERE data BETWEEN {od:Date} AND {do:Date}
            GROUP BY data
            ORDER BY data ASC
        """

        try:
            wynik = await self._klient.query(
                zapytanie,
                parameters={"od": od.date(), "do": do.date()},
            )
            return wynik.named_results()
        except Exception as e:
            logger.error("Błąd zapytania panelu", blad=str(e))
            return []

    async def pobierz_top_wideo(
        self,
        platforma: str | None = None,
        limit: int = 10,
        metrika: str = "wyswietlenia",
    ) -> list[dict[str, Any]]:
        """Pobiera ranking najlepszych wideo."""
        if self._klient is None:
            return []

        warunek_platformy = "AND platforma = {platforma:String}" if platforma else ""

        zapytanie = f"""
            SELECT
                id_wideo,
                platforma,
                sum(wyswietlenia)  AS wyswietlenia_total,
                avg(ctr_procent)   AS ctr_sredni,
                avg(watch_time_s)  AS watch_time_sredni
            FROM metryki_wideo
            WHERE timestamp >= now() - INTERVAL 30 DAY
            {warunek_platformy}
            GROUP BY id_wideo, platforma
            ORDER BY wyswietlenia_total DESC
            LIMIT {{limit:UInt16}}
        """

        try:
            parametry: dict[str, Any] = {"limit": limit}
            if platforma:
                parametry["platforma"] = platforma

            wynik = await self._klient.query(zapytanie, parameters=parametry)
            return wynik.named_results()
        except Exception as e:
            logger.error("Błąd zapytania top wideo", blad=str(e))
            return []
