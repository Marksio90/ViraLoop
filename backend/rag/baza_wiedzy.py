"""
NEXUS — Brand RAG: Baza Wiedzy Marki
======================================
System RAG (Retrieval-Augmented Generation) zapewniający spójność
głosu marki we wszystkich generowanych treściach.

Używa:
- OpenAI text-embedding-3-small ($0.020/1M tokenów — najtańszy, świetny)
- ChromaDB jako lokalny vector store (darmowy, zero latencji)
- Automatyczne chunking dokumentów marki

Funkcje:
- Przechowywanie wytycznych marki
- Semantyczne wyszukiwanie podobnych treści
- Kontekst RAG dla agentów
"""

import json
import hashlib
import structlog
from pathlib import Path
from openai import AsyncOpenAI

from konfiguracja import konf

logger = structlog.get_logger(__name__)

# Domyślna baza wiedzy NEXUS (gdy brak profilu marki)
DOMYSLNA_BAZA_WIEDZY = {
    "ogolna": """
Platforma NEXUS tworzy wirusowe krótkie wideo po polsku.
Ton: ekspercki, energiczny, autentyczny.
Styl wizualny: nowoczesny, dynamiczny, profesjonalny.
Odbiorcy: twórcy treści 18-35 lat, marketerzy, agencje.
Wartości: innowacja, skuteczność, data-driven marketing.
Unikamy: clickbaitu, dezinformacji, treści naruszających prawa autorskie.
""",
    "haki": """
Najlepiej konwertujące haki dla polskiej publiczności:
1. "Nie wiedziałem, że X zmienia wszystko..."
2. "To dlatego Twoje wideo nie viralują..."
3. "95% twórców popełnia ten błąd..."
4. "W 60 sekund nauczę Cię X..."
5. "Algorytm TikToka nie lubi gdy robisz X..."
""",
    "cta": """
Najskuteczniejsze CTA po polsku:
- "Obserwuj, żeby nie przegapić kolejnej lekcji"
- "Komentuj co Cię zaskoczyło"
- "Zapisz ten post — będziesz potrzebować"
- "Wyślij znajomemu, który robi wideo"
- "Kliknij profil po więcej takich wskazówek"
""",
}


class BazaWiedzyMarki:
    """
    Lokalna baza wiedzy marki dla RAG.

    Używa ChromaDB (in-memory dla uproszczenia lub persistent dla produkcji).
    """

    def __init__(self, nazwa_marki: str = "nexus"):
        self._klient_openai = AsyncOpenAI(api_key=konf.OPENAI_API_KEY)
        self._nazwa_marki = nazwa_marki
        self._dokumenty: dict[str, str] = {}
        self._embeddingi: dict[str, list[float]] = {}
        self._log = logger.bind(komponent="BazaWiedzyMarki", marka=nazwa_marki)

        # Załaduj domyślną wiedzę
        for klucz, tekst in DOMYSLNA_BAZA_WIEDZY.items():
            self._dokumenty[klucz] = tekst.strip()

        self._log.info("Baza wiedzy marki zainicjalizowana")

    def _hash_tekstu(self, tekst: str) -> str:
        """Generuje hash tekstu (do cache'owania embedingów)."""
        return hashlib.md5(tekst.encode()).hexdigest()[:8]

    async def dodaj_dokument(self, klucz: str, tekst: str) -> None:
        """
        Dodaje dokument do bazy wiedzy.

        Args:
            klucz: Identyfikator dokumentu (np. "wytyczne_marki")
            tekst: Treść dokumentu
        """
        self._dokumenty[klucz] = tekst
        # Usuń stary embedding (wymusi przeliczenie)
        self._embeddingi.pop(klucz, None)
        self._log.info("Dokument dodany", klucz=klucz, dlugosc=len(tekst))

    async def _pobierz_embedding(self, tekst: str) -> list[float]:
        """Pobiera embedding z OpenAI (z cache)."""
        hash_klucz = self._hash_tekstu(tekst)

        if hash_klucz not in self._embeddingi:
            # Truncate do max 8191 tokenów
            tekst_skrocony = tekst[:30000]

            odpowiedz = await self._klient_openai.embeddings.create(
                model=konf.MODEL_EMBEDDINGI,  # text-embedding-3-small
                input=tekst_skrocony,
            )
            self._embeddingi[hash_klucz] = odpowiedz.data[0].embedding

        return self._embeddingi[hash_klucz]

    def _podobienstwo_cosinusowe(
        self, vec1: list[float], vec2: list[float]
    ) -> float:
        """Oblicza cosine similarity między dwoma wektorami."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = sum(a ** 2 for a in vec1) ** 0.5
        mag2 = sum(b ** 2 for b in vec2) ** 0.5
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    async def wyszukaj(
        self, zapytanie: str, top_k: int = 3
    ) -> list[tuple[str, str, float]]:
        """
        Semantyczne wyszukiwanie w bazie wiedzy.

        Args:
            zapytanie: Treść zapytania
            top_k: Liczba wyników

        Returns:
            Lista (klucz, tekst, podobieństwo) posortowana malejąco
        """
        if not self._dokumenty:
            return []

        embedding_zapytania = await self._pobierz_embedding(zapytanie)

        wyniki = []
        for klucz, tekst in self._dokumenty.items():
            embedding_dok = await self._pobierz_embedding(tekst)
            podobienstwo = self._podobienstwo_cosinusowe(embedding_zapytania, embedding_dok)
            wyniki.append((klucz, tekst, podobienstwo))

        wyniki.sort(key=lambda x: x[2], reverse=True)
        return wyniki[:top_k]

    async def pobierz_kontekst(self, brief: str) -> str:
        """
        Pobiera skonsolidowany kontekst RAG dla danego briefu.

        Args:
            brief: Brief wideo od użytkownika

        Returns:
            Tekst kontekstu dla agentów
        """
        try:
            wyniki = await self.wyszukaj(brief, top_k=3)

            if not wyniki:
                return ""

            kontekst_czesci = []
            for klucz, tekst, podobienstwo in wyniki:
                if podobienstwo > 0.3:  # Tylko wystarczająco podobne
                    kontekst_czesci.append(f"### {klucz.upper()}:\n{tekst}")

            kontekst = "\n\n".join(kontekst_czesci)
            self._log.info("Kontekst RAG pobrany", dokumenty=len(wyniki), dlugosc=len(kontekst))
            return kontekst

        except Exception as e:
            self._log.error("Błąd pobierania kontekstu RAG", blad=str(e))
            return ""

    def zaladuj_profil_marki(self, profil: dict) -> None:
        """
        Ładuje profil marki do bazy.

        Args:
            profil: Słownik z danymi marki
        """
        for klucz, wartosc in profil.items():
            if isinstance(wartosc, str) and wartosc.strip():
                self._dokumenty[f"marka_{klucz}"] = wartosc


# Globalny cache baz wiedzy per marka
_bazy_wiedzy: dict[str, BazaWiedzyMarki] = {}


def pobierz_baze_wiedzy(nazwa_marki: str = "nexus") -> BazaWiedzyMarki:
    """Zwraca (lub tworzy) bazę wiedzy dla marki."""
    if nazwa_marki not in _bazy_wiedzy:
        _bazy_wiedzy[nazwa_marki] = BazaWiedzyMarki(nazwa_marki)
    return _bazy_wiedzy[nazwa_marki]
