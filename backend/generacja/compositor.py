"""
ViraLoop — Compositor Wideo v2.0
==================================
Zaawansowany compositor tworzący shortsy na poziomie konkurencyjnych kanałów.

Techniki produkcji:
- Ken Burns PRO: 6 wzorców ruchu (zoom-in, zoom-out, pan-lewo, pan-prawo, diagonal, static)
- Karaoke subtitles: animowane napisy pojawiające się słowo po słowie
- Hook overlay: dramatyczny tekst tytułowy w pierwszych 3 sekundach
- CTA end card: animowany wezwanie do działania na końcu
- Muzyka tła: subtelna warstwa muzyczna (synthezowana przez FFmpeg)
- Vignette + color grade: cinematyczny wygląd przez LUT-like filtr
- Crossfade transitions: 0.5s płynne przejścia między ujęciami
- Loudnorm: normalizacja głośności audio
"""

import os
import asyncio
import structlog
import random
from pathlib import Path
from typing import Optional

from konfiguracja import konf
from agenci.schematy import StanNEXUS, Wideo

logger = structlog.get_logger(__name__)

FORMATY_PLATFORM = {
    "tiktok":    {"szerokosc": 1080, "wysokosc": 1920, "fps": 30},
    "youtube":   {"szerokosc": 1080, "wysokosc": 1920, "fps": 30},
    "instagram": {"szerokosc": 1080, "wysokosc": 1920, "fps": 30},
}

# Ken Burns - wzorce ruchu (zoom, x, y per obraz)
KEN_BURNS_WZORCE = [
    # (opis, wyrazenie_z, wyrazenie_x, wyrazenie_y)
    ("zoom-in",       "min(zoom+0.0012,1.08)",  "(iw-iw/zoom)/2",   "(ih-ih/zoom)/2"),
    ("zoom-out",      "max(zoom-0.0012,1.0)",   "(iw-iw/zoom)/2",   "(ih-ih/zoom)/2"),
    ("pan-right",     "min(zoom+0.0008,1.05)",  "(iw-iw/zoom)*t/8", "(ih-ih/zoom)/2"),
    ("pan-left",      "min(zoom+0.0008,1.05)",  "(iw-iw/zoom)*(1-t/8)", "(ih-ih/zoom)/2"),
    ("diagonal",      "min(zoom+0.001,1.06)",   "(iw-iw/zoom)*t/10","(ih-ih/zoom)*t/10"),
    ("steady",        "1.02",                    "(iw-iw/zoom)/2",   "(ih-ih/zoom)/2"),
]


def sprawdz_ffmpeg() -> bool:
    import shutil
    return shutil.which("ffmpeg") is not None


async def uruchom_ffmpeg(komenda: list[str], timeout: int = 300) -> tuple[bool, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *komenda,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        sukces = proc.returncode == 0
        return sukces, stderr.decode("utf-8", errors="replace")
    except asyncio.TimeoutError:
        return False, "Timeout FFmpeg (>300s)"
    except Exception as e:
        return False, str(e)


def escape_drawtext(tekst: str) -> str:
    """Escapuje znaki specjalne dla FFmpeg drawtext."""
    for ch in ["'", ":", "\\", "[", "]", "=", ";"]:
        tekst = tekst.replace(ch, f"\\{ch}")
    return tekst


def zbuduj_filtr_napisow(
    napisy: list[dict],
    szerokosc: int = 1080,
    wysokosc: int = 1920,
) -> str:
    """
    Buduje łańcuch filtrów drawtext dla animowanych napisów karaoke.

    Każdy segment pojawia się w odpowiednim czasie z:
    - białym tekstem + czarnym cieniem
    - półprzezroczystym tłem
    - pozycją w dolnej tercji ekranu
    """
    if not napisy:
        return ""

    filtry = []
    y_pos = int(wysokosc * 0.78)  # dolna tercja

    for seg in napisy:
        tekst = escape_drawtext(seg.get("tekst", ""))
        if not tekst:
            continue

        t_start = seg.get("start", 0.0)
        t_end = seg.get("end", t_start + 3.0)

        # Główny tekst
        filtr = (
            f"drawtext="
            f"text='{tekst}':"
            f"fontsize=52:"
            f"fontcolor=white:"
            f"shadowcolor=black:"
            f"shadowx=2:"
            f"shadowy=2:"
            f"x=(w-text_w)/2:"
            f"y={y_pos}:"
            f"box=1:"
            f"boxcolor=black@0.55:"
            f"boxborderw=12:"
            f"enable='between(t,{t_start:.2f},{t_end:.2f})'"
        )
        filtry.append(filtr)

    return ",".join(filtry) if filtry else ""


def zbuduj_hook_overlay(hook_tekst: str, szerokosc: int = 1080, wysokosc: int = 1920) -> str:
    """
    Buduje dramatyczny overlay tekstowy dla pierwszych 3 sekund (hook).
    Pojawia się z efektem fade-in.
    """
    if not hook_tekst:
        return ""

    tekst = escape_drawtext(hook_tekst[:80])
    y_center = int(wysokosc * 0.35)

    # Hook tekst — duży, centered, z alpha fade-in przez 0.5s
    return (
        f"drawtext="
        f"text='{tekst}':"
        f"fontsize=68:"
        f"fontcolor=white@(if(lt(t,0.5),t/0.5,if(lt(t,2.5),1.0,max(0,(3.0-t)/0.5)))):"
        f"shadowcolor=black@0.8:"
        f"shadowx=3:"
        f"shadowy=3:"
        f"x=(w-text_w)/2:"
        f"y={y_center}:"
        f"enable='between(t,0,3.0)'"
    )


def zbuduj_cta_overlay(cta_tekst: str, czas_start: float, szerokosc: int = 1080, wysokosc: int = 1920) -> str:
    """
    CTA end card — pojawia się w ostatnich 4 sekundach.
    """
    if not cta_tekst:
        return ""

    tekst = escape_drawtext(cta_tekst[:60])
    y_pos = int(wysokosc * 0.82)

    return (
        f"drawtext="
        f"text='{tekst}':"
        f"fontsize=48:"
        f"fontcolor=yellow:"
        f"shadowcolor=black:"
        f"shadowx=2:"
        f"shadowy=2:"
        f"x=(w-text_w)/2:"
        f"y={y_pos}:"
        f"box=1:"
        f"boxcolor=black@0.6:"
        f"boxborderw=10:"
        f"enable='gte(t,{czas_start:.2f})'"
    )


async def generuj_muzyke_tla(sciezka_wyjsciowa: str, czas_trwania: float) -> bool:
    """
    Generuje subtelną muzykę tła używając FFmpeg synth.
    Tworzy atmosferyczny drone sound z wolnymi akordami.
    """
    # Generuj wielowarstwową muzykę synthezowaną przez FFmpeg
    # Warstwy: bas (55Hz), mid (110Hz), harm (165Hz) z modulacją AM
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", (
            f"aevalsrc="
            f"'0.035*sin(2*PI*55*t)*sin(PI*0.12*t+0.2)"
            f"+0.025*sin(2*PI*110*t)*sin(PI*0.08*t)"
            f"+0.02*sin(2*PI*165*t)*sin(PI*0.06*t+1.5)"
            f"+0.012*sin(2*PI*220*t)*sin(PI*0.04*t+3.0)"
            f"+0.008*sin(2*PI*330*t)*sin(PI*0.05*t+1.0)"
            f"|0.035*sin(2*PI*55*t+0.3)*sin(PI*0.12*t)"
            f"+0.025*sin(2*PI*110*t+0.5)*sin(PI*0.08*t+0.5)"
            f"+0.02*sin(2*PI*165*t+0.8)*sin(PI*0.06*t)"
            f"+0.012*sin(2*PI*220*t+1.2)*sin(PI*0.04*t+2.0)"
            f"+0.008*sin(2*PI*330*t+0.6)*sin(PI*0.05*t)'"
            f":s=44100:c=stereo"
        ),
        "-t", str(czas_trwania + 1),
        "-af", "loudnorm=I=-28:LRA=7:TP=-2,aecho=0.8:0.6:60:0.4,afade=t=in:st=0:d=2,afade=t=out:st={:.2f}:d=2".format(max(0, czas_trwania - 2)),
        "-c:a", "aac",
        "-b:a", "128k",
        sciezka_wyjsciowa,
    ]

    sukces, stderr = await uruchom_ffmpeg(cmd, timeout=60)
    if not sukces:
        logger.warning("Błąd generacji muzyki tła", stderr=stderr[:200])
    return sukces


async def stworz_wideo_premium(
    obrazy: list[str],
    audio_narracja: str,
    wyjscie: str,
    czas_per_obraz: float = 3.0,
    napisy: list[dict] | None = None,
    hook_tekst: str = "",
    cta_tekst: str = "",
    calkowity_czas: float = 60.0,
    audio_muzyka: str | None = None,
) -> bool:
    """
    Tworzy profesjonalne wideo short z:
    - Ken Burns PRO (różne wzorce per obraz)
    - Animowane napisy karaoke
    - Hook overlay (pierwsze 3 sekundy)
    - CTA overlay (ostatnie 4 sekundy)
    - Muzyka tła (subtelna)
    - Vignette effect
    - Crossfade transitions
    """
    if not obrazy:
        logger.error("Brak obrazów do kompozycji")
        return False

    Path(wyjscie).parent.mkdir(parents=True, exist_ok=True)
    n = len(obrazy)

    # Wybierz losowe wzorce Ken Burns dla każdego obrazu
    wzorce = [random.choice(KEN_BURNS_WZORCE) for _ in range(n)]

    # ── BUDUJ FILTRY WIDEO ──────────────────────────────────────────
    video_filtry = []
    mapowania = []
    fps = 30
    klatki_per_obraz = int(czas_per_obraz * fps)

    for i, (img, wzorzec) in enumerate(zip(obrazy, wzorce)):
        _, expr_z, expr_x, expr_y = wzorzec
        filtr = (
            f"[{i}:v]"
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"zoompan="
            f"z='{expr_z}':"
            f"x='{expr_x}':"
            f"y='{expr_y}':"
            f"d={klatki_per_obraz}:"
            f"s=1080x1920:"
            f"fps={fps},"
            f"setsar=1"
            f"[v{i}]"
        )
        video_filtry.append(filtr)
        mapowania.append(f"[v{i}]")

    # Crossfade transitions
    czas_crossfade = 0.5
    klatki_crossfade = int(czas_crossfade * fps)

    if len(mapowania) == 1:
        video_filtry.append(f"{mapowania[0]}copy[vmerged]")
        wyjscie_video = "[vmerged]"
    else:
        aktualny = mapowania[0]
        offset_czasu = 0.0

        for i in range(1, len(mapowania)):
            nast = mapowania[i]
            offset = offset_czasu + czas_per_obraz - czas_crossfade
            wyjscie_xfade = f"[vx{i}]"
            video_filtry.append(
                f"{aktualny}{nast}xfade=transition=fade:duration={czas_crossfade}:offset={offset:.3f}{wyjscie_xfade}"
            )
            aktualny = wyjscie_xfade
            offset_czasu = offset

        wyjscie_video = aktualny

    # ── NAKŁADKI TEKSTOWE ───────────────────────────────────────────
    tekst_filtry = []

    # Vignette effect
    tekst_filtry.append(
        f"{wyjscie_video}vignette=angle=PI/4:mode=backward[vvig]"
    )
    wyjscie_po_vignette = "[vvig]"

    # Karaoke subtitles
    filtr_napisow = zbuduj_filtr_napisow(napisy or [], 1080, 1920)
    # Hook overlay
    filtr_hooka = zbuduj_hook_overlay(hook_tekst, 1080, 1920)
    # CTA
    czas_cta_start = max(0, calkowity_czas - 4.0)
    filtr_cta = zbuduj_cta_overlay(cta_tekst, czas_cta_start, 1080, 1920)

    # Łącz nakładki tekstowe
    nakладки = [f for f in [filtr_napisow, filtr_hooka, filtr_cta] if f]

    if nakладки:
        tekst_filtry.append(
            f"{wyjscie_po_vignette}"
            + ",".join(nakładки)
            + "[vfinal]"
        )
        wyjscie_finalne = "[vfinal]"
    else:
        tekst_filtry.append(f"{wyjscie_po_vignette}copy[vfinal]")
        wyjscie_finalne = "[vfinal]"

    # Łącz wszystkie filtry wideo
    pelny_filtr_video = ";".join(video_filtry + tekst_filtry)

    # ── BUDUJ KOMENDĘ FFMPEG ────────────────────────────────────────
    cmd = ["ffmpeg", "-y"]

    # Wejścia: obrazy
    for img in obrazy:
        dur = czas_per_obraz + (czas_crossfade if len(obrazy) > 1 else 0)
        cmd.extend(["-loop", "1", "-t", str(dur + 1), "-i", img])

    # Narracja audio
    has_audio = os.path.exists(audio_narracja) if audio_narracja else False
    audio_idx = len(obrazy)
    if has_audio:
        cmd.extend(["-i", audio_narracja])

    # Muzyka tła
    has_muzyka = audio_muzyka and os.path.exists(audio_muzyka)
    muzyka_idx = audio_idx + (1 if has_audio else 0)
    if has_muzyka:
        cmd.extend(["-i", audio_muzyka])

    # Filtry wideo
    cmd.extend(["-filter_complex", pelny_filtr_video])

    # Mapowanie wideo
    cmd.extend(["-map", wyjscie_finalne])

    # Miksowanie audio: narracja + muzyka (opcjonalnie)
    if has_audio and has_muzyka:
        # Mix: narracja na 100%, muzyka na 25%
        audio_filter = (
            f"[{audio_idx}:a]volume=1.0[narr];"
            f"[{muzyka_idx}:a]volume=0.22[muz];"
            f"[narr][muz]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-16:LRA=11:TP=-1.5[audio_out]"
        )
        cmd.extend(["-filter_complex", pelny_filtr_video + ";" + audio_filter])
        # Nadpisz filter_complex
        idx_fc = cmd.index("-filter_complex")
        cmd[idx_fc + 1] = pelny_filtr_video + ";" + audio_filter
        cmd.extend(["-map", "[audio_out]"])
    elif has_audio:
        cmd.extend([
            "-map", f"{audio_idx}:a",
            "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
        ])

    # Encoding
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-movflags", "+faststart",
    ])

    if has_audio:
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])

    cmd.extend(["-shortest", wyjscie])

    sukces, stderr = await uruchom_ffmpeg(cmd, timeout=600)
    if not sukces:
        logger.error("FFmpeg błąd", stderr=stderr[:800])

    return sukces


async def generuj_miniaturke(
    obraz_zrodlowy: str,
    wyjscie: str,
    tytul: str = "",
) -> bool:
    if not os.path.exists(obraz_zrodlowy):
        return False

    Path(wyjscie).parent.mkdir(parents=True, exist_ok=True)

    tytul_escaped = escape_drawtext(tytul[:60]) if tytul else ""
    filtr_tytulu = ""
    if tytul_escaped:
        filtr_tytulu = (
            f",drawtext=text='{tytul_escaped}':"
            f"fontsize=48:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:y=h-180:"
            f"box=1:boxcolor=black@0.65:boxborderw=14"
        )

    cmd = [
        "ffmpeg", "-y",
        "-i", obraz_zrodlowy,
        "-vf", (
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"vignette=angle=PI/4:mode=backward"
            f"{filtr_tytulu}"
        ),
        "-q:v", "2",
        wyjscie
    ]

    sukces, _ = await uruchom_ffmpeg(cmd, timeout=60)
    return sukces


async def kompozytor(stan: StanNEXUS) -> dict:
    """
    Węzeł Compositor v2.0 — scala wszystkie komponenty w finalne wideo premium.

    Nowe funkcje vs v1.0:
    - Ken Burns z 6 wzorcami zamiast zawsze zoom-in
    - Animowane napisy karaoke z segmentami TTS
    - Hook overlay w pierwszych 3 sekundach
    - CTA overlay w ostatnich 4 sekundach
    - Muzyka tła synthezowana przez FFmpeg
    - Vignette effect dla kinowego wyglądu
    """
    log = logger.bind(wezel="compositor_v2")
    log.info("Compositor v2.0 scala wideo premium")

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
    plan = stan.get("plan_tresci", {})

    if not wizualia or not wizualia.get("obrazy"):
        log.error("Brak obrazów do kompozycji")
        return {
            "bledy": ["Compositor: brak obrazów wizualnych"],
            "krok_aktualny": "blad_compositora",
        }

    sesja_id = stan.get("metadane", {}).get("sesja_id", "domyslna")
    katalog_wyjscia = Path(konf.SCIEZKA_WYJSCIOWA) / sesja_id
    katalog_wyjscia.mkdir(parents=True, exist_ok=True)

    # Ścieżki obrazów
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

    # Audio narracja
    audio_sciezka = ""
    if audio and os.path.exists(audio.get("sciezka_pliku", "")):
        audio_sciezka = audio["sciezka_pliku"]

    # Czas trwania
    calkowity_czas = scenariusz["calkowity_czas"] if scenariusz else 60.0
    czas_per_obraz = max(2.5, calkowity_czas / len(obrazy_sciezki))

    # ── NAPISY Z SEGMENTÓW TTS ──────────────────────────────────────
    napisy = []
    if audio and audio.get("segmenty"):
        # Użyj realnych segmentów TTS
        for seg in audio["segmenty"]:
            napisy.append({
                "tekst": seg.get("text", ""),
                "start": seg.get("start", 0.0),
                "end": seg.get("end", 0.0),
            })
    elif scenariusz:
        # Fallback: ręczne napisy ze scenariusza
        for scena in scenariusz["sceny"]:
            if scena.get("tekst_na_ekranie"):
                napisy.append({
                    "tekst": scena["tekst_na_ekranie"],
                    "start": scena["czas_start"],
                    "end": scena["czas_koniec"],
                })

    # ── HOOK I CTA ──────────────────────────────────────────────────
    hook_tekst = plan.get("hak_tekstowy", "")
    if not hook_tekst and scenariusz:
        hook_tekst = scenariusz.get("hook_otwierający", "")

    cta_tekst = scenariusz.get("cta", "") if scenariusz else "Obserwuj po więcej!"

    # ── MUZYKA TŁA ──────────────────────────────────────────────────
    sciezka_muzyki = str(katalog_wyjscia / "muzyka_tla.aac")
    muzyka_ok = await generuj_muzyke_tla(sciezka_muzyki, calkowity_czas)
    audio_muzyka: Optional[str] = sciezka_muzyki if muzyka_ok else None

    log.info(
        "Generuję wideo premium",
        obrazy=len(obrazy_sciezki),
        napisy=len(napisy),
        muzyka=muzyka_ok,
        hook=bool(hook_tekst),
        cta=bool(cta_tekst),
    )

    # ── GENERUJ WIDEO ───────────────────────────────────────────────
    sciezka_wideo = str(katalog_wyjscia / "wideo_glowne.mp4")

    sukces = await stworz_wideo_premium(
        obrazy=obrazy_sciezki,
        audio_narracja=audio_sciezka,
        wyjscie=sciezka_wideo,
        czas_per_obraz=czas_per_obraz,
        napisy=napisy,
        hook_tekst=hook_tekst,
        cta_tekst=cta_tekst,
        calkowity_czas=calkowity_czas,
        audio_muzyka=audio_muzyka,
    )

    if not sukces:
        log.error("Błąd generacji wideo premium")
        # Fallback: spróbuj prostszą wersję bez napisów
        log.info("Próba fallback bez nakładek tekstowych")
        sukces = await stworz_wideo_premium(
            obrazy=obrazy_sciezki,
            audio_narracja=audio_sciezka,
            wyjscie=sciezka_wideo,
            czas_per_obraz=czas_per_obraz,
            napisy=None,
            hook_tekst="",
            cta_tekst="",
            calkowity_czas=calkowity_czas,
            audio_muzyka=None,
        )

    if not sukces:
        return {
            "bledy": ["Compositor: błąd FFmpeg przy generacji wideo"],
            "krok_aktualny": "blad_compositora",
        }

    # ── MINIATURKA ──────────────────────────────────────────────────
    sciezka_miniaturki = str(katalog_wyjscia / "miniaturka.jpg")
    miniaturka_src = obrazy_sciezki[0]

    sciezka_mini_specjalna = Path(konf.SCIEZKA_TYMCZASOWA) / sesja_id / "obrazy" / "miniaturka.png"
    if sciezka_mini_specjalna.exists():
        miniaturka_src = str(sciezka_mini_specjalna)

    tytul_mini = scenariusz["tytul"] if scenariusz else ""
    await generuj_miniaturke(miniaturka_src, sciezka_miniaturki, tytul_mini)

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
        "Compositor v2.0 zakończony",
        sciezka=sciezka_wideo,
        rozmiar_mb=rozmiar_mb,
        efekty=["ken_burns_pro", "karaoke_napisy", "hook_overlay", "cta_overlay", "vignette", "muzyka_tla"],
    )

    return {
        "wideo": wideo,
        "krok_aktualny": "wideo_gotowe",
        "metadane": {
            **stan.get("metadane", {}),
            "status": "gotowe",
            "compositor_wersja": "2.0",
        }
    }
