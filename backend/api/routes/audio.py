"""
ViraLoop – Router API audio

Obsługuje syntezę głosu, generowanie muzyki i transkrypcję.
"""

from uuid import UUID, uuid4
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

router = APIRouter()


class ZadanieSyntezyGlosu(BaseModel):
    """Żądanie syntezy mowy z tekstu (TTS)."""

    tekst: str = Field(..., min_length=1, max_length=5000, description="Tekst do wypowiedzenia")
    id_glosu: str = Field(
        default="pl-narrator-profesjonalny",
        description="ID głosu (ElevenLabs, FishAudio lub wbudowany)",
    )
    silnik: str = Field(
        default="elevenlabs",
        description="Silnik TTS",
        examples=["elevenlabs", "fishaudio", "chatterbox", "kokoro"],
    )
    jezyk: str = Field(default="pl", description="Język syntezy (ISO 639-1)")
    emocja: str | None = Field(
        default=None,
        description="Znacznik emocji",
        examples=["[entuzjastyczny]", "[spokojny]", "[dramatyczny]"],
    )
    szybkosc: float = Field(default=1.0, ge=0.5, le=2.0, description="Szybkość mowy")


class ZadanieGeneracjiMuzyki(BaseModel):
    """Żądanie wygenerowania muzyki tła."""

    opis: str = Field(..., min_length=5, max_length=500, description="Opis nastroju i stylu muzyki")
    czas_trwania: int = Field(default=30, ge=5, le=300, description="Czas trwania w sekundach")
    silnik: str = Field(
        default="soundraw",
        description="Silnik generowania muzyki",
        examples=["soundraw", "beatoven", "ace-step", "mubert"],
    )
    tempo: int | None = Field(default=None, ge=60, le=200, description="Tempo w BPM")
    gatunek: str = Field(
        default="ambient",
        description="Gatunek muzyczny",
        examples=["ambient", "electronic", "orkiestra", "hip-hop", "cinematic"],
    )
    bez_praw_autorskich: bool = Field(
        default=True,
        description="Czy wymagana jest licencja wolna od praw autorskich",
    )


class ZadanieTranskrypcji(BaseModel):
    """Żądanie transkrypcji audio na tekst."""

    jezyk: str | None = Field(
        default=None,
        description="Język audio (None = automatyczne wykrycie)",
    )
    format_wyjsciowy: str = Field(
        default="srt",
        description="Format napisów",
        examples=["srt", "vtt", "json", "txt"],
    )
    model: str = Field(
        default="faster-whisper-large-v3",
        description="Model transkrypcji",
    )


@router.post("/synteza-glosu", summary="Synteza głosu (TTS)")
async def syntezuj_glos(
    zadanie: ZadanieSyntezyGlosu,
    zadania_w_tle: BackgroundTasks,
):
    """
    Generuje plik audio z tekstu przy użyciu wybranego silnika TTS.

    Priorytety silników:
    - ElevenLabs v3: najwyższa jakość, 70+ języków, tagi emocji
    - FishAudio S1: najlepsza cena/jakość, WER 0.8%, #1 na TTS Arena V2
    - Chatterbox: 23 języki, MIT, 63% preferowany nad ElevenLabs w testach ślepych
    - Kokoro: 82M parametrów, CPU-friendly, <$1 za milion znaków
    """
    id_zadania = uuid4()

    # Mapowanie silnika na klienta API
    klienci_tts = {
        "elevenlabs": "ElevenLabsKlient",
        "fishaudio": "FishAudioKlient",
        "chatterbox": "ChatterboxKlient",
        "kokoro": "KokoroKlient",
    }

    if zadanie.silnik not in klienci_tts:
        raise HTTPException(
            status_code=400,
            detail=f"Nieznany silnik TTS: {zadanie.silnik}. Dostępne: {list(klienci_tts.keys())}",
        )

    # TODO: Uruchom syntezę przez odpowiedni klient
    zadania_w_tle.add_task(
        _syntezuj_w_tle,
        id_zadania=id_zadania,
        zadanie=zadanie,
    )

    return {
        "id_zadania": str(id_zadania),
        "status": "przetwarzanie",
        "silnik": zadanie.silnik,
        "szacowany_czas_sekund": max(5, len(zadanie.tekst) // 200),
    }


@router.post("/generuj-muzyke", summary="Generowanie muzyki tła")
async def generuj_muzyke(
    zadanie: ZadanieGeneracjiMuzyki,
    zadania_w_tle: BackgroundTasks,
):
    """
    Generuje muzykę tła bez praw autorskich dla wideo.

    Rekomendowane silniki dla platformy komercyjnej:
    - SOUNDRAW / Beatoven.ai: 100% bezpieczne prawnie, licencja wieczysta
    - ACE-Step 1.5: open-source, 4-minutowy utwór w ~20s na A100
    - Mubert: API do muzyki w czasie rzeczywistym dopasowanej do nastroju wideo
    """
    id_zadania = uuid4()

    if zadanie.bez_praw_autorskich and zadanie.silnik not in ("soundraw", "beatoven", "mubert", "tempolr"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Silnik '{zadanie.silnik}' może generować muzykę z ograniczeniami praw autorskich. "
                "Użyj: soundraw, beatoven, mubert lub tempolr dla bezpiecznej muzyki komercyjnej."
            ),
        )

    zadania_w_tle.add_task(
        _generuj_muzyke_w_tle,
        id_zadania=id_zadania,
        zadanie=zadanie,
    )

    return {
        "id_zadania": str(id_zadania),
        "status": "przetwarzanie",
        "silnik": zadanie.silnik,
        "szacowany_czas_sekund": zadanie.czas_trwania // 10 + 5,
    }


@router.post("/transkrypcja", summary="Transkrypcja audio na tekst")
async def transkrybuj_audio(
    plik_audio: UploadFile = File(..., description="Plik audio do transkrypcji (MP3, WAV, M4A)"),
    jezyk: str | None = None,
    format_wyjsciowy: str = "srt",
):
    """
    Transkrybuje plik audio na tekst lub napisy używając faster-whisper.

    FFmpeg 8.0 zawiera wbudowaną integrację Whisper umożliwiającą generację
    napisów SRT jedną komendą z detekcją aktywności głosowej (VAD).
    """
    dozwolone_formaty = {"mp3", "wav", "m4a", "ogg", "flac", "webm"}
    rozszerzenie = plik_audio.filename.rsplit(".", 1)[-1].lower()

    if rozszerzenie not in dozwolone_formaty:
        raise HTTPException(
            status_code=400,
            detail=f"Nieobsługiwany format pliku: .{rozszerzenie}. Dozwolone: {dozwolone_formaty}",
        )

    id_zadania = uuid4()

    # TODO: Zapisz plik tymczasowo i uruchom faster-whisper
    return {
        "id_zadania": str(id_zadania),
        "status": "przetwarzanie",
        "model": "faster-whisper-large-v3",
        "jezyk_wykryty": jezyk or "auto",
        "format_wyjsciowy": format_wyjsciowy,
    }


@router.post("/klonuj-glos", summary="Klonowanie głosu")
async def klonuj_glos(
    probka_audio: UploadFile = File(
        ...,
        description="Próbka głosu do sklonowania (min. 10s, zalecane 30s)",
    ),
    nazwa: str = "Mój sklonowany głos",
):
    """
    Klonuje głos z próbki audio.

    ElevenLabs: klonowanie głosu w 73 językach z jednej próbki.
    XTTS-v2 (open-source): 17 języków, 85-95% podobieństwo głosu z 10s próbki.
    """
    id_glosu = uuid4()

    # TODO: Implementacja klonowania przez ElevenLabs lub XTTS-v2
    return {
        "id_glosu": str(id_glosu),
        "nazwa": nazwa,
        "status": "w_trakcie_klonowania",
        "komunikat": "Klonowanie głosu zainicjowane. Wynik dostępny za ok. 2 minuty.",
    }


# ---- Funkcje pomocnicze (uruchamiane w tle) ----


async def _syntezuj_w_tle(id_zadania: UUID, zadanie: ZadanieSyntezyGlosu) -> None:
    """Uruchamia syntezę głosu w tle."""
    # TODO: Implementacja przez odpowiedni klient TTS
    pass


async def _generuj_muzyke_w_tle(id_zadania: UUID, zadanie: ZadanieGeneracjiMuzyki) -> None:
    """Uruchamia generowanie muzyki w tle."""
    # TODO: Implementacja przez wybrany silnik muzyki
    pass
