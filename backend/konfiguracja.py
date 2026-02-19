"""
NEXUS — Konfiguracja Systemu
============================
Centralne zarządzanie wszystkimi ustawieniami platformy.
Optymalizacja kosztów OpenAI: mini dla 90% zadań, gpt-4o dla 10%.

Koszt szacunkowy na wideo: ~$0.14
- Skrypty (gpt-4o-mini): $0.001
- Obrazy 3x (dall-e-3): $0.12
- Głos (tts-1): $0.018
- Recenzja (gpt-4o): $0.005
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Konfiguracja(BaseSettings):
    """Główna konfiguracja platformy NEXUS."""

    # ----------------------------------------------------------------
    # Środowisko aplikacji
    # ----------------------------------------------------------------
    SRODOWISKO: str = Field(default="development", description="development | production")
    DEBUG: bool = Field(default=True)
    WERSJA_API: str = Field(default="1.0.0")
    TAJNY_KLUCZ: str = Field(default="zmien-to-na-produkcji-min-64-znaki-bardzo-wazne-bezpieczenstwo!")

    # ----------------------------------------------------------------
    # OpenAI — klucz główny (jedyny dostawca AI)
    # ----------------------------------------------------------------
    OPENAI_API_KEY: str = Field(default="", description="Klucz API OpenAI")

    # Modele OpenAI — strategia kosztów:
    # gpt-4o-mini: $0.15/1M wej, $0.60/1M wyj (90% zadań)
    # gpt-4o:      $2.50/1M wej, $10/1M wyj  (10% zadań — tylko recenzja)
    MODEL_INTELIGENTNY: str = Field(default="gpt-4o", description="Dla złożonego rozumowania")
    MODEL_EKONOMICZNY: str = Field(default="gpt-4o-mini", description="Dla większości zadań")
    MODEL_OBRAZY: str = Field(default="dall-e-3", description="Generacja wizualna")
    MODEL_GLOS: str = Field(default="tts-1", description="Synteza mowy — tańszy")
    MODEL_GLOS_HD: str = Field(default="tts-1-hd", description="Synteza mowy — HD")
    MODEL_EMBEDDINGI: str = Field(default="text-embedding-3-small", description="Embeddingi RAG")
    MODEL_WHISPER: str = Field(default="whisper-1", description="Transkrypcja audio")

    # Głosy TTS
    DOMYSLNY_GLOS: str = Field(default="nova", description="nova | alloy | echo | fable | onyx | shimmer")

    # ----------------------------------------------------------------
    # LangSmith — obserwacja agentów (opcjonalnie)
    # ----------------------------------------------------------------
    LANGCHAIN_TRACING_V2: bool = Field(default=False)
    LANGCHAIN_API_KEY: str = Field(default="")
    LANGCHAIN_PROJECT: str = Field(default="nexus-ai-platforma")

    # ----------------------------------------------------------------
    # Bazy danych
    # ----------------------------------------------------------------
    POSTGRES_URL: str = Field(
        default="postgresql+asyncpg://nexus:nexus@localhost:5432/nexus",
        description="PostgreSQL — dane transakcyjne"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis — cache i kolejkowanie"
    )

    # ChromaDB — lokalna baza wektorów (zastępuje Qdrant dla prostoty)
    CHROMA_SCIEZKA: str = Field(default="./dane/chroma", description="Lokalna baza wektorów")

    # ----------------------------------------------------------------
    # Storage — pliki wideo i audio
    # ----------------------------------------------------------------
    SCIEZKA_TYMCZASOWA: str = Field(default="/tmp/nexus", description="Pliki tymczasowe")
    SCIEZKA_WYJSCIOWA: str = Field(default="./dane/wideo", description="Gotowe wideo")

    # ----------------------------------------------------------------
    # Limity i parametry
    # ----------------------------------------------------------------
    MAKS_DLUGOSC_WIDEO: int = Field(default=180, description="Maks. długość wideo w sekundach")
    MAKS_OBRAZOW_NA_SCENA: int = Field(default=5, description="Maks. liczba obrazów DALL-E na wideo")
    MAKS_PONOWNYCH_PROB: int = Field(default=3, description="Maks. liczba ponowień przy błędzie")
    PROG_JAKOSCI: int = Field(default=60, description="Minimalny wynik jakości (0-100)")
    PROG_WIRALNOSCI: int = Field(default=75, description="Wynik wiralności → odznaka 🔥")

    # ----------------------------------------------------------------
    # CORS
    # ----------------------------------------------------------------
    DOZWOLONE_ZRODLA: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Dozwolone origins CORS"
    )

    # ----------------------------------------------------------------
    # Platforma i analityki społecznościowe (opcjonalnie)
    # ----------------------------------------------------------------
    YOUTUBE_API_KEY: str = Field(default="", description="YouTube Data API v3")
    TIKTOK_CLIENT_KEY: str = Field(default="", description="TikTok Research API")
    INSTAGRAM_ACCESS_TOKEN: str = Field(default="", description="Instagram Graph API")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def pobierz_konfiguracje() -> Konfiguracja:
    """Zwraca singleton konfiguracji (cache LRU)."""
    return Konfiguracja()


# Alias globalny
konf = pobierz_konfiguracje()
