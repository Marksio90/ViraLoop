"""
ViraLoop – Synteza głosu (TTS)

Obsługuje cztery silniki TTS w ramach strategii czterech warstw:
1. ElevenLabs v3 – premium, 70+ języków, tagi emocji
2. FishAudio S1 – #1 TTS Arena V2, WER 0.8%, ~6x tańszy od ElevenLabs
3. Chatterbox (Resemble AI) – 23 języki, MIT, 63% preferowany w testach ślepych
4. Kokoro – 82M params, CPU-friendly, <$1/milion znaków (angielski)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class SilnikTTS(str, Enum):
    """Dostępne silniki syntezy głosu."""

    ELEVENLABS = "elevenlabs"
    FISHAUDIO = "fishaudio"
    CHATTERBOX = "chatterbox"
    KOKORO = "kokoro"


@dataclass
class KonfiguracacjaTTS:
    """Konfiguracja silnika TTS."""

    id: str
    nazwa: str
    jezyki: list[str]
    koszt_za_1k_znakow_usd: float
    latencja_ttfb_ms: int  # czas do pierwszego bajtu
    klonowanie_glosu: bool
    min_probka_klonowania_s: int  # sekundy próbki do klonowania
    licencja: str
    opis: str


SILNIKI_TTS: dict[str, KonfiguracacjaTTS] = {
    SilnikTTS.ELEVENLABS: KonfiguracacjaTTS(
        id="elevenlabs",
        nazwa="ElevenLabs Eleven v3",
        jezyki=["pl", "en", "de", "fr", "es", "it", "pt", "nl", "ru", "zh", "ja", "ko"],  # 70+
        koszt_za_1k_znakow_usd=0.17,  # Multilingual v2 na planie Scale
        latencja_ttfb_ms=75,  # Flash v2.5
        klonowanie_glosu=True,
        min_probka_klonowania_s=30,
        licencja="Komercyjna",
        opis=(
            "Standard rynkowy. Eleven v3 (alpha) obsługuje tagi emocji: [szepcze], [entuzjastyczny]. "
            "Text-to-Dialogue z JSON dla wielu głosów. Flash v2.5: 75ms TTFB dla czasu rzeczywistego. "
            "Klonowanie głosu w 73 językach z jednej próbki."
        ),
    ),
    SilnikTTS.FISHAUDIO: KonfiguracacjaTTS(
        id="fishaudio",
        nazwa="FishAudio S1",
        jezyki=["pl", "en", "zh", "ja", "ko", "de", "fr", "es"],  # 50+
        koszt_za_1k_znakow_usd=0.03,  # ~6x tańszy od ElevenLabs
        latencja_ttfb_ms=200,
        klonowanie_glosu=True,
        min_probka_klonowania_s=10,
        licencja="Komercyjna (API)",
        opis=(
            "#1 na TTS Arena V2. WER 0.8% (najniższy na rynku). "
            "Zero-shot klonowanie głosu z 10-30s próbki. 50+ markerów emocji. "
            "~6x tańszy od ElevenLabs przy porównywalnej jakości."
        ),
    ),
    SilnikTTS.CHATTERBOX: KonfiguracacjaTTS(
        id="chatterbox",
        nazwa="Chatterbox (Resemble AI)",
        jezyki=["pl", "en", "de", "fr", "es", "it", "pt", "nl", "ru", "ar", "hi", "tr"],  # 23
        koszt_za_1k_znakow_usd=0.02,
        latencja_ttfb_ms=200,  # Turbo: <200ms
        klonowanie_glosu=True,
        min_probka_klonowania_s=10,
        licencja="MIT",
        opis=(
            "23 języki, licencja MIT (samodzielny hosting). "
            "63.75% preferowany nad ElevenLabs w testach ślepych. "
            "Turbo: <200ms latencja. Idealne gdy ElevenLabs nie obsługuje języka."
        ),
    ),
    SilnikTTS.KOKORO: KonfiguracacjaTTS(
        id="kokoro",
        nazwa="Kokoro",
        jezyki=["en"],  # angielski
        koszt_za_1k_znakow_usd=0.001,  # <$1/milion znaków
        latencja_ttfb_ms=500,
        klonowanie_glosu=False,
        min_probka_klonowania_s=0,
        licencja="Apache 2.0",
        opis=(
            "82M parametrów, Apache 2.0. Działa na CPU. "
            "<$1 za milion znaków – idealny do masowej narracji po angielsku. "
            "Nie obsługuje klonowania głosu ani wielojęzyczności."
        ),
    ),
}


class SyntezatorGlosu:
    """
    Zarządza syntezą głosu przez różne silniki TTS.

    Strategia wyboru silnika dla ViraLoop:
    - Produkcja premium: ElevenLabs Multilingual v2
    - Główny silnik ekonomiczny: FishAudio S1
    - Języki nieobsługiwane przez Fish: Chatterbox (self-hosted)
    - Masowa narracja angielska: Kokoro
    """

    def __init__(self, domyslny_silnik: SilnikTTS = SilnikTTS.FISHAUDIO):
        self.domyslny_silnik = domyslny_silnik

    def wybierz_silnik(self, jezyk: str, wymaga_klonowania: bool, budzet_oszczedny: bool) -> SilnikTTS:
        """
        Automatycznie wybiera optymalny silnik TTS.

        Logika:
        1. Jeśli angielski i brak klonowania i oszczędny budżet → Kokoro
        2. Jeśli język obsługiwany przez FishAudio → FishAudio S1
        3. Jeśli język obsługiwany przez Chatterbox → Chatterbox
        4. Fallback → ElevenLabs (najszersze pokrycie językowe)
        """
        if jezyk == "en" and not wymaga_klonowania and budzet_oszczedny:
            return SilnikTTS.KOKORO

        jezyki_fish = SILNIKI_TTS[SilnikTTS.FISHAUDIO].jezyki
        if jezyk in jezyki_fish:
            return SilnikTTS.FISHAUDIO

        jezyki_chatterbox = SILNIKI_TTS[SilnikTTS.CHATTERBOX].jezyki
        if jezyk in jezyki_chatterbox:
            return SilnikTTS.CHATTERBOX

        return SilnikTTS.ELEVENLABS

    async def syntezuj(
        self,
        tekst: str,
        id_glosu: str,
        jezyk: str = "pl",
        silnik: SilnikTTS | None = None,
        emocja: str | None = None,
        szybkosc: float = 1.0,
    ) -> bytes:
        """
        Syntezuje mowę z tekstu.

        Args:
            tekst: Tekst do wypowiedzenia
            id_glosu: ID głosu lub "domyslny"
            jezyk: Kod języka ISO 639-1
            silnik: Wybrany silnik (None = automatyczny wybór)
            emocja: Znacznik emocji np. "[entuzjastyczny]", "[spokojny]"
            szybkosc: Szybkość mowy (0.5-2.0)

        Returns:
            Dane binarne pliku MP3
        """
        wybrany_silnik = silnik or self.wybierz_silnik(
            jezyk=jezyk,
            wymaga_klonowania=id_glosu != "domyslny",
            budzet_oszczedny=False,
        )

        logger.info(
            "Synteza głosu",
            silnik=wybrany_silnik,
            jezyk=jezyk,
            dlugosc_znakow=len(tekst),
            koszt_usd=self._szacuj_koszt(tekst, wybrany_silnik),
        )

        if wybrany_silnik == SilnikTTS.ELEVENLABS:
            return await self._elevenlabs(tekst, id_glosu, jezyk, emocja, szybkosc)
        elif wybrany_silnik == SilnikTTS.FISHAUDIO:
            return await self._fishaudio(tekst, id_glosu, jezyk, szybkosc)
        elif wybrany_silnik == SilnikTTS.CHATTERBOX:
            return await self._chatterbox(tekst, id_glosu, jezyk, szybkosc)
        elif wybrany_silnik == SilnikTTS.KOKORO:
            return await self._kokoro(tekst, id_glosu, szybkosc)
        else:
            raise ValueError(f"Nieznany silnik TTS: {wybrany_silnik}")

    async def _elevenlabs(
        self,
        tekst: str,
        id_glosu: str,
        jezyk: str,
        emocja: str | None,
        szybkosc: float,
    ) -> bytes:
        """Synteza przez ElevenLabs API."""
        try:
            from elevenlabs import ElevenLabs, VoiceSettings

            klient = ElevenLabs()

            # Dodaj tag emocji jeśli podany
            tekst_z_emocja = f"{emocja} {tekst}" if emocja else tekst

            audio = klient.text_to_speech.convert(
                voice_id=id_glosu if id_glosu != "domyslny" else "XB0fDUnXU5powFXDhCwa",
                text=tekst_z_emocja,
                model_id="eleven_multilingual_v2",
                voice_settings=VoiceSettings(
                    stability=0.71,
                    similarity_boost=0.85,
                    speed=szybkosc,
                ),
            )

            return b"".join(audio)

        except ImportError:
            logger.warning("elevenlabs SDK niedostępny – symulacja")
            await asyncio.sleep(0.5)
            return b"FAKE_AUDIO_DATA_ELEVENLABS"

    async def _fishaudio(self, tekst: str, id_glosu: str, jezyk: str, szybkosc: float) -> bytes:
        """Synteza przez FishAudio S1 API."""
        try:
            import httpx

            async with httpx.AsyncClient() as klient:
                odpowiedz = await klient.post(
                    "https://api.fish.audio/v1/tts",
                    json={
                        "text": tekst,
                        "reference_id": id_glosu if id_glosu != "domyslny" else None,
                        "format": "mp3",
                        "mp3_bitrate": 192,
                        "normalize": True,
                        "latency": "normal",
                    },
                    timeout=30.0,
                )
                odpowiedz.raise_for_status()
                return odpowiedz.content

        except ImportError:
            await asyncio.sleep(0.3)
            return b"FAKE_AUDIO_DATA_FISHAUDIO"

    async def _chatterbox(self, tekst: str, id_glosu: str, jezyk: str, szybkosc: float) -> bytes:
        """Synteza przez Chatterbox (self-hosted lub Resemble API)."""
        # TODO: Implementacja przez Resemble AI API lub lokalny model
        await asyncio.sleep(0.5)
        return b"FAKE_AUDIO_DATA_CHATTERBOX"

    async def _kokoro(self, tekst: str, id_glosu: str, szybkosc: float) -> bytes:
        """Synteza przez Kokoro (Apache 2.0, CPU-friendly)."""
        # TODO: Implementacja przez kokoro-onnx
        await asyncio.sleep(0.2)
        return b"FAKE_AUDIO_DATA_KOKORO"

    def _szacuj_koszt(self, tekst: str, silnik: SilnikTTS) -> float:
        """Szacuje koszt syntezy w USD."""
        konfiguracja = SILNIKI_TTS[silnik]
        return round(len(tekst) / 1000 * konfiguracja.koszt_za_1k_znakow_usd, 6)

    async def klonuj_glos(
        self,
        probka_audio: bytes,
        nazwa: str,
        silnik: SilnikTTS = SilnikTTS.ELEVENLABS,
    ) -> str:
        """
        Klonuje głos z próbki audio.

        ElevenLabs: klonowanie w 73 językach z 30s próbki
        XTTS-v2 (open-source): 17 języków, 85-95% podobieństwo z 10s próbki
        """
        konfiguracja = SILNIKI_TTS[silnik]
        if not konfiguracja.klonowanie_glosu:
            raise ValueError(f"Silnik {silnik} nie obsługuje klonowania głosu")

        logger.info("Klonowanie głosu", silnik=silnik, nazwa=nazwa)

        if silnik == SilnikTTS.ELEVENLABS:
            try:
                from elevenlabs import ElevenLabs

                klient = ElevenLabs()
                glos = klient.clone(
                    name=nazwa,
                    files=[probka_audio],
                    description=f"Sklonowany głos: {nazwa}",
                )
                return glos.voice_id
            except ImportError:
                return f"fake_voice_id_{nazwa.lower().replace(' ', '_')}"
        else:
            # TODO: Implementacja klonowania przez XTTS-v2 lub FishAudio
            await asyncio.sleep(2.0)
            return f"fake_voice_id_{nazwa.lower().replace(' ', '_')}"
