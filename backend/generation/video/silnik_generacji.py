"""
ViraLoop – Silnik generacji wideo

Zarządza wyborem modelu, wysyłaniem żądań do API i pobieraniem wyników.
Obsługuje modele Tier 1 (premium), Tier 1.5 (przełomowe) i open-source.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class TierModelu(str, Enum):
    """Warstwy jakościowe modeli wideo."""

    TIER_1_PREMIUM = "tier1"      # Veo 3.1, Sora 2, Runway Gen-4.5
    TIER_15_PRZELAMANIE = "tier1.5"  # Kling 3.0, Seedance 2.0
    TIER_2_EKONOMICZNY = "tier2"  # Hailuo 02, Luma Ray 3
    OPEN_SOURCE = "open"          # Wan2.2, HunyuanVideo 1.5, LTX-Video


@dataclass
class KonfiguracyjaModelu:
    """Konfiguracja modelu generowania wideo."""

    id: str
    nazwa: str
    tier: TierModelu
    dostawca_api: str  # "fal.ai", "runwayml", "vertex", "local"
    koszt_za_sekunde_usd: float
    max_dlugosc_sekund: int
    max_rozdzielczosc: str
    natywne_audio: bool
    obsługuje_4k60: bool
    max_vram_gb: int | None  # None = chmura (bez wymagań VRAM)
    opis: str


DOSTEPNE_MODELE: dict[str, KonfiguracyjaModelu] = {
    # ── Tier 1: Klasa filmowa ──────────────────────────────────────
    "veo-3.1": KonfiguracyjaModelu(
        id="veo-3.1",
        nazwa="Google Veo 3.1",
        tier=TierModelu.TIER_1_PREMIUM,
        dostawca_api="vertex",
        koszt_za_sekunde_usd=0.40,
        max_dlugosc_sekund=8,
        max_rozdzielczosc="1080p",
        natywne_audio=True,
        obsługuje_4k60=False,
        max_vram_gb=None,
        opis="Najlepsza fizyka, realizm i audio przestrzenne. Lider w testach porównawczych 2026.",
    ),
    "sora-2-pro": KonfiguracyjaModelu(
        id="sora-2-pro",
        nazwa="OpenAI Sora 2 Pro",
        tier=TierModelu.TIER_1_PREMIUM,
        dostawca_api="openai",
        koszt_za_sekunde_usd=0.50,
        max_dlugosc_sekund=25,
        max_rozdzielczosc="1792x1024",
        natywne_audio=True,
        obsługuje_4k60=False,
        max_vram_gb=None,
        opis="Najlepsza inteligencja narracyjna i spójność fabularna.",
    ),
    "runway-gen-4.5": KonfiguracyjaModelu(
        id="runway-gen-4.5",
        nazwa="Runway Gen-4.5",
        tier=TierModelu.TIER_1_PREMIUM,
        dostawca_api="fal.ai",
        koszt_za_sekunde_usd=0.25,
        max_dlugosc_sekund=10,
        max_rozdzielczosc="1080p",
        natywne_audio=False,
        obsługuje_4k60=False,
        max_vram_gb=None,
        opis="#1 w benchmarkach (Elo 1247). Najlepszy realizm ruchu i zgodność z promptem.",
    ),
    # ── Tier 1.5: Przełomowe możliwości ───────────────────────────
    "kling-3.0": KonfiguracyjaModelu(
        id="kling-3.0",
        nazwa="Kuaishou Kling 3.0",
        tier=TierModelu.TIER_15_PRZELAMANIE,
        dostawca_api="fal.ai",
        koszt_za_sekunde_usd=0.07,  # ~$0.03-0.14/s przez fal.ai
        max_dlugosc_sekund=15,
        max_rozdzielczosc="4K@60fps",
        natywne_audio=True,
        obsługuje_4k60=True,
        max_vram_gb=None,
        opis="JEDYNY model z natywnym 4K@60fps (nie upscale!). Wielojęzyczna synchronizacja ust (5 języków). Łańcuchowanie 6 ujęć → 3-minutowe narracje.",
    ),
    "seedance-2.0": KonfiguracyjaModelu(
        id="seedance-2.0",
        nazwa="ByteDance Seedance 2.0",
        tier=TierModelu.TIER_15_PRZELAMANIE,
        dostawca_api="fal.ai",
        koszt_za_sekunde_usd=0.10,
        max_dlugosc_sekund=20,
        max_rozdzielczosc="1080p",
        natywne_audio=True,
        obsługuje_4k60=False,
        max_vram_gb=None,
        opis="12 jednoczesnych wejść multimodalnych (tekst + 9 obrazów + 9 wideo + 3 audio). UWAGA: ryzyko prawne (pozwy Disney/Paramount).",
    ),
    # ── Tier 2: Ekonomiczne ────────────────────────────────────────
    "hailuo-02": KonfiguracyjaModelu(
        id="hailuo-02",
        nazwa="MiniMax Hailuo 02",
        tier=TierModelu.TIER_2_EKONOMICZNY,
        dostawca_api="fal.ai",
        koszt_za_sekunde_usd=0.05,
        max_dlugosc_sekund=12,
        max_rozdzielczosc="1080p",
        natywne_audio=False,
        obsługuje_4k60=False,
        max_vram_gb=None,
        opis="#2 globalnie w benchmarkach. Zaczyna od $14.99/miesiąc. Najlepsza cena/jakość w Tier 2.",
    ),
    "luma-ray-3": KonfiguracyjaModelu(
        id="luma-ray-3",
        nazwa="Luma Ray 3",
        tier=TierModelu.TIER_2_EKONOMICZNY,
        dostawca_api="fal.ai",
        koszt_za_sekunde_usd=0.08,
        max_dlugosc_sekund=10,
        max_rozdzielczosc="4K HDR",
        natywne_audio=False,
        obsługuje_4k60=False,
        max_vram_gb=None,
        opis="Wyjście 4K HDR w rozsądnej cenie.",
    ),
    # ── Open-Source: Samodzielny hosting ──────────────────────────
    "wan2.2": KonfiguracyjaModelu(
        id="wan2.2",
        nazwa="Alibaba Wan2.2",
        tier=TierModelu.OPEN_SOURCE,
        dostawca_api="local",
        koszt_za_sekunde_usd=0.02,  # koszt GPU
        max_dlugosc_sekund=20,
        max_rozdzielczosc="1080p",
        natywne_audio=False,
        obsługuje_4k60=False,
        max_vram_gb=40,
        opis="Pierwsza architektura MoE w dyfuzji (14B aktywnych parametrów). Najlepsza jakość kinematograficzna wśród open-source. Licencja Apache 2.0.",
    ),
    "hunyuan-1.5": KonfiguracyjaModelu(
        id="hunyuan-1.5",
        nazwa="Tencent HunyuanVideo 1.5",
        tier=TierModelu.OPEN_SOURCE,
        dostawca_api="local",
        koszt_za_sekunde_usd=0.015,
        max_dlugosc_sekund=15,
        max_rozdzielczosc="720p",
        natywne_audio=False,
        obsługuje_4k60=False,
        max_vram_gb=14,  # 8GB z offloadingiem
        opis="8.3B parametrów, działa na 14GB VRAM (RTX 4090). 720p w 19s. Wynik 96.4% jakości wizualnej – bije Runway Gen-3.",
    ),
    "ltx-video": KonfiguracyjaModelu(
        id="ltx-video",
        nazwa="LTX-Video (Lightricks)",
        tier=TierModelu.OPEN_SOURCE,
        dostawca_api="local",
        koszt_za_sekunde_usd=0.01,
        max_dlugosc_sekund=10,
        max_rozdzielczosc="720p",
        natywne_audio=False,
        obsługuje_4k60=False,
        max_vram_gb=12,
        opis="Najszybszy open-source: 5-10s klip w <10s. Idealny do szybkiego prototypowania i masowej generacji.",
    ),
}


class SilnikGeneracjiWideo:
    """
    Główny silnik do generowania wideo przez różne API.

    Strategia wyboru modelu:
    1. Tryb premium (niska latencja, max jakość) → Runway Gen-4.5 / Veo 3.1
    2. Tryb 4K@60fps → Kling 3.0 (jedyna opcja)
    3. Tryb ekonomiczny → Hailuo 02
    4. Tryb open-source → Wan2.2 / HunyuanVideo 1.5 (zależnie od VRAM)
    """

    def __init__(self):
        self._klienci: dict[str, Any] = {}

    def szacuj_czas(self, model_id: str, czas_trwania: int) -> int:
        """
        Szacuje czas generacji w sekundach.

        Benchmarki (H100 80GB):
        - Kling 3.0 / Runway / Veo: 20-60s dla 8s klipu (API)
        - Wan2.2: ~90s dla 10s klipu (lokalnie na A100)
        - HunyuanVideo 1.5: 19s dla 720p (RTX 4090)
        - LTX-Video: <10s dla 5-10s klipu (RTX 4090)
        """
        model = DOSTEPNE_MODELE.get(model_id)
        if model is None:
            return 60

        if model.dostawca_api == "local":
            # Lokalne modele: wolniejsze
            mnoznik = {"wan2.2": 9.0, "hunyuan-1.5": 1.9, "ltx-video": 1.0}.get(model_id, 5.0)
            return int(czas_trwania * mnoznik)
        else:
            # Modele API: szybsze, ale z latencją sieci
            return max(20, czas_trwania * 4)

    def szacuj_koszt(self, model_id: str, czas_trwania: int) -> float:
        """Szacuje koszt generacji w USD."""
        model = DOSTEPNE_MODELE.get(model_id)
        if model is None:
            return 0.0
        return round(model.koszt_za_sekunde_usd * czas_trwania, 4)

    def wybierz_optymalny_model(
        self,
        rozdzielczosc: str,
        budzet_usd: float | None,
        czas_trwania: int,
        wymaga_audio: bool,
        uzywaj_lokalnych: bool,
    ) -> str:
        """
        Automatycznie wybiera optymalny model na podstawie wymagań.

        Logika:
        1. 4K@60fps → Kling 3.0 (jedyna opcja)
        2. Audio natywne + premium → Veo 3.1 lub Sora 2
        3. Najlepsza jakość bez audio → Runway Gen-4.5
        4. Lokalny hosting → Wan2.2 (jakość) lub HunyuanVideo (niskie VRAM)
        5. Budżet → Hailuo 02
        """
        # Jedyna opcja dla 4K@60fps
        if rozdzielczosc in ("4K@60fps", "4k60"):
            return "kling-3.0"

        # Filtruj modele według możliwości
        kandydaci = []
        for model_id, konfiguracja in DOSTEPNE_MODELE.items():
            # Pomiń lokalne jeśli nie wymagane
            if not uzywaj_lokalnych and konfiguracja.dostawca_api == "local":
                continue

            # Sprawdź budżet
            if budzet_usd is not None:
                koszt = self.szacuj_koszt(model_id, czas_trwania)
                if koszt > budzet_usd:
                    continue

            # Preferuj modele z audio gdy wymagane
            if wymaga_audio and not konfiguracja.natywne_audio:
                continue

            kandydaci.append((model_id, konfiguracja))

        if not kandydaci:
            # Fallback do najtańszego modelu
            return "hailuo-02"

        # Sortuj: Tier 1 > Tier 1.5 > Tier 2 > Open-source
        kolejnosc_tier = {
            TierModelu.TIER_1_PREMIUM: 0,
            TierModelu.TIER_15_PRZELAMANIE: 1,
            TierModelu.TIER_2_EKONOMICZNY: 2,
            TierModelu.OPEN_SOURCE: 3,
        }
        kandydaci.sort(key=lambda x: kolejnosc_tier[x[1].tier])
        return kandydaci[0][0]

    async def generuj(
        self,
        prompt: str,
        model_id: str = "kling-3.0",
        czas_trwania: int = 8,
        rozdzielczosc: str = "1080p",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generuje wideo przez odpowiednie API.

        Dla modeli fal.ai:
            import fal_client
            handler = await fal_client.submit_async(
                f"fal-ai/{model_id}",
                arguments={"prompt": prompt, "duration": czas_trwania, ...}
            )
            result = await handler.get()

        Dla modeli lokalnych (Ray Serve):
            Wysyła żądanie do endpointu Ray Serve na własnym klastrze GPU.
        """
        model = DOSTEPNE_MODELE.get(model_id)
        if model is None:
            raise ValueError(f"Nieznany model: {model_id}. Dostępne: {list(DOSTEPNE_MODELE.keys())}")

        logger.info(
            "Generowanie wideo",
            model=model_id,
            tier=model.tier,
            dostawca=model.dostawca_api,
            koszt_szacowany_usd=self.szacuj_koszt(model_id, czas_trwania),
        )

        if model.dostawca_api == "fal.ai":
            return await self._generuj_przez_fal(prompt, model, czas_trwania, rozdzielczosc, **kwargs)
        elif model.dostawca_api == "local":
            return await self._generuj_lokalnie(prompt, model, czas_trwania, rozdzielczosc, **kwargs)
        elif model.dostawca_api == "runwayml":
            return await self._generuj_przez_runway(prompt, model, czas_trwania, **kwargs)
        elif model.dostawca_api == "vertex":
            return await self._generuj_przez_vertex(prompt, model, czas_trwania, **kwargs)
        else:
            raise NotImplementedError(f"Dostawca API nieobsługiwany: {model.dostawca_api}")

    async def _generuj_przez_fal(
        self,
        prompt: str,
        model: KonfiguracyjaModelu,
        czas_trwania: int,
        rozdzielczosc: str,
        **kwargs,
    ) -> dict:
        """Generuje wideo przez fal.ai (Kling, Runway, Luma, MiniMax)."""
        try:
            import fal_client

            # Mapowanie ID modeli na endpointy fal.ai
            mapowanie_endpoints = {
                "kling-3.0": "fal-ai/kling-video/v3/standard/text-to-video",
                "runway-gen-4.5": "fal-ai/runway-gen4/turbo",
                "hailuo-02": "fal-ai/minimax/video-01",
                "luma-ray-3": "fal-ai/luma-dream-machine/ray-3",
                "seedance-2.0": "fal-ai/bytedance/seedance-v1",
            }

            endpoint = mapowanie_endpoints.get(model.id, f"fal-ai/{model.id}")

            handler = await fal_client.submit_async(
                endpoint,
                arguments={
                    "prompt": prompt,
                    "duration": czas_trwania,
                    "resolution": rozdzielczosc,
                    **kwargs,
                },
            )

            wynik = await handler.get()
            return {
                "url_wideo": wynik["video"]["url"],
                "model": model.id,
                "czas_trwania": czas_trwania,
                "rozdzielczosc": rozdzielczosc,
            }

        except ImportError:
            logger.warning("fal_client niedostępny – symulacja wyniku")
            await asyncio.sleep(2)
            return {
                "url_wideo": f"https://storage.viraloop.pl/test/{model.id}.mp4",
                "model": model.id,
                "symulacja": True,
            }

    async def _generuj_lokalnie(
        self,
        prompt: str,
        model: KonfiguracyjaModelu,
        czas_trwania: int,
        rozdzielczosc: str,
        **kwargs,
    ) -> dict:
        """
        Generuje wideo przez lokalny klaster GPU (Ray Serve).

        Konfiguracja Ray Serve dla HunyuanVideo 1.5:
        - deployment_name: "hunyuan-video-1.5"
        - num_replicas: 4 (na klastrze 4×RTX 4090)
        - ray_actor_options: {"num_gpus": 1}
        - Fractional GPU allocation: max_concurrent_queries=2
        """
        import aiohttp

        ray_serve_url = f"http://ray-serve:8000/generuj/{model.id}"

        async with aiohttp.ClientSession() as sesja:
            async with sesja.post(
                ray_serve_url,
                json={
                    "prompt": prompt,
                    "duration": czas_trwania,
                    "resolution": rozdzielczosc,
                },
                timeout=aiohttp.ClientTimeout(total=300),
            ) as odpowiedz:
                if odpowiedz.status == 200:
                    wynik = await odpowiedz.json()
                    return wynik
                else:
                    tekst_bledu = await odpowiedz.text()
                    raise RuntimeError(f"Błąd Ray Serve {odpowiedz.status}: {tekst_bledu}")

    async def _generuj_przez_runway(self, prompt: str, model, czas_trwania: int, **kwargs) -> dict:
        """Generuje wideo przez RunwayML API bezpośrednio."""
        # TODO: Implementacja przez runwayml Python SDK
        raise NotImplementedError("Runway bezpośrednie API – w trakcie implementacji")

    async def _generuj_przez_vertex(self, prompt: str, model, czas_trwania: int, **kwargs) -> dict:
        """Generuje wideo przez Google Vertex AI (Veo 3.1)."""
        # TODO: Implementacja przez google-cloud-aiplatform SDK
        raise NotImplementedError("Vertex AI (Veo 3.1) – w trakcie implementacji")

    def lista_modeli(self) -> list[dict]:
        """Zwraca listę dostępnych modeli z metadanymi."""
        return [
            {
                "id": m.id,
                "nazwa": m.nazwa,
                "tier": m.tier,
                "koszt_za_sekunde_usd": m.koszt_za_sekunde_usd,
                "max_rozdzielczosc": m.max_rozdzielczosc,
                "natywne_audio": m.natywne_audio,
                "obsluguje_4k60": m.obsługuje_4k60,
                "opis": m.opis,
            }
            for m in DOSTEPNE_MODELE.values()
        ]
