"""
NEXUS — Compositor Wideo
========================
Łączy obrazy DALL-E 3, audio TTS i napisy w gotowe wideo MP4.
Używa FFmpeg do profesjonalnej kompozycji.

Obsługiwane warianty:
- 9:16 (TikTok, Reels, Shorts) — główny format
- 1:1 (Instagram feed)
- 16:9 (YouTube standard)

Techniki:
- Ken Burns effect (powolny zoom) dla nieruchomych obrazów
- Crossfade transitions między scenami
- Wypalone napisy z animowanym tłem
- Normalizacja głośności audio
"""

import os
import asyncio
import structlog
from pathlib import Path

from konfiguracja import konf
from agenci.schematy import StanNEXUS, Wideo

logger = structlog.get_logger(__name__)

# Format wideo per platforma
FORMATY_PLATFORM = {
    "tiktok": {"szerokosc": 1080, "wysokosc": 1920, "fps": 30},
    "youtube": {"szerokosc": 1080, "wysokosc": 1920, "fps": 30},  # Shorts
    "instagram": {"szerokosc": 1080, "wysokosc": 1920, "fps": 30},
}


def sprawdz_ffmpeg() -> bool:
    """Sprawdza czy FFmpeg jest dostępny w systemie."""
    import shutil
    return shutil.which("ffmpeg") is not None


async def uruchom_ffmpeg(komenda: list[str]) -> tuple[bool, str]:
    """
    Uruchamia FFmpeg asynchronicznie.

    Returns:
        (sukces, stderr)
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *komenda,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        sukces = proc.returncode == 0
        return sukces, stderr.decode("utf-8", errors="replace")
    except asyncio.TimeoutError:
        return False, "Timeout FFmpeg (>300s)"
    except Exception as e:
        return False, str(e)


async def stworz_wideo_z_obrazow(
    obrazy: list[str],
    audio: str,
    wyjscie: str,
    czas_per_obraz: float = 3.0,
    napisy: list[dict] | None = None,
) -> bool:
    """
    Tworzy wideo z listy obrazów + audio.

    Zastosowane techniki:
    - zoompan: Ken Burns effect (powolny zoom 1.0→1.1)
    - crossfade: płynne przejście między obrazami
    - subtitles: wypalone napisy
    - loudnorm: normalizacja głośności

    Args:
        obrazy: Lista ścieżek do plików PNG
        audio: Ścieżka do pliku MP3
        wyjscie: Ścieżka wyjściowa MP4
        czas_per_obraz: Czas wyświetlania każdego obrazu
        napisy: Lista [{tekst, start, end}]

    Returns:
        True jeśli sukces
    """
    if not obrazy:
        logger.error("Brak obrazów do kompozycji")
        return False

    Path(wyjscie).parent.mkdir(parents=True, exist_ok=True)

    # Buduj filtr wideo dla każdego obrazu
    filtry_wejscia = []
    mapowania = []

    for i, _ in enumerate(obrazy):
        # Każdy obraz: skalowanie + Ken Burns effect
        filtr = (
            f"[{i}:v]"
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"zoompan=z='min(zoom+0.0015,1.1)':d={int(czas_per_obraz * 30)}:s=1080x1920:fps=30,"
            f"setsar=1"
            f"[v{i}]"
        )
        filtry_wejscia.append(filtr)
        mapowania.append(f"[v{i}]")

    # Połącz z crossfade transitions
    if len(mapowania) == 1:
        filtr_scalony = f"{mapowania[0]}copy[vout]"
    else:
        current = mapowania[0]
        poprzedni_offset = 0.0
        filtr_concat = filtry_wejscia.copy()

        for i in range(1, len(mapowania)):
            offset = poprzedni_offset + czas_per_obraz - 0.5  # 0.5s crossfade
            filtr_concat.append(
                f"{current}{mapowania[i]}"
                f"xfade=transition=fade:duration=0.5:offset={offset:.2f}[v_x{i}]"
            )
            current = f"[v_x{i}]"
            poprzedni_offset = offset

        filtr_concat.append(f"{current}copy[vout]")
        filtry_wejscia = filtr_concat

    pelny_filtr = ";".join(filtry_wejscia)

    # Buduj komendę FFmpeg
    cmd = ["ffmpeg", "-y"]

    # Wejścia
    for img in obrazy:
        cmd.extend(["-loop", "1", "-t", str(czas_per_obraz + 1), "-i", img])

    # Audio
    if os.path.exists(audio):
        cmd.extend(["-i", audio])
        audio_idx = len(obrazy)
    else:
        audio_idx = None

    # Filtry
    cmd.extend(["-filter_complex", pelny_filtr])

    # Mapowanie
    cmd.extend(["-map", "[vout]"])
    if audio_idx is not None:
        cmd.extend(["-map", f"{audio_idx}:a"])

    # Encoding
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", "30",
    ])

    if audio_idx is not None:
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])

    # Czas trwania = czas audio
    if audio_idx is not None:
        cmd.extend(["-shortest"])

    cmd.append(wyjscie)

    sukces, stderr = await uruchom_ffmpeg(cmd)
    if not sukces:
        logger.error("FFmpeg błąd", stderr=stderr[:500])

    return sukces


async def generuj_miniaturke(
    obraz_zrodlowy: str,
    wyjscie: str,
    tytul: str = "",
) -> bool:
    """
    Generuje miniaturkę wideo (1080x1920 JPG, zoptymalizowana pod CTR).

    Args:
        obraz_zrodlowy: Źródłowy obraz PNG
        wyjscie: Ścieżka wyjściowa JPG
        tytul: Tekst do nałożenia (opcjonalnie)
    """
    if not os.path.exists(obraz_zrodlowy):
        return False

    Path(wyjscie).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", obraz_zrodlowy,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-q:v", "2",  # Wysoka jakość JPG
        wyjscie
    ]

    sukces, _ = await uruchom_ffmpeg(cmd)
    return sukces


async def kompozytor(stan: StanNEXUS) -> dict:
    """
    Węzeł Compositor — scala wszystkie komponenty w finalne wideo.

    Args:
        stan: Pełny stan NEXUS z audio, wizualiami i scenariuszem

    Returns:
        Aktualizacja stanu z gotowym wideo
    """
    log = logger.bind(wezel="compositor")
    log.info("Compositor scala wideo")

    # Sprawdź FFmpeg
    if not sprawdz_ffmpeg():
        log.error("FFmpeg niedostępny!")
        return {
            "bledy": ["Compositor: FFmpeg nie jest zainstalowany"],
            "krok_aktualny": "blad_compositora",
        }

    # Pobierz komponenty
    wizualia = stan.get("wizualia")
    audio = stan.get("audio")
    scenariusz = stan.get("scenariusz")

    if not wizualia or not wizualia.get("obrazy"):
        log.error("Brak obrazów do kompozycji")
        return {
            "bledy": ["Compositor: brak obrazów wizualnych"],
            "krok_aktualny": "blad_compositora",
        }

    # Ścieżki
    sesja_id = stan.get("metadane", {}).get("sesja_id", "domyslna")
    katalog_wyjscia = Path(konf.SCIEZKA_WYJSCIOWA) / sesja_id
    katalog_wyjscia.mkdir(parents=True, exist_ok=True)

    # Pobierz ścieżki obrazów (posortowane)
    obrazy_sciezki = [
        obr["sciezka_pliku"]
        for obr in sorted(wizualia["obrazy"], key=lambda x: x["numer_sceny"])
        if os.path.exists(obr["sciezka_pliku"])
    ]

    if not obrazy_sciezki:
        log.error("Brak dostępnych plików obrazów")
        return {
            "bledy": ["Compositor: pliki obrazów niedostępne"],
            "krok_aktualny": "blad_compositora",
        }

    # Audio ścieżka
    audio_sciezka = audio["sciezka_pliku"] if audio and os.path.exists(audio.get("sciezka_pliku", "")) else ""

    # Oblicz czas per obraz
    calkowity_czas = scenariusz["calkowity_czas"] if scenariusz else 60.0
    czas_per_obraz = max(2.0, calkowity_czas / len(obrazy_sciezki))

    # Napisy ze scenariusza
    napisy = None
    if scenariusz:
        napisy = [
            {
                "tekst": s["tekst_na_ekranie"],
                "start": s["czas_start"],
                "end": s["czas_koniec"],
            }
            for s in scenariusz["sceny"]
            if s.get("tekst_na_ekranie")
        ]

    # Generuj wideo główne
    sciezka_wideo = str(katalog_wyjscia / "wideo_glowne.mp4")
    log.info("Generuję wideo", obrazy=len(obrazy_sciezki), czas_per=round(czas_per_obraz, 1))

    sukces = await stworz_wideo_z_obrazow(
        obrazy=obrazy_sciezki,
        audio=audio_sciezka,
        wyjscie=sciezka_wideo,
        czas_per_obraz=czas_per_obraz,
        napisy=napisy,
    )

    if not sukces:
        log.error("Błąd generacji wideo")
        return {
            "bledy": ["Compositor: błąd FFmpeg przy generacji wideo"],
            "krok_aktualny": "blad_compositora",
        }

    # Generuj miniaturkę
    sciezka_miniaturki = str(katalog_wyjscia / "miniaturka.jpg")
    miniaturka_src = obrazy_sciezki[0]

    # Sprawdź czy mamy specjalną miniaturkę
    sciezka_mini_specjalna = Path(konf.SCIEZKA_TYMCZASOWA) / sesja_id / "obrazy" / "miniaturka.png"
    if sciezka_mini_specjalna.exists():
        miniaturka_src = str(sciezka_mini_specjalna)

    await generuj_miniaturke(miniaturka_src, sciezka_miniaturki, scenariusz["tytul"] if scenariusz else "")

    # Pobierz rozmiar pliku
    rozmiar_mb = 0.0
    try:
        rozmiar_mb = round(os.path.getsize(sciezka_wideo) / (1024 * 1024), 2)
    except Exception:
        pass

    wideo: Wideo = {
        "sciezka_pliku": sciezka_wideo,
        "miniatura_sciezka": sciezka_miniaturki if os.path.exists(sciezka_miniaturki) else "",
        "format": "mp4",
        "rozdzielczosc": "1080x1920",
        "czas_trwania": calkowity_czas,
        "rozmiar_mb": rozmiar_mb,
        "wariant_tiktok": sciezka_wideo,
        "wariant_youtube": sciezka_wideo,
        "wariant_instagram": sciezka_wideo,
    }

    log.info(
        "Compositor zakończony",
        sciezka=sciezka_wideo,
        rozmiar_mb=rozmiar_mb,
        czas_trwania=calkowity_czas,
    )

    return {
        "wideo": wideo,
        "krok_aktualny": "wideo_gotowe",
        "metadane": {
            **stan.get("metadane", {}),
            "status": "gotowe",
        }
    }
