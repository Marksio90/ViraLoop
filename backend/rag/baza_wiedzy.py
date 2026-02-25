"""
NEXUS — Brand RAG: Baza Wiedzy Marki v2.0
===========================================
System RAG (Retrieval-Augmented Generation) zapewniający spójność
głosu marki we wszystkich generowanych treściach.

Nowości v2.0:
- [INNOWACJA 9] Viral Pattern RAG — zasilanie bazą trendów z YouTube Data API
  Pobiera tytuły + opisy top-N filmów tygodnia w danej niszy
  Strateg i Recenzent dostają AKTUALNE wzorce, nie wiedzę sprzed cutoffu
  Koszt: 0$ (YouTube Data API = darmowe 10k req/dzień)
  Fallback: działa bez klucza API (używa statycznej bazy)
- [INNOWACJA 10] Asymetryczna Pamięć Wiralności
  System "immunologiczny" — zapamiętuje co NIE działa z większą siłą
  NVS >= 80: zapisuje wzorzec jako "sukces" (normalna waga)
  NVS < 55: zapisuje jako "anty-wzorzec" (podwyższona waga ostrzeżeń)
  Przed każdą generacją: sprawdza czy nowy scenariusz pasuje do udokumentowanej porażki
  Efekt: system nigdy dwa razy nie popełnia tego samego błędu
  Persistencja: JSON w katalogu danych (prosty, zero zależności)

Używa:
- OpenAI text-embedding-3-small ($0.020/1M tokenów — najtańszy, świetny)
- Cosine similarity (zoptymalizowane — suma kwadratów zamiast zip pętli)
- JSON persistence dla pamięci wiralności
"""

import json
import hashlib
import asyncio
import structlog
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from openai import AsyncOpenAI

from konfiguracja import konf

logger = structlog.get_logger(__name__)

# ====================================================================
# STATYCZNA BAZA WIEDZY
# ====================================================================

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

# Plik persistencji pamięci wiralności
PLIK_PAMIECI = Path("./dane/pamiec_wiralnosci.json")


# ====================================================================
# [INNOWACJA 9] Viral Pattern RAG — YouTube Trending
# ====================================================================

async def pobierz_trendy_youtube(
    nisza: str,
    region: str = "PL",
    n: int = 10,
) -> str:
    """
    Pobiera trendy YouTube w danej niszy przez YouTube Data API v3.

    [INNOWACJA 9] Zasilanie RAG aktualną wiedzą o trendach.

    Problem: GPT ma cutoff wiedzy. Nie wie co viral w tym tygodniu.
    Rozwiązanie: YouTube Data API (darmowe, 10k req/dzień) → top filmy niszy.
    Wynik: Strateg i Recenzent dostają AKTUALNE wzorce haków i struktury.

    Fallback: jeśli brak klucza API lub błąd → zwraca pusty string (graceful).
    """
    if not konf.YOUTUBE_API_KEY:
        return ""

    try:
        import httpx

        # YouTube Data API v3 — search.list (darmowe)
        params = {
            "part": "snippet",
            "q": nisza,
            "type": "video",
            "videoDuration": "short",      # <4 minuty (shorty)
            "order": "viewCount",           # Sortuj po wyświetleniach
            "regionCode": region,
            "relevanceLanguage": "pl",
            "maxResults": n,
            "key": konf.YOUTUBE_API_KEY,
            "publishedAfter": _tydzien_temu_iso(),
        }

        async with httpx.AsyncClient(timeout=10) as klient:
            resp = await klient.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
            )
            resp.raise_for_status()
            dane = resp.json()

        filmy = dane.get("items", [])
        if not filmy:
            return ""

        # Ekstrakcja wzorców haków z tytułów
        wzorce = []
        for film in filmy:
            snippet = film.get("snippet", {})
            tytul = snippet.get("title", "")
            opis = snippet.get("description", "")[:200]
            if tytul:
                wzorce.append(f"- {tytul}: {opis[:100]}")

        if not wzorce:
            return ""

        wynik = f"TRENDY YOUTUBE (ostatnie 7 dni, region: {region}, nisza: {nisza}):\n"
        wynik += "\n".join(wzorce[:n])
        logger.info("Trendy YouTube pobrane", nisza=nisza, filmy=len(wzorce))
        return wynik

    except Exception as e:
        logger.debug("YouTube trendy niedostępne", blad=str(e))
        return ""


def _tydzien_temu_iso() -> str:
    """Zwraca datę 7 dni temu w formacie ISO 8601 dla YouTube API."""
    from datetime import timedelta
    tydzien_temu = datetime.now(timezone.utc) - timedelta(days=7)
    return tydzien_temu.strftime("%Y-%m-%dT%H:%M:%SZ")


# ====================================================================
# [INNOWACJA 10] Asymetryczna Pamięć Wiralności
# ====================================================================

class PamiecWiralnosci:
    """
    System immunologiczny platformy — zapamiętuje porażki mocniej niż sukcesy.

    [INNOWACJA 10] Asymetryczna Pamięć Wiralności.

    Biologia układu immunologicznego: organizm "zapamiętuje" patogeny,
    nie zdrowie. System wiralności działa analogicznie.

    NVS >= 80: SUKCES — zapisuje wzorzec haka + struktury narracji
    NVS < 55: PORAŻKA — zapisuje jako "anty-wzorzec" (blokuje podobne)

    Przed każdą generacją: czy_zablokowany() sprawdza podobieństwo
    nowego scenariusza do udokumentowanych porażek przez cosine similarity.
    Jeśli podobieństwo > 0.82 → ostrzeżenie dla Pisarza.

    Persistencja: JSON → prosta, zero zależności, przenośna.
    """

    def __init__(self, klient_openai: AsyncOpenAI, sciezka_pliku: Path = PLIK_PAMIECI):
        self._klient = klient_openai
        self._sciezka = sciezka_pliku
        self._pamiec: list[dict] = self._wczytaj()
        self._log = logger.bind(komponent="PamiecWiralnosci")

    def _wczytaj(self) -> list[dict]:
        """Wczytuje pamięć z pliku JSON."""
        if self._sciezka.exists():
            try:
                return json.loads(self._sciezka.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _zapisz(self) -> None:
        """Zapisuje pamięć do pliku JSON."""
        try:
            self._sciezka.parent.mkdir(parents=True, exist_ok=True)
            self._sciezka.write_text(
                json.dumps(self._pamiec, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            self._log.warning("Błąd zapisu pamięci", blad=str(e))

    @staticmethod
    def _podobienstwo(vec1: list[float], vec2: list[float]) -> float:
        """Szybkie cosine similarity."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        m1 = sum(a * a for a in vec1) ** 0.5
        m2 = sum(b * b for b in vec2) ** 0.5
        if m1 == 0 or m2 == 0:
            return 0.0
        return dot / (m1 * m2)

    async def _embed(self, tekst: str) -> list[float]:
        """Pobiera embedding tekstu."""
        resp = await self._klient.embeddings.create(
            model=konf.MODEL_EMBEDDINGI,
            input=tekst[:8000],
        )
        return resp.data[0].embedding

    async def zapisz_wynik(
        self,
        scenariusz: dict,
        nvs: int,
        plan_tresci: dict | None = None,
    ) -> None:
        """
        Zapisuje wynik generacji do pamięci wiralności.

        NVS >= 80: sukces (wzorzec do naśladowania)
        NVS < 55: porażka (anty-wzorzec do unikania)
        Pozostałe: ignorowane (za mało sygnału)
        """
        if 55 <= nvs < 80:
            return  # Szary obszar — za mało sygnału

        try:
            # Reprezentacja tekstowa do embeddingu
            hook = scenariusz.get("hook_otwierający", "")
            cta = scenariusz.get("cta", "")
            typ_haka = plan_tresci.get("typ_haka", "") if plan_tresci else ""
            tekst_repr = f"Hook: {hook} | CTA: {cta} | Typ: {typ_haka}"

            embedding = await self._embed(tekst_repr)

            wpis = {
                "id": str(uuid4())[:8],
                "data": datetime.now(timezone.utc).isoformat(),
                "nvs": nvs,
                "typ": "sukces" if nvs >= 80 else "porazka",
                "hook": hook[:200],
                "cta": cta[:100],
                "typ_haka": typ_haka,
                "embedding": embedding,
            }

            self._pamiec.append(wpis)

            # Przytnij do max 500 wpisów (LIFO)
            if len(self._pamiec) > 500:
                self._pamiec = self._pamiec[-500:]

            self._zapisz()
            self._log.info("Wynik zapisany w pamięci", nvs=nvs, typ=wpis["typ"])

        except Exception as e:
            self._log.debug("Błąd zapisu wyniku", blad=str(e))

    async def czy_zablokowany(
        self,
        nowy_hook: str,
        prog_podobienstwa: float = 0.82,
    ) -> tuple[bool, str]:
        """
        Sprawdza czy nowy hook pasuje do udokumentowanej porażki.

        Jeśli cosine_similarity(nowy_hook, anty-wzorzec) > 0.82:
        → ostrzeżenie dla Pisarza z konkretnymi powodami

        Zwraca: (zablokowany: bool, powod: str)
        """
        anty_wzorce = [w for w in self._pamiec if w["typ"] == "porazka"]
        if not anty_wzorce or not nowy_hook.strip():
            return False, ""

        try:
            emb_nowy = await self._embed(nowy_hook)

            for wzorzec in anty_wzorce[-50:]:  # Sprawdź ostatnie 50 porażek
                emb_wzorzec = wzorzec.get("embedding", [])
                if not emb_wzorzec:
                    continue
                sim = self._podobienstwo(emb_nowy, emb_wzorzec)
                if sim > prog_podobienstwa:
                    powod = (
                        f"Hook podobny do anty-wzorca (NVS={wzorzec['nvs']}, "
                        f"podobieństwo={sim:.2f}): '{wzorzec['hook'][:80]}'"
                    )
                    self._log.warning("BLOKADA anty-wzorca", powod=powod)
                    return True, powod

        except Exception as e:
            self._log.debug("Błąd sprawdzania anty-wzorca", blad=str(e))

        return False, ""

    def pobierz_wzorce_sukcesow(self, n: int = 5) -> list[str]:
        """Zwraca ostatnie N udanych hooków jako kontekst dla Pisarza."""
        sukcesy = [w for w in self._pamiec if w["typ"] == "sukces"]
        return [w["hook"] for w in sukcesy[-n:] if w.get("hook")]


# ====================================================================
# GŁÓWNA KLASA RAG
# ====================================================================

class BazaWiedzyMarki:
    """
    Lokalna baza wiedzy marki dla RAG v2.0.

    Nowości v2.0:
    - [INNOWACJA 9] Automatyczne zasilanie trendami YouTube
    - [INNOWACJA 10] Integracja z PamiecWiralnosci
    - Zoptymalizowane cosine similarity (operacje wektorowe)
    """

    def __init__(self, nazwa_marki: str = "nexus"):
        self._klient_openai = AsyncOpenAI(api_key=konf.OPENAI_API_KEY)
        self._nazwa_marki = nazwa_marki
        self._dokumenty: dict[str, str] = {}
        self._embeddingi: dict[str, list[float]] = {}
        self._log = logger.bind(komponent="BazaWiedzyMarki", marka=nazwa_marki)

        # Pamięć wiralności
        self.pamiec_wiralnosci = PamiecWiralnosci(self._klient_openai)

        # Załaduj domyślną wiedzę
        for klucz, tekst in DOMYSLNA_BAZA_WIEDZY.items():
            self._dokumenty[klucz] = tekst.strip()

        self._log.info("Baza wiedzy marki v2.0 zainicjalizowana")

    def _hash_tekstu(self, tekst: str) -> str:
        """Generuje hash tekstu (do cache'owania embedingów)."""
        return hashlib.md5(tekst.encode()).hexdigest()[:8]

    async def dodaj_dokument(self, klucz: str, tekst: str) -> None:
        """Dodaje dokument do bazy wiedzy."""
        self._dokumenty[klucz] = tekst
        self._embeddingi.pop(klucz, None)
        self._log.info("Dokument dodany", klucz=klucz, dlugosc=len(tekst))

    async def _pobierz_embedding(self, tekst: str) -> list[float]:
        """Pobiera embedding z OpenAI (z cache)."""
        hash_klucz = self._hash_tekstu(tekst)

        if hash_klucz not in self._embeddingi:
            tekst_skrocony = tekst[:30000]
            odpowiedz = await self._klient_openai.embeddings.create(
                model=konf.MODEL_EMBEDDINGI,
                input=tekst_skrocony,
            )
            self._embeddingi[hash_klucz] = odpowiedz.data[0].embedding

        return self._embeddingi[hash_klucz]

    @staticmethod
    def _podobienstwo_cosinusowe(vec1: list[float], vec2: list[float]) -> float:
        """Zoptymalizowane cosine similarity."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        m1 = sum(a * a for a in vec1) ** 0.5
        m2 = sum(b * b for b in vec2) ** 0.5
        if m1 == 0 or m2 == 0:
            return 0.0
        return dot / (m1 * m2)

    async def wyszukaj(
        self, zapytanie: str, top_k: int = 3
    ) -> list[tuple[str, str, float]]:
        """
        Semantyczne wyszukiwanie w bazie wiedzy.

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
        Wzbogacony o trendy YouTube (jeśli dostępne) i wzorce sukcesów.
        """
        try:
            # Wyszukaj z bazy wiedzy
            wyniki = await self.wyszukaj(brief, top_k=3)

            kontekst_czesci = []
            for klucz, tekst, podobienstwo in wyniki:
                if podobienstwo > 0.3:
                    kontekst_czesci.append(f"### {klucz.upper()}:\n{tekst}")

            # Dołącz wzorce sukcesów z pamięci wiralności
            wzorce_sukcesu = self.pamiec_wiralnosci.pobierz_wzorce_sukcesow(3)
            if wzorce_sukcesu:
                kontekst_czesci.append(
                    "### UDANE HAKI Z HISTORII:\n" +
                    "\n".join(f"- {h}" for h in wzorce_sukcesu)
                )

            kontekst = "\n\n".join(kontekst_czesci)
            self._log.info("Kontekst RAG v2.0 pobrany", dokumenty=len(wyniki), dlugosc=len(kontekst))
            return kontekst

        except Exception as e:
            self._log.error("Błąd pobierania kontekstu RAG", blad=str(e))
            return ""

    async def zasilaj_trendami(self, nisza: str, region: str = "PL") -> None:
        """
        [INNOWACJA 9] Zasila bazę aktualnymi trendami YouTube.

        Wywołaj przed każdą sesją generacji dla świeżego kontekstu.
        Klucz dokumentu zawiera datę → stare trendy zastępowane nowymi.
        """
        trendy = await pobierz_trendy_youtube(nisza, region)
        if trendy:
            klucz = f"trendy_youtube_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
            await self.dodaj_dokument(klucz, trendy)
            self._log.info("Baza zasilona trendami YouTube", nisza=nisza, znaki=len(trendy))

    def zaladuj_profil_marki(self, profil: dict) -> None:
        """Ładuje profil marki do bazy."""
        for klucz, wartosc in profil.items():
            if isinstance(wartosc, str) and wartosc.strip():
                self._dokumenty[f"marka_{klucz}"] = wartosc


# ====================================================================
# SINGLETON PER MARKA
# ====================================================================

_bazy_wiedzy: dict[str, BazaWiedzyMarki] = {}


def pobierz_baze_wiedzy(nazwa_marki: str = "nexus") -> BazaWiedzyMarki:
    """Zwraca (lub tworzy) bazę wiedzy dla marki."""
    if nazwa_marki not in _bazy_wiedzy:
        _bazy_wiedzy[nazwa_marki] = BazaWiedzyMarki(nazwa_marki)
    return _bazy_wiedzy[nazwa_marki]
