"""
ViraLoop – DNA Wideo (Baza wektorowa Qdrant)

"DNA wideo" to embeddingi kodujące treść, styl i wzorce wydajności każdego wideo.
Qdrant (Rust, 12K QPS, pre-filtering) idealnie pasuje do filtrowania milionów
embeddingów według platformy, kategorii, tieru wydajności i zakresu dat.

Multi-wektory na punkt: osobne embeddingi dla stylu wizualnego, charakterystyki
audio i struktury treści – wszystko w jednym wpisie Qdrant.

Cennik: Darmowy self-hosted, free tier 1GB cloud, ~$102/mies za 1M wektorów na AWS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)

# Wymiary embeddingów
WYMIAR_EMBEDDINGS_WIZUALNE = 1024   # CLIP ViT-L/14
WYMIAR_EMBEDDINGS_AUDIO = 512       # CLAP (Contrastive Language-Audio Pretraining)
WYMIAR_EMBEDDINGS_TRESCI = 768      # text-embedding-3-small


@dataclass
class DnaWideo:
    """
    'DNA' pojedynczego wideo – wielowymiarowa reprezentacja wektorowa.

    Każde pole to osobny wektor w Qdrant (multi-vector per point).
    """

    id_wideo: UUID

    # Embeddingi treści wizualnej (CLIP ViT-L/14)
    embedding_wizualne: list[float] = field(default_factory=list)

    # Embeddingi charakterystyki audio (CLAP)
    embedding_audio: list[float] = field(default_factory=list)

    # Embeddingi struktury treści (opis + tagi + transkrypcja)
    embedding_tresci: list[float] = field(default_factory=list)

    # Metadane do pre-filtrowania w Qdrant
    platforma: str = "youtube"
    kategoria: str = "edukacja"
    model_ai: str = "kling-3.0"
    jezyk: str = "pl"
    rozdzielczosc: str = "1080p"
    czas_trwania_s: int = 0
    data_publikacji: str = ""

    # Metryki wydajności (do filtrowania po "tierze wydajności")
    wyswietlenia: int = 0
    ctr_procent: float = 0.0
    watch_time_procent: float = 0.0
    tier_wydajnosci: str = "sredni"  # niski | sredni | wysoki | wirusowy


class BazaDnaWideo:
    """
    Zarządza bazą wektorową DNA wideo w Qdrant.

    Architektura kolekcji Qdrant:
    - Kolekcja: "dna_wideo"
    - Wektory nazwane: "wizualne", "audio", "tresci"
    - Indeksy filtrowania: platforma, kategoria, tier_wydajnosci, data

    Przykładowe zapytanie (wyszukaj podobne wideo high-CTR w kategorii 'technologia'):
        wyniki = await baza.wyszukaj_podobne(
            embedding_referencyjny=moje_embedding,
            typ_wektora="wizualne",
            filtry={"kategoria": "technologia", "tier_wydajnosci": "wysoki"},
            top_k=20
        )
    """

    NAZWA_KOLEKCJI = "dna_wideo"

    def __init__(self, url: str = "http://localhost:6333"):
        self.url = url
        self._klient = None

    async def polacz(self) -> None:
        """Nawiązuje połączenie z Qdrant."""
        try:
            from qdrant_client import AsyncQdrantClient
            from qdrant_client.models import Distance, VectorParams

            self._klient = AsyncQdrantClient(url=self.url)

            # Utwórz kolekcję z multi-wektorami jeśli nie istnieje
            kolekcje = await self._klient.get_collections()
            nazwy_istniejacych = [k.name for k in kolekcje.collections]

            if self.NAZWA_KOLEKCJI not in nazwy_istniejacych:
                await self._klient.create_collection(
                    collection_name=self.NAZWA_KOLEKCJI,
                    vectors_config={
                        "wizualne": VectorParams(
                            size=WYMIAR_EMBEDDINGS_WIZUALNE,
                            distance=Distance.COSINE,
                        ),
                        "audio": VectorParams(
                            size=WYMIAR_EMBEDDINGS_AUDIO,
                            distance=Distance.COSINE,
                        ),
                        "tresci": VectorParams(
                            size=WYMIAR_EMBEDDINGS_TRESCI,
                            distance=Distance.COSINE,
                        ),
                    },
                )
                logger.info("Kolekcja Qdrant utworzona", nazwa=self.NAZWA_KOLEKCJI)

                # Utwórz indeks payload dla szybkiego pre-filtrowania
                for pole in ["platforma", "kategoria", "tier_wydajnosci", "jezyk", "model_ai"]:
                    await self._klient.create_payload_index(
                        collection_name=self.NAZWA_KOLEKCJI,
                        field_name=pole,
                        field_schema="keyword",
                    )

                logger.info("Indeksy payload Qdrant utworzone")

        except ImportError:
            logger.warning("qdrant_client niedostępny – tryb offline")

    async def zapisz_dna(self, dna: DnaWideo) -> bool:
        """
        Zapisuje DNA wideo do Qdrant.

        Qdrant przyjmuje multi-wektory w jednym punkcie – efektywniejsze
        niż przechowywanie osobnych kolekcji dla każdego typu embeddings.
        """
        if self._klient is None:
            logger.debug("Symulacja zapisu DNA", id_wideo=str(dna.id_wideo))
            return True

        try:
            from qdrant_client.models import PointStruct

            await self._klient.upsert(
                collection_name=self.NAZWA_KOLEKCJI,
                points=[
                    PointStruct(
                        id=str(dna.id_wideo),
                        vector={
                            "wizualne": dna.embedding_wizualne or [0.0] * WYMIAR_EMBEDDINGS_WIZUALNE,
                            "audio": dna.embedding_audio or [0.0] * WYMIAR_EMBEDDINGS_AUDIO,
                            "tresci": dna.embedding_tresci or [0.0] * WYMIAR_EMBEDDINGS_TRESCI,
                        },
                        payload={
                            "id_wideo": str(dna.id_wideo),
                            "platforma": dna.platforma,
                            "kategoria": dna.kategoria,
                            "model_ai": dna.model_ai,
                            "jezyk": dna.jezyk,
                            "rozdzielczosc": dna.rozdzielczosc,
                            "czas_trwania_s": dna.czas_trwania_s,
                            "data_publikacji": dna.data_publikacji,
                            "wyswietlenia": dna.wyswietlenia,
                            "ctr_procent": dna.ctr_procent,
                            "watch_time_procent": dna.watch_time_procent,
                            "tier_wydajnosci": dna.tier_wydajnosci,
                        },
                    )
                ],
            )
            return True

        except Exception as e:
            logger.error("Błąd zapisu DNA", blad=str(e))
            return False

    async def wyszukaj_podobne(
        self,
        embedding_referencyjny: list[float],
        typ_wektora: str = "wizualne",
        filtry: dict[str, Any] | None = None,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Wyszukuje wideo podobne do referencyjnego.

        Pre-filtering Qdrant: wykonuje złożone zapytania metadanych PRZED
        przeszukiwaniem wektorów – kluczowe dla milionów wideo przefiltrowanych
        po platformie, kategorii, tierze wydajności i dacie.

        Args:
            embedding_referencyjny: Wektor wideo referencyjnego
            typ_wektora: "wizualne" | "audio" | "tresci"
            filtry: Słownik filtrów metadanych
            top_k: Liczba zwracanych wyników

        Returns:
            Lista wideo z wynikami podobieństwa i metadanymi
        """
        if self._klient is None:
            return []

        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Zbuduj filtr Qdrant z metadanych
            warunki_filtra = []
            if filtry:
                for pole, wartosc in filtry.items():
                    warunki_filtra.append(
                        FieldCondition(
                            key=pole,
                            match=MatchValue(value=wartosc),
                        )
                    )

            filtr_qdrant = Filter(must=warunki_filtra) if warunki_filtra else None

            wyniki = await self._klient.search(
                collection_name=self.NAZWA_KOLEKCJI,
                query_vector=(typ_wektora, embedding_referencyjny),
                query_filter=filtr_qdrant,
                limit=top_k,
                with_payload=True,
            )

            return [
                {
                    "id_wideo": wynik.payload.get("id_wideo"),
                    "wynik_podobienstwa": wynik.score,
                    **wynik.payload,
                }
                for wynik in wyniki
            ]

        except Exception as e:
            logger.error("Błąd wyszukiwania Qdrant", blad=str(e))
            return []

    async def pobierz_dna(self, id_wideo: UUID) -> DnaWideo | None:
        """Pobiera DNA konkretnego wideo."""
        if self._klient is None:
            return None

        try:
            wyniki = await self._klient.retrieve(
                collection_name=self.NAZWA_KOLEKCJI,
                ids=[str(id_wideo)],
                with_vectors=True,
                with_payload=True,
            )

            if not wyniki:
                return None

            punkt = wyniki[0]
            payload = punkt.payload or {}
            wektory = punkt.vector or {}

            return DnaWideo(
                id_wideo=id_wideo,
                embedding_wizualne=wektory.get("wizualne", []),
                embedding_audio=wektory.get("audio", []),
                embedding_tresci=wektory.get("tresci", []),
                platforma=payload.get("platforma", "youtube"),
                kategoria=payload.get("kategoria", ""),
                model_ai=payload.get("model_ai", ""),
                jezyk=payload.get("jezyk", "pl"),
                wyswietlenia=payload.get("wyswietlenia", 0),
                ctr_procent=payload.get("ctr_procent", 0.0),
                watch_time_procent=payload.get("watch_time_procent", 0.0),
                tier_wydajnosci=payload.get("tier_wydajnosci", "sredni"),
            )

        except Exception as e:
            logger.error("Błąd pobierania DNA", blad=str(e))
            return None
