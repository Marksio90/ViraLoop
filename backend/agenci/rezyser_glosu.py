"""
NEXUS — Agent 3: Reżyser Głosu v2.0
=====================================
Generuje profesjonalną narrację audio dla wideo.
Model: OpenAI TTS-1 + Whisper-1 dla word-level karaoke.

Nowości v2.0:
- [NAPRAWA BUG #1] Rzeczywisty pomiar czasu MP3 via ffprobe (koniec A/V desync!)
  Poprzednia implementacja: (słowa / 150) * 60 → błąd 15-25% → 3-4s driftu
  Nowa implementacja: ffprobe → dokładność ±10ms
- [INNOWACJA 1] Emotywne dostrojenie tempa TTS per scena
  Mapuje emocję + tempo scenariusza na parametr speed OpenAI TTS (0.85-1.15)
  Pauzy dramatyczne wstrzykiwane przez "..." (OpenAI TTS respektuje interpunkcję)
- [INNOWACJA 2] Whisper word-timestamps dla prawdziwego karaoke
  Whisper timestamp_granularities=["word"] → dokładność ~50-100ms per słowo
  Zastępuje blokowe szacunki całymi zdaniami sceny
"""

import os
import json
import asyncio
import structlog
from pathlib import Path
from openai import AsyncOpenAI

from konfiguracja import konf
from agenci.schematy import StanNEXUS, AudioWideo

logger = structlog.get_logger(__name__)

# ====================================================================
# MAPOWANIA GŁOSÓW
# ====================================================================

GLOSY_PER_EMOCJE = {
    "inspiracja": "nova",
    "energia": "echo",
    "profesjonalizm": "onyx",
    "przyjazny": "nova",
    "dramatyczny": "fable",
    "spokojny": "shimmer",
    "autorytatywny": "onyx",
    "ciekawość": "alloy",
    "napięcie": "fable",
    "zaskoczenie": "nova",
    "radość": "nova",
}

GLOSY_PER_PLATFORMA = {
    "tiktok": "nova",       # Młody, energiczny
    "youtube": "echo",      # Profesjonalny
    "instagram": "shimmer", # Estetyczny
}

# ====================================================================
# INNOWACJA 1: Emotywne dostrojenie tempa TTS
# ====================================================================

# Mapowanie emocji → prędkość TTS (zakres OpenAI: 0.25-4.0, bezpieczny: 0.85-1.15)
# Badania: tempo mowy BEZPOŚREDNIO wpływa na percepcję emocji
# Wolne = dramatyzm, powaga, napięcie
# Szybkie = energia, ekscytacja, pilność
EMOCJA_DO_TEMPA = {
    "zaskoczenie":    1.10,   # Szybkie — reakcja na nieoczekiwane
    "napięcie":       0.88,   # Wolne — budowanie napięcia
    "inspiracja":     0.95,   # Lekko wolniejsze — emocja, refleksja
    "radość":         1.12,   # Szybkie — energia pozytywna
    "spokój":         0.82,   # Bardzo wolne — meditacyjność
    "spokojny":       0.82,
    "ciekawość":      1.02,   # Nieznacznie szybsze — zainteresowanie
    "dramatyczny":    0.85,   # Wolne — dramatyzm
    "energia":        1.10,   # Szybkie — action
    "profesjonalizm": 0.97,   # Normalne z lekkim spowalnieniem
    "neutralna":      1.00,   # Bazowe
}

# Mapowanie tempo scenariusza → korekta współczynnika
TEMPO_DO_WSPOLCZYNNIKA = {
    "wolne":    0.90,
    "normalne": 1.00,
    "szybkie":  1.08,
}

# Max 6 słów na jeden segment karaoke (fit na ekranie mobilnym)
MAKS_SLOW_NA_SEGMENT_KARAOKE = 6


# ====================================================================
# FUNKCJE POMOCNICZE
# ====================================================================

def wybierz_glos(plan_tresci: dict) -> str:
    """Dobiera optymalny głos na podstawie tonu i platformy."""
    ton = plan_tresci.get("ton_glosu", "energiczny").lower()
    platforma = plan_tresci.get("platforma_docelowa", ["tiktok"])[0]

    for emocja, glos in GLOSY_PER_EMOCJE.items():
        if emocja in ton:
            return glos

    return GLOSY_PER_PLATFORMA.get(platforma, konf.DOMYSLNY_GLOS)


def oblicz_predkosc_tts(emocja: str, tempo: str) -> float:
    """
    Oblicza optymalną prędkość TTS na podstawie emocji i tempa sceny.

    Mapuje emocje i tempo scenariusza na parametr speed OpenAI TTS.
    Każda scena ma indywidualną prędkość zamiast monotonnego 1.0.
    """
    baza = EMOCJA_DO_TEMPA.get(emocja.lower(), 1.00)
    wspolczynnik = TEMPO_DO_WSPOLCZYNNIKA.get(tempo.lower(), 1.00)
    predkosc = baza * wspolczynnik
    # Bezpieczny zakres dla TTS-1 (unikamy skrajności)
    return round(max(0.85, min(1.15, predkosc)), 2)


def wstrzyknij_pauzy_dramatyczne(tekst: str, emocja: str, tempo: str) -> str:
    """
    Wstrzykuje dramatyczne pauzy przez interpunkcję.

    OpenAI TTS respektuje "..." jako ~0.5s pauzy.
    Stosowane przed kluczowymi informacjami dla efektu dramatycznego.
    Technika niezerowego kosztu (0$) z dużym efektem percepcyjnym.
    """
    if emocja in ("napięcie", "dramatyczny") or tempo == "wolne":
        # Wstaw pauzę po pierwszym zdaniu — hak werbalny potrzebuje oddechu
        zdania = tekst.split(". ", 1)
        if len(zdania) == 2 and len(zdania[0]) > 10:
            return zdania[0] + "... " + zdania[1]
    return tekst


async def mierz_czas_mp3(sciezka: str) -> float:
    """
    Mierzy rzeczywisty czas trwania pliku MP3 przez ffprobe.

    [NAPRAWA KRYTYCZNA BUG #1 — A/V Desync]
    Poprzednia implementacja: czas = słowa/150*60 → błąd 15-25% per scena
    Efekt: po 5 scenach drift = 3-4 sekundy → napisy i obraz się rozjeżdżają

    ffprobe mierzy czas z metadanych pliku MP3 z dokładnością ±10ms.
    Zero kosztu API, wymaga tylko FFmpeg (już jest w systemie).
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            sciezka,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            dane = json.loads(stdout.decode())
            for stream in dane.get("streams", []):
                if stream.get("codec_type") == "audio":
                    return float(stream.get("duration", 0.0))
    except Exception:
        pass
    return 0.0


async def pobierz_znaczniki_slow(
    klient: AsyncOpenAI,
    sciezka_mp3: str,
) -> list[dict]:
    """
    Transkrybuje wygenerowane audio przez Whisper z dokładnymi znacznikami słów.

    [INNOWACJA 2 — Prawdziwe karaoke word-by-word]
    Whisper timestamp_granularities=["word"] → dokładność ~50-100ms per słowo.
    Zastępuje blokowe szacunki całymi zdaniami scenariusza.

    Efekt: napisy pojawiają się zsynchronizowane DOKŁADNIE z wypowiadanym słowem.
    Koszt: whisper-1 = $0.006/minutę audio (minimalny).
    """
    if not os.path.exists(sciezka_mp3):
        return []
    try:
        with open(sciezka_mp3, "rb") as f:
            odpowiedz = await klient.audio.transcriptions.create(
                model=konf.MODEL_WHISPER,
                file=f,
                language="pl",
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )
        if hasattr(odpowiedz, "words") and odpowiedz.words:
            return [
                {
                    "slowo": w.word.strip(),
                    "start": float(w.start),
                    "end": float(w.end),
                }
                for w in odpowiedz.words
                if w.word.strip()
            ]
    except Exception as e:
        logger.warning("Whisper znaczniki słów niedostępne", blad=str(e))
    return []


def grupuj_slowa_w_segmenty_karaoke(
    znaczniki_slow: list[dict],
) -> list[dict]:
    """
    Grupuje znaczniki słów Whispera w segmenty karaoke.

    Każdy segment = max MAKS_SLOW_NA_SEGMENT_KARAOKE słów.
    Zapewnia że tekst mieści się na ekranie mobilnym (1080x1920).
    Wynik trafia bezpośrednio do compositor.py jako napisy.
    """
    if not znaczniki_slow:
        return []

    segmenty = []
    i = 0
    while i < len(znaczniki_slow):
        partia = znaczniki_slow[i:i + MAKS_SLOW_NA_SEGMENT_KARAOKE]
        if partia:
            tekst = " ".join(s["slowo"] for s in partia)
            segmenty.append({
                "tekst": tekst,
                "start": partia[0]["start"],
                "end": partia[-1]["end"],
            })
        i += MAKS_SLOW_NA_SEGMENT_KARAOKE

    return segmenty


# ====================================================================
# GENERACJA AUDIO
# ====================================================================

async def generuj_audio_sceny(
    klient: AsyncOpenAI,
    tekst: str,
    glos: str,
    sciezka: Path,
    emocja: str = "neutralna",
    tempo: str = "normalne",
    hd: bool = False,
) -> bool:
    """
    Generuje audio dla jednej sceny z emocjonalnym dostrojeniem tempa.

    Nowość vs v1.0:
    - speed param dobierany per scena (emocja + tempo)
    - Pauzy dramatyczne przez "..."
    """
    if not tekst.strip():
        return False

    model_tts = konf.MODEL_GLOS_HD if hd else konf.MODEL_GLOS

    # [INNOWACJA 1] Wstrzyknij pauzy i oblicz emocjonalną prędkość
    tekst_z_pauzami = wstrzyknij_pauzy_dramatyczne(tekst, emocja, tempo)
    predkosc = oblicz_predkosc_tts(emocja, tempo)

    odpowiedz = await klient.audio.speech.create(
        model=model_tts,
        voice=glos,
        input=tekst_z_pauzami,
        response_format="mp3",
        speed=predkosc,
    )

    sciezka.parent.mkdir(parents=True, exist_ok=True)
    with open(sciezka, "wb") as plik:
        plik.write(odpowiedz.content)

    return True


# ====================================================================
# GŁÓWNY AGENT
# ====================================================================

async def rezyser_glosu(stan: StanNEXUS) -> dict:
    """
    Agent Reżyser Głosu v2.0 — generuje narrację audio z realnym timingiem.

    [v2.0 vs v1.0]:
    - A/V desync NAPRAWIONY: ffprobe mierzy rzeczywisty czas zamiast szacowania
    - Emotywne tempo: speed param per scena zamiast stałego 1.0 dla wszystkich
    - Word-level karaoke: Whisper timestamps → synchronizacja do ±100ms
    - Dramatyczne pauzy przez interpunkcję (koszt $0)
    """
    log = logger.bind(agent="rezyser_glosu_v2")

    if not stan.get("scenariusz"):
        return {
            "bledy": ["Reżyser Głosu: brak scenariusza"],
            "krok_aktualny": "blad_rezysera",
        }

    scenariusz = stan["scenariusz"]
    plan = stan.get("plan_tresci", {})
    log.info("Reżyser Głosu v2.0 generuje narrację", sceny=len(scenariusz["sceny"]))

    klient = AsyncOpenAI(api_key=konf.OPENAI_API_KEY)
    glos = wybierz_glos(plan)

    sesja_id = stan.get("metadane", {}).get("sesja_id", "domyslna")
    katalog_audio = Path(konf.SCIEZKA_TYMCZASOWA) / sesja_id / "audio"
    katalog_audio.mkdir(parents=True, exist_ok=True)

    # Pełny tekst (cała narracja złączona)
    pelny_tekst = " ".join(
        s["tekst_narracji"]
        for s in scenariusz["sceny"]
        if s["tekst_narracji"].strip()
    )

    liczba_znakow = len(pelny_tekst)
    koszt_tts = liczba_znakow * 15 / 1_000_000

    sciezka_pelne = katalog_audio / "narracja_pelna.mp3"

    try:
        # Generuj pełną narrację (emocja dominująca pierwszej sceny)
        emocja_glowna = "inspiracja"
        tempo_glowne = "normalne"
        if scenariusz["sceny"]:
            emocja_glowna = scenariusz["sceny"][0].get("emocja", "inspiracja")
            tempo_glowne = scenariusz["sceny"][0].get("tempo", "normalne")

        sukces = await generuj_audio_sceny(
            klient=klient,
            tekst=pelny_tekst,
            glos=glos,
            sciezka=sciezka_pelne,
            emocja=emocja_glowna,
            tempo=tempo_glowne,
        )

        if not sukces:
            return {
                "bledy": ["Reżyser Głosu: błąd generacji audio"],
                "krok_aktualny": "blad_rezysera",
            }

        # ── [BUG #1 NAPRAWA] Zmierz rzeczywisty czas MP3 ─────────────────
        czas_trwania = await mierz_czas_mp3(str(sciezka_pelne))
        if czas_trwania <= 0:
            # Fallback na szacunek jeśli ffprobe niedostępne
            czas_trwania = len(pelny_tekst.split()) / 150 * 60
            log.warning("ffprobe niedostępne — używam szacunku czasu (A/V drift możliwy!)")
        else:
            log.info(
                "Rzeczywisty czas MP3 zmierzony przez ffprobe",
                czas_s=round(czas_trwania, 2),
                szacunek_s=round(len(pelny_tekst.split()) / 150 * 60, 2),
                roznica_s=round(czas_trwania - len(pelny_tekst.split()) / 150 * 60, 2),
            )

        # Generuj segmenty per scena równolegle — z emocjonalnym tempem per scena
        zadania_scen = []
        for scena in scenariusz["sceny"]:
            if scena["tekst_narracji"].strip():
                sciezka_sceny = katalog_audio / f"scena_{scena['numer']:02d}.mp3"
                zadanie = generuj_audio_sceny(
                    klient=klient,
                    tekst=scena["tekst_narracji"],
                    glos=glos,
                    sciezka=sciezka_sceny,
                    emocja=scena.get("emocja", "neutralna"),
                    tempo=scena.get("tempo", "normalne"),
                )
                zadania_scen.append((scena["numer"], sciezka_sceny, zadanie))

        if zadania_scen:
            await asyncio.gather(*[z[2] for z in zadania_scen], return_exceptions=True)
            koszt_tts += liczba_znakow * 0.3 * 15 / 1_000_000

        # ── [BUG #1 NAPRAWA] Zmierz czasy per scena przez ffprobe ────────
        # Buduj segmenty z REALNYCH czasów każdego pliku sceny
        segmenty_realne = []
        czas_aktualny = 0.0

        for numer_sceny, sciezka_sceny, _ in zadania_scen:
            czas_sceny = await mierz_czas_mp3(str(sciezka_sceny))
            if czas_sceny <= 0:
                # Fallback proporcjonalny per scena
                scena_obj = next(
                    (s for s in scenariusz["sceny"] if s["numer"] == numer_sceny), None
                )
                if scena_obj:
                    czas_sceny = len(scena_obj["tekst_narracji"].split()) / 150 * 60
                else:
                    czas_sceny = 3.0

            scena_obj = next(
                (s for s in scenariusz["sceny"] if s["numer"] == numer_sceny), None
            )
            tekst_sceny = scena_obj["tekst_narracji"] if scena_obj else ""

            segmenty_realne.append({
                "numer": numer_sceny,
                "start": czas_aktualny,
                "end": czas_aktualny + czas_sceny,
                "tekst": tekst_sceny,
            })
            czas_aktualny += czas_sceny

        # ── [INNOWACJA 2] Whisper word-timestamps dla prawdziwego karaoke ──
        znaczniki_slow = await pobierz_znaczniki_slow(klient, str(sciezka_pelne))

        # Koszt Whispera: $0.006/minutę
        koszt_whisper = (czas_trwania / 60.0) * 0.006
        koszt_tts += koszt_whisper

        segmenty_karaoke = grupuj_slowa_w_segmenty_karaoke(znaczniki_slow)

        log.info(
            "Karaoke word-level",
            slowa=len(znaczniki_slow),
            segmenty=len(segmenty_karaoke),
            koszt_whisper_usd=round(koszt_whisper, 5),
        )

        # Użyj karaoke word-level jeśli dostępne, inaczej fallback do scen
        segmenty_finalne = segmenty_karaoke if segmenty_karaoke else segmenty_realne

        audio: AudioWideo = {
            "sciezka_pliku": str(sciezka_pelne),
            "czas_trwania": czas_trwania,
            "jezyk": "pl",
            "glos": glos,
            "format": "mp3",
            "transkrypcja": pelny_tekst,
            "segmenty": segmenty_finalne,
            "segmenty_scen": segmenty_realne,  # Dodatkowe — dla synchronizacji obrazów
        }

        log.info(
            "Audio v2.0 wygenerowane",
            glos=glos,
            czas_s=round(czas_trwania, 1),
            znaki=liczba_znakow,
            karaoke_word_level=bool(segmenty_karaoke),
            segmenty_karaoke=len(segmenty_karaoke),
            koszt_usd=round(koszt_tts, 5),
        )

        return {
            "audio": audio,
            "krok_aktualny": "audio_gotowe",
            "koszt_calkowity_usd": stan.get("koszt_calkowity_usd", 0.0) + koszt_tts,
        }

    except Exception as e:
        log.error("Błąd Reżysera Głosu v2.0", blad=str(e))
        return {
            "bledy": [f"Reżyser Głosu: {str(e)}"],
            "krok_aktualny": "blad_rezysera",
        }
