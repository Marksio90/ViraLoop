"""
ViraLoop – Generator muzyki AI

Obsługuje kilka silników muzyki z priorytetem bezpieczeństwa prawnego.

Ważne: Suno v5 i podobne modele są przedmiotem pozwów sądowych Sony/Universal/Warner.
Dla platformy komercyjnej ZAWSZE preferuj: SOUNDRAW, Beatoven.ai, Mubert, TemPolor.

"Moment Stable Diffusion dla muzyki": ACE-Step v1.5 (styczeń 2026) – open-source,
4-minutowy utwór w ~20s na A100, klonowanie głosu, edycja tekstów, LoRA fine-tuning.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class SilnikMuzyki(str, Enum):
    """Dostępne silniki generowania muzyki."""

    SOUNDRAW = "soundraw"       # Bezpieczne prawnie, licencja wieczysta
    BEATOVEN = "beatoven"       # Bezpieczne prawnie, wytrenowane na licencjonowanym audio
    ACE_STEP = "ace-step"       # Open-source, 4-min w 20s na A100
    MUBERT = "mubert"           # API, muzyka w czasie rzeczywistym
    TEMPOLR = "tempolr"         # Bezpieczne prawnie, royalty-free
    MUSICGEN = "musicgen"       # Meta, MIT, 300M-3.3B params (do prototypowania)


@dataclass
class KonfiguracijaMuzyki:
    """Konfiguracja silnika muzyki."""

    id: str
    nazwa: str
    bezpieczne_prawnie: bool
    typ_licencji: str
    koszt_usd: str
    generuje_wokal: bool
    max_dlugosc_min: int
    opis: str


SILNIKI_MUZYKI: dict[str, KonfiguracijaMuzyki] = {
    SilnikMuzyki.SOUNDRAW: KonfiguracijaMuzyki(
        id="soundraw",
        nazwa="SOUNDRAW",
        bezpieczne_prawnie=True,
        typ_licencji="Wieczysta royalty-free",
        koszt_usd="$16.99/mies (Creator) / $49.99/mies (Team)",
        generuje_wokal=False,
        max_dlugosc_min=10,
        opis=(
            "Trenowany wyłącznie na muzyce wewnętrznej. Wieczysta licencja royalty-free. "
            "ZERO ryzyka praw autorskich dla platformy komercyjnej. Idealne dla reklam i treści YT."
        ),
    ),
    SilnikMuzyki.BEATOVEN: KonfiguracijaMuzyki(
        id="beatoven",
        nazwa="Beatoven.ai",
        bezpieczne_prawnie=True,
        typ_licencji="Royalty-free z licencją komercyjną",
        koszt_usd="$9.99/mies (Basic) / $29.99/mies (Pro)",
        generuje_wokal=False,
        max_dlugosc_min=5,
        opis=(
            "Trenowany na licencjonowanej muzyce. Pełna licencja komercyjna. "
            "Dopasowuje nastrój i tempo do kluczowych momentów wideo."
        ),
    ),
    SilnikMuzyki.ACE_STEP: KonfiguracijaMuzyki(
        id="ace-step",
        nazwa="ACE-Step v1.5",
        bezpieczne_prawnie=False,  # Otwarte pytania dot. danych treningowych
        typ_licencji="Apache 2.0 (kod)",
        koszt_usd="Koszt GPU (~$0.05/utwór na A100)",
        generuje_wokal=True,
        max_dlugosc_min=10,
        opis=(
            "PRZEŁOM w open-source muzyce (styczeń 2026). 4-minutowy utwór klasy komercyjnej w ~20s na A100. "
            "Klonowanie głosu, edycja tekstów na żywo, LoRA fine-tuning. Działa na RTX 3060 12GB. "
            "UWAGA: Status prawny danych treningowych niejasny – skonsultuj z prawnikiem przed użyciem komercyjnym."
        ),
    ),
    SilnikMuzyki.MUBERT: KonfiguracijaMuzyki(
        id="mubert",
        nazwa="Mubert",
        bezpieczne_prawnie=True,
        typ_licencji="Royalty-free (licencja API)",
        koszt_usd="$14/mies (Creator) / $39/mies (Business)",
        generuje_wokal=False,
        max_dlugosc_min=60,
        opis=(
            "API do muzyki w czasie rzeczywistym. Dynamicznie dopasowuje nastrój i tempo do wideo. "
            "Idealne do długich treści i streamingu. Stworzone przez artystów, bezpieczne prawnie."
        ),
    ),
    SilnikMuzyki.TEMPOLR: KonfiguracijaMuzyki(
        id="tempolr",
        nazwa="TemPolor",
        bezpieczne_prawnie=True,
        typ_licencji="Royalty-free",
        koszt_usd="$9.99/mies",
        generuje_wokal=False,
        max_dlugosc_min=5,
        opis="Muzyka tła royalty-free z synchronizacją do nastroju wideo.",
    ),
    SilnikMuzyki.MUSICGEN: KonfiguracijaMuzyki(
        id="musicgen",
        nazwa="Meta MusicGen",
        bezpieczne_prawnie=False,
        typ_licencji="MIT (kod) / Niekomercyjne (modele)",
        koszt_usd="Koszt GPU (~$0.02/utwór)",
        generuje_wokal=False,
        max_dlugosc_min=5,
        opis=(
            "Meta, 300M-3.3B params, MIT kod. Do prototypowania i testów. "
            "ACE-Step wyprzedza MusicGen jakością. Modele tylko do użytku niekomercyjnego."
        ),
    ),
}


class GeneratorMuzyki:
    """
    Generuje muzykę tła dla wideo.

    Rekomendowana strategia dla ViraLoop:
    1. Treści komercyjne → SOUNDRAW lub Beatoven.ai
    2. Muzyka w czasie rzeczywistym → Mubert API
    3. Najwyższa jakość artystyczna (internal use) → ACE-Step v1.5
    4. Prototypowanie → MusicGen lub ACE-Step
    """

    async def generuj(
        self,
        opis: str,
        czas_trwania: int = 30,
        silnik: SilnikMuzyki = SilnikMuzyki.SOUNDRAW,
        gatunek: str = "ambient",
        tempo: int | None = None,
        energia: float = 0.7,  # 0.0 = spokojny, 1.0 = energiczny
        bezpieczne_prawnie: bool = True,
    ) -> bytes:
        """
        Generuje muzykę tła.

        Args:
            opis: Opis nastroju i stylu ("epicka muzyka orkiestralna, budowanie napięcia")
            czas_trwania: Czas w sekundach
            silnik: Wybrany silnik
            gatunek: Gatunek muzyczny
            tempo: BPM (None = automatyczny)
            energia: Poziom energii 0.0-1.0
            bezpieczne_prawnie: Czy wymagana bezpieczna licencja komercyjna

        Returns:
            Dane binarne pliku MP3
        """
        konfiguracja = SILNIKI_MUZYKI.get(silnik)
        if konfiguracja is None:
            raise ValueError(f"Nieznany silnik muzyki: {silnik}")

        if bezpieczne_prawnie and not konfiguracja.bezpieczne_prawnie:
            raise ValueError(
                f"Silnik '{silnik}' nie jest bezpieczny prawnie dla użytku komercyjnego. "
                f"Użyj: {[s for s, k in SILNIKI_MUZYKI.items() if k.bezpieczne_prawnie]}"
            )

        logger.info(
            "Generowanie muzyki",
            silnik=silnik,
            czas_trwania_s=czas_trwania,
            gatunek=gatunek,
            bezpieczne=konfiguracja.bezpieczne_prawnie,
        )

        if silnik == SilnikMuzyki.SOUNDRAW:
            return await self._soundraw(opis, czas_trwania, gatunek, tempo, energia)
        elif silnik == SilnikMuzyki.BEATOVEN:
            return await self._beatoven(opis, czas_trwania, gatunek)
        elif silnik == SilnikMuzyki.ACE_STEP:
            return await self._ace_step(opis, czas_trwania, gatunek)
        elif silnik == SilnikMuzyki.MUBERT:
            return await self._mubert(opis, czas_trwania, gatunek, energia)
        elif silnik == SilnikMuzyki.MUSICGEN:
            return await self._musicgen(opis, czas_trwania)
        else:
            raise NotImplementedError(f"Silnik {silnik} nie jest jeszcze zaimplementowany")

    async def _soundraw(
        self,
        opis: str,
        czas_trwania: int,
        gatunek: str,
        tempo: int | None,
        energia: float,
    ) -> bytes:
        """Generuje muzykę przez SOUNDRAW API."""
        try:
            import httpx

            # Mapowanie gatunków na kategorie SOUNDRAW
            mapowanie_gatunkow = {
                "ambient": "Ambient",
                "electronic": "Electronic",
                "orkiestra": "Cinematic",
                "hip-hop": "Hip Hop",
                "cinematic": "Cinematic",
                "pop": "Pop",
                "rock": "Rock",
            }

            async with httpx.AsyncClient() as klient:
                odpowiedz = await klient.post(
                    "https://soundraw.io/api/v2/musics",
                    json={
                        "length": czas_trwania,
                        "tempo": "fast" if energia > 0.7 else ("medium" if energia > 0.4 else "slow"),
                        "genre": mapowanie_gatunkow.get(gatunek, "Cinematic"),
                        "mood": opis[:100],
                        "bpm": tempo,
                    },
                    timeout=60.0,
                )
                odpowiedz.raise_for_status()
                dane = odpowiedz.json()
                # Pobierz plik audio
                async with klient.get(dane["audio_url"]) as audio:
                    return await audio.aread()

        except (ImportError, Exception) as e:
            logger.warning("SOUNDRAW niedostępny – symulacja", blad=str(e))
            await asyncio.sleep(1.0)
            return b"FAKE_MUSIC_SOUNDRAW"

    async def _beatoven(self, opis: str, czas_trwania: int, gatunek: str) -> bytes:
        """Generuje muzykę przez Beatoven.ai API."""
        # TODO: Implementacja przez Beatoven.ai API
        await asyncio.sleep(2.0)
        return b"FAKE_MUSIC_BEATOVEN"

    async def _ace_step(self, opis: str, czas_trwania: int, gatunek: str) -> bytes:
        """
        Generuje muzykę przez ACE-Step v1.5 (lokalnie lub przez API).

        ACE-Step v1.5 (styczeń 2026):
        - 4-minutowy utwór klasy komercyjnej w ~20s na A100
        - Działa na RTX 3060 12GB z optymalizacjami
        - Klonowanie głosu, edycja tekstów, LoRA fine-tuning
        - Format: text prompt → audio (MP3/WAV)

        Przykład wywołania lokalnego:
        python ace_step/inference.py \
            --prompt "energetic electronic music, 120 bpm, uplifting" \
            --duration 60 \
            --output music.mp3
        """
        try:
            import httpx

            async with httpx.AsyncClient() as klient:
                odpowiedz = await klient.post(
                    "http://ace-step-server:8080/generate",
                    json={
                        "prompt": f"{gatunek} music: {opis}",
                        "duration": czas_trwania,
                        "format": "mp3",
                    },
                    timeout=120.0,
                )
                odpowiedz.raise_for_status()
                return odpowiedz.content

        except Exception as e:
            logger.warning("ACE-Step niedostępny – symulacja", blad=str(e))
            await asyncio.sleep(3.0)
            return b"FAKE_MUSIC_ACESTEP"

    async def _mubert(self, opis: str, czas_trwania: int, gatunek: str, energia: float) -> bytes:
        """Generuje muzykę przez Mubert API."""
        # TODO: Implementacja przez Mubert API
        await asyncio.sleep(1.5)
        return b"FAKE_MUSIC_MUBERT"

    async def _musicgen(self, opis: str, czas_trwania: int) -> bytes:
        """Generuje muzykę przez Meta MusicGen (lokalnie)."""
        # TODO: Implementacja przez transformers + MusicGen
        await asyncio.sleep(5.0)
        return b"FAKE_MUSIC_MUSICGEN"
