"""
NEXUS — Tarcza Unikalności (Competitive Uniqueness Shield)
===========================================================
[INNOWACJA 11] Mierzy "kątową odległość" nowego wideo od konkurencji.

Problem: Platforma nie wie czy generuje treści identyczne z konkurencją.
Klony popularnych wideo dostają MNIEJSZY boost algorytmiczny.
TikTok/YouTube promują "nowość" w niszy, nie nth-kopię trendu.

Rozwiązanie: Embedduj opisy konkurencji → cosine distance → "uniqueness score".

Architektura:
1. Pobierz top-N filmów z YouTube Data API w danej niszy (tytuły + opisy)
2. Embedduj każdy przez text-embedding-3-small
3. Embedduj nowy scenariusz
4. Oblicz średnią odległość od wszystkich konkurentów
5. Zwróć Uniqueness Score 0-1 + konkretne rekomendacje

Calibracja:
- Uniqueness < 0.30: Klon. Algorytm ukarze. Generuj inaczej.
- 0.30-0.50: Nasycony rynek. Dodaj unikalny kąt.
- 0.50-0.70: OPTIMUM. Oryginalny głos w niszy. Algorytm nagrodzi.
- > 0.70: Ultra-niszowe. Może nie trafić do feed odbiorców.

Koszt: text-embedding-3-small × (N+1) ≈ $0.0002 per wywołanie
Fallback: jeśli brak YouTube API → zwraca wynik neutralny (0.60)
"""

import json
import structlog
from pathlib import Path
from datetime import datetime, timezone
from openai import AsyncOpenAI

from konfiguracja import konf

logger = structlog.get_logger(__name__)

# Cache konkurentów per nisza (odświeżany co 24h)
_CACHE_KONKURENTOW: dict[str, dict] = {}
_CACHE_TTL_GODZIN = 24


def _podobienstwo_cosinusowe(vec1: list[float], vec2: list[float]) -> float:
    """Cosine similarity."""
    dot = sum(a * b for a, b in zip(vec1, vec2))
    m1 = sum(a * a for a in vec1) ** 0.5
    m2 = sum(b * b for b in vec2) ** 0.5
    if m1 == 0 or m2 == 0:
        return 0.0
    return dot / (m1 * m2)


async def _pobierz_filmy_konkurencji(
    nisza: str,
    n: int = 30,
    region: str = "PL",
) -> list[str]:
    """
    Pobiera tytuły + opisy top filmów konkurencji z YouTube Data API.
    Zwraca listę tekstów do embeddowania.
    """
    if not konf.YOUTUBE_API_KEY:
        return []

    # Sprawdź cache (max 24h)
    klucz_cache = f"{nisza}_{region}"
    if klucz_cache in _CACHE_KONKURENTOW:
        wpis = _CACHE_KONKURENTOW[klucz_cache]
        godziny_od_pobrania = (
            datetime.now(timezone.utc).timestamp() - wpis["timestamp"]
        ) / 3600
        if godziny_od_pobrania < _CACHE_TTL_GODZIN:
            return wpis["teksty"]

    try:
        import httpx
        from datetime import timedelta

        miesiac_temu = (
            datetime.now(timezone.utc) - timedelta(days=30)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        params = {
            "part": "snippet",
            "q": nisza,
            "type": "video",
            "videoDuration": "short",
            "order": "viewCount",
            "regionCode": region,
            "relevanceLanguage": "pl",
            "maxResults": n,
            "key": konf.YOUTUBE_API_KEY,
            "publishedAfter": miesiac_temu,
        }

        async with httpx.AsyncClient(timeout=10) as klient:
            resp = await klient.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
            )
            resp.raise_for_status()
            dane = resp.json()

        teksty = []
        for film in dane.get("items", []):
            snippet = film.get("snippet", {})
            tytul = snippet.get("title", "")
            opis = snippet.get("description", "")[:300]
            if tytul:
                teksty.append(f"{tytul}. {opis}")

        # Zapisz do cache
        _CACHE_KONKURENTOW[klucz_cache] = {
            "teksty": teksty,
            "timestamp": datetime.now(timezone.utc).timestamp(),
        }

        logger.info("Mapa konkurencji pobrana", nisza=nisza, filmy=len(teksty))
        return teksty

    except Exception as e:
        logger.debug("Mapa konkurencji niedostępna", blad=str(e))
        return []


async def ocen_unikalnosc(
    klient: AsyncOpenAI,
    scenariusz: dict,
    plan_tresci: dict,
    nisza: str,
    region: str = "PL",
) -> dict:
    """
    Ocenia unikalność nowego wideo względem konkurencji w niszy.

    Zwraca:
        {
            "wynik_unikalnosci": 0.62,     # 0-1 (optimum: 0.50-0.70)
            "interpretacja": "OPTIMUM",
            "n_konkurentow": 28,
            "rekomendacja": "Twoja treść jest wystarczająco unikalna.",
            "kluczowe_roznice": ["Skupiasz się na X, konkurencja na Y"],
        }
    """
    log = logger.bind(funkcja="ocen_unikalnosc")

    # Pobierz teksty konkurencji
    teksty_konkurencji = await _pobierz_filmy_konkurencji(nisza, region=region)

    if not teksty_konkurencji:
        return {
            "wynik_unikalnosci": 0.60,
            "interpretacja": "BRAK DANYCH",
            "n_konkurentow": 0,
            "rekomendacja": "Brak danych o konkurencji (ustaw YOUTUBE_API_KEY).",
            "kluczowe_roznice": [],
        }

    # Reprezentacja tekstowa nowego wideo
    tekst_nowy = (
        f"{scenariusz.get('tytul', '')}. "
        f"{scenariusz.get('hook_otwierający', '')}. "
        f"{plan_tresci.get('hak_tekstowy', '')}. "
        f"{scenariusz.get('streszczenie', '')}"
    )

    try:
        # Embedduj nowe wideo + wszystkich konkurentów w jednym wywołaniu API
        wszystkie_teksty = [tekst_nowy] + teksty_konkurencji[:29]

        resp = await klient.embeddings.create(
            model=konf.MODEL_EMBEDDINGI,
            input=wszystkie_teksty,
        )
        embeddingi = [e.embedding for e in resp.data]

        emb_nowy = embeddingi[0]
        emb_konkurenci = embeddingi[1:]

        # Oblicz średnią odległość kątową (1 - similarity = distance)
        odleglosci = [
            1.0 - _podobienstwo_cosinusowe(emb_nowy, emb_k)
            for emb_k in emb_konkurenci
        ]
        srednia_odleglosc = sum(odleglosci) / len(odleglosci) if odleglosci else 0.60

        # Interpretacja
        if srednia_odleglosc < 0.30:
            interpretacja = "KLON"
            rekomendacja = (
                "UWAGA: Treść bardzo podobna do konkurencji. "
                "Algorytm może nie promować. Dodaj unikalny kąt lub perspektywę."
            )
        elif srednia_odleglosc < 0.50:
            interpretacja = "SATURACJA"
            rekomendacja = (
                "Rynek nasycony podobnymi treściami. "
                "Rozważ zmianę perspektywy lub skupienie na bardziej niszowym aspekcie."
            )
        elif srednia_odleglosc <= 0.70:
            interpretacja = "OPTIMUM"
            rekomendacja = (
                "Unikalna perspektywa w niszy. "
                "Algorytm premiuje oryginalność — ta treść ma przewagę."
            )
        else:
            interpretacja = "ULTRA-NISZOWE"
            rekomendacja = (
                "Treść bardzo odległa od mainstreamu niszy. "
                "Może mieć trudność z dotarciem do szerszej publiczności."
            )

        log.info(
            "Ocena unikalności",
            wynik=round(srednia_odleglosc, 3),
            interpretacja=interpretacja,
            n_konkurentow=len(emb_konkurenci),
        )

        return {
            "wynik_unikalnosci": round(srednia_odleglosc, 3),
            "interpretacja": interpretacja,
            "n_konkurentow": len(emb_konkurenci),
            "rekomendacja": rekomendacja,
            "kluczowe_roznice": [],
        }

    except Exception as e:
        log.error("Błąd oceny unikalności", blad=str(e))
        return {
            "wynik_unikalnosci": 0.60,
            "interpretacja": "BŁĄD",
            "n_konkurentow": 0,
            "rekomendacja": f"Błąd oceny: {str(e)}",
            "kluczowe_roznice": [],
        }


async def agent_tarczy_unikalnosci(stan: dict) -> dict:
    """
    Węzeł LangGraph: ocenia unikalność wideo przed publikacją.

    Używany jako opcjonalny krok po Recenzencie Jakości.
    Dodaje `ocena_unikalnosci` do stanu — informacyjnie (nie blokuje).
    """
    scenariusz = stan.get("scenariusz")
    plan = stan.get("plan_tresci", {})

    if not scenariusz or not plan:
        return {}

    klient = AsyncOpenAI(api_key=konf.OPENAI_API_KEY)

    # Nisza z briefa lub planu
    nisza = plan.get("temat", stan.get("brief", "content marketing"))[:100]

    ocena = await ocen_unikalnosc(klient, scenariusz, plan, nisza)

    logger.info(
        "Tarcza Unikalności",
        wynik=ocena["wynik_unikalnosci"],
        interpretacja=ocena["interpretacja"],
        rekomendacja=ocena["rekomendacja"][:80],
    )

    return {
        "ocena_unikalnosci": ocena,
        "koszt_calkowity_usd": stan.get("koszt_calkowity_usd", 0.0) + 0.0002,
    }
