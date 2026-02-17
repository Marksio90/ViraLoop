"""
ViraLoop – Centralna konfiguracja aplikacji

Używa pydantic-settings do zarządzania zmiennymi środowiskowymi.
Wszystkie sekrety ładowane są z .env lub zmiennych środowiskowych.
NIGDY nie trzymaj sekretów w kodzie źródłowym.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Ustawienia(BaseSettings):
    """Konfiguracja aplikacji ViraLoop."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Informacje o aplikacji ──────────────────────────────────────
    WERSJA_API: str = "1.0.0"
    SRODOWISKO: str = "development"  # development | staging | production
    DEBUG: bool = False
    TAJNY_KLUCZ: str = "ZMIEN_MNIE_W_PRODUKCJI_na_losowy_ciag_64_znakow"

    # ── Dozwolone źródła CORS ───────────────────────────────────────
    DOZWOLONE_ZRODLA: list[str] = [
        "http://localhost:3000",
        "https://app.viraloop.pl",
        "https://www.viraloop.pl",
    ]

    # ── Generowanie wideo ───────────────────────────────────────────
    FAL_API_KEY: str = ""
    RUNWAYML_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""           # Vertex AI (Veo 3.1)
    OPENAI_API_KEY: str = ""           # Sora 2
    REPLICATE_API_TOKEN: str = ""

    # ── Głos i muzyka ───────────────────────────────────────────────
    ELEVENLABS_API_KEY: str = ""
    FISHAUDIO_API_KEY: str = ""
    MUBERT_API_KEY: str = ""
    SOUNDRAW_API_KEY: str = ""

    # ── LLM i orkiestracja ──────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""        # Claude (tłumaczenia, scenariusze)
    LANGSMITH_API_KEY: str = ""        # Obserwowalność LangGraph/DSPy
    LANGSMITH_PROJECT: str = "viraloop-production"

    # ── Tłumaczenia ─────────────────────────────────────────────────
    DEEPL_API_KEY: str = ""            # Języki europejskie
    GOOGLE_TRANSLATE_KEY: str = ""     # 130+ języków (azjatyckie, egzotyczne)

    # ── Bazy danych ─────────────────────────────────────────────────
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_DB: str = "viraloop"
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""

    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""           # Wymagany dla Qdrant Cloud

    REDIS_URL: str = "redis://localhost:6379/0"

    POSTGRES_URL: str = "postgresql+asyncpg://viraloop:haslo@localhost:5432/viraloop"

    # ── Analityka platform ──────────────────────────────────────────
    YOUTUBE_API_KEY: str = ""          # 10K darmowych jednostek/dzień
    TIKTOK_CLIENT_KEY: str = ""        # TikTok Research API
    TIKTOK_CLIENT_SECRET: str = ""
    INSTAGRAM_ACCESS_TOKEN: str = ""   # Instagram Graph API

    # ── Infrastruktura obliczeniowa ─────────────────────────────────
    RAY_ADDRESS: str = "ray://ray-head:10001"  # KubeRay
    MODAL_TOKEN_ID: str = ""
    MODAL_TOKEN_SECRET: str = ""

    # ── Storage ─────────────────────────────────────────────────────
    S3_BUCKET: str = "viraloop-media"
    S3_REGION: str = "eu-central-1"
    AWS_ACCESS_KEY: str = ""
    AWS_SECRET_KEY: str = ""
    CDN_URL: str = "https://cdn.viraloop.pl"

    # ── Limity i ograniczenia ───────────────────────────────────────
    MAX_DLUGOSC_WIDEO_S: int = 600         # 10 minut max
    MAX_ROZMIAR_PLIKU_MB: int = 2048       # 2GB
    MAKS_JEDNOCZESNYCH_ZADAN: int = 50
    LIMIT_SZYBKOSCI_API: int = 100         # żądań/minutę na użytkownika

    @property
    def jest_produkcja(self) -> bool:
        return self.SRODOWISKO == "production"

    @property
    def jest_dev(self) -> bool:
        return self.SRODOWISKO == "development"


@lru_cache
def pobierz_ustawienia() -> Ustawienia:
    """Zwraca singleton konfiguracji (cache LRU)."""
    return Ustawienia()


# Eksportuj singleton
ustawienia = pobierz_ustawienia()
