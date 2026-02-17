"""
ViraLoop – Ewolucyjna optymalizacja treści wideo

Hybrydowy system ewolucyjno-banditowy maksymalizujący wiralność treści:

Faza 1 – PyGAD (Algorytm genetyczny):
  Geny: styl_miniatury, typ_haka, dlugosc_intro, tempo_montazu, energia_muzyki,
        dlugosc_wideo, styl_napisow, cta_pozycja
  Fitness: ważona suma (CTR × 0.4 + watch_time × 0.35 + zaangazowanie × 0.25)
  Selekcja: turniejowa (k=3)
  Krzyżowanie: jednorodne (p=0.8)
  Mutacja: adaptacyjna (maleje z generacją)

Faza 2 – Thompson Sampling (Bandyta kontekstowy):
  Top N kandydatów z GA → ramiona bandyty
  Bayesowska aktualizacja w czasie rzeczywistym

Faza 3 – Pętla sprzężenia zwrotnego:
  Rzeczywiste wyniki z platform → aktualizacja priorów → kolejna runda GA

Netflix używa dokładnie tego wzorca (Thompson Sampling) do personalizacji miniatur,
osiągając +11.88% i +44.85% wzrost zaangażowania.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)


# ── Definicja genów konfiguracji wideo ──────────────────────────────────────

DEFINICJE_GENOW = {
    "styl_miniatury": ["minimalistyczny", "dramatyczny", "twarz_zblizenie", "tekst_duzy", "kontrast_kolorów"],
    "typ_haka": ["pytanie", "szokujacy_fakt", "historia", "demonstracja", "kontrowersja", "obietnica"],
    "dlugosc_intro_s": [3, 5, 7, 10, 15],
    "tempo_montazu": ["bardzo_wolne", "wolne", "srednie", "szybkie", "bardzo_szybkie"],
    "energia_muzyki": [0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 1.0],
    "dlugosc_wideo_s": [15, 30, 60, 90, 120, 180, 300, 600],
    "styl_napisow": ["brak", "standardowe", "tiktok_animowane", "podswietlane_slowo", "kinematograficzne"],
    "cta_pozycja": ["poczatek", "srodek", "koniec", "wiele_miejsc"],
    "format_proporcji": ["9:16", "16:9", "1:1", "4:5"],
}


@dataclass
class KonfiguracacjaWideo:
    """Konfiguracja wideo reprezentowana jako osobnik w algorytmie genetycznym."""

    styl_miniatury: str = "dramatyczny"
    typ_haka: str = "pytanie"
    dlugosc_intro_s: int = 5
    tempo_montazu: str = "srednie"
    energia_muzyki: float = 0.7
    dlugosc_wideo_s: int = 60
    styl_napisow: str = "tiktok_animowane"
    cta_pozycja: str = "koniec"
    format_proporcji: str = "9:16"

    # Metryki (wypełniane po testowaniu)
    przewidywany_ctr: float = 0.0
    przewidywane_watch_time: float = 0.0
    przewidywane_zaangazowanie: float = 0.0
    wynik_fitness: float = 0.0

    def jako_chromosom(self) -> list[int]:
        """Koduje konfigurację jako listę indeksów (chromosom)."""
        return [
            DEFINICJE_GENOW["styl_miniatury"].index(self.styl_miniatury),
            DEFINICJE_GENOW["typ_haka"].index(self.typ_haka),
            DEFINICJE_GENOW["dlugosc_intro_s"].index(self.dlugosc_intro_s),
            DEFINICJE_GENOW["tempo_montazu"].index(self.tempo_montazu),
            DEFINICJE_GENOW["energia_muzyki"].index(self.energia_muzyki),
            DEFINICJE_GENOW["dlugosc_wideo_s"].index(self.dlugosc_wideo_s),
            DEFINICJE_GENOW["styl_napisow"].index(self.styl_napisow),
            DEFINICJE_GENOW["cta_pozycja"].index(self.cta_pozycja),
            DEFINICJE_GENOW["format_proporcji"].index(self.format_proporcji),
        ]

    @classmethod
    def z_chromosomu(cls, chromosom: list[int]) -> "KonfiguracacjaWideo":
        """Dekoduje chromosom na konfigurację wideo."""
        geny = list(DEFINICJE_GENOW.values())
        return cls(
            styl_miniatury=geny[0][chromosom[0] % len(geny[0])],
            typ_haka=geny[1][chromosom[1] % len(geny[1])],
            dlugosc_intro_s=geny[2][chromosom[2] % len(geny[2])],
            tempo_montazu=geny[3][chromosom[3] % len(geny[3])],
            energia_muzyki=geny[4][chromosom[4] % len(geny[4])],
            dlugosc_wideo_s=geny[5][chromosom[5] % len(geny[5])],
            styl_napisow=geny[6][chromosom[6] % len(geny[6])],
            cta_pozycja=geny[7][chromosom[7] % len(geny[7])],
            format_proporcji=geny[8][chromosom[8] % len(geny[8])],
        )


@dataclass
class RamieThompson:
    """Ramię bandyty do Thompson Sampling."""

    konfiguracja: KonfiguracacjaWideo
    alpha: float = 1.0   # Successes (przystosowania Beta)
    beta: float = 1.0    # Failures
    liczba_prob: int = 0

    def probkuj(self) -> float:
        """Próbkuje z rozkładu Beta (Thompson Sampling)."""
        try:
            import numpy as np
            return float(np.random.beta(self.alpha, self.beta))
        except ImportError:
            # Fallback bez NumPy
            return random.betavariate(self.alpha, self.beta)

    def aktualizuj(self, nagroda: float) -> None:
        """Aktualizuje parametry Beta po obserwacji nagrody."""
        self.alpha += nagroda
        self.beta += 1.0 - nagroda
        self.liczba_prob += 1


class OptymalizatorTresci:
    """
    Hybrydowy system GA + Thompson Sampling do optymalizacji treści wideo.

    Implementuje wzorzec używany przez Netflix do personalizacji miniatur.
    """

    def __init__(
        self,
        id_kampanii: UUID,
        liczba_generacji: int = 50,
        wielkosc_populacji: int = 20,
        wspolczynnik_mutacji: float = 0.1,
        wspolczynnik_krzyzowania: float = 0.8,
        # Wagi metryki fitness
        waga_ctr: float = 0.40,
        waga_watch_time: float = 0.35,
        waga_zaangazowania: float = 0.25,
    ):
        self.id_kampanii = id_kampanii
        self.liczba_generacji = liczba_generacji
        self.wielkosc_populacji = wielkosc_populacji
        self.wspolczynnik_mutacji = wspolczynnik_mutacji
        self.wspolczynnik_krzyzowania = wspolczynnik_krzyzowania
        self.waga_ctr = waga_ctr
        self.waga_watch_time = waga_watch_time
        self.waga_zaangazowania = waga_zaangazowania

        # Ramiona bandyty (wypełniane w Fazie 2)
        self.ramiona_bandyty: list[RamieThompson] = []

    async def uruchom(self) -> dict[str, Any]:
        """
        Uruchamia pełny pipeline optymalizacji.

        Faza 1: Ewolucja populacji GA
        Faza 2: Eksploatacja przez Thompson Sampling
        Faza 3: Zwrot najlepszej konfiguracji
        """
        id_sesji = str(uuid4())
        logger.info(
            "Uruchamianie optymalizacji",
            id_sesji=id_sesji,
            id_kampanii=str(self.id_kampanii),
            generacje=self.liczba_generacji,
            populacja=self.wielkosc_populacji,
        )

        # Faza 1: Algorytm genetyczny
        najlepsza_konfiguracja, historia = await self._faza_ga()

        # Faza 2: Thompson Sampling na top 5 kandydatach
        najlepsza_po_ts = await self._faza_thompson_sampling(historia)

        return {
            "id_sesji": id_sesji,
            "id_kampanii": str(self.id_kampanii),
            "generacja": self.liczba_generacji,
            "najlepszy_wynik": najlepsza_po_ts.wynik_fitness,
            "sredni_wynik": sum(k.wynik_fitness for k in historia[-1]) / len(historia[-1]),
            "konfiguracja": {
                "styl_miniatury": najlepsza_po_ts.styl_miniatury,
                "typ_haka": najlepsza_po_ts.typ_haka,
                "dlugosc_intro_s": najlepsza_po_ts.dlugosc_intro_s,
                "tempo_montazu": najlepsza_po_ts.tempo_montazu,
                "energia_muzyki": najlepsza_po_ts.energia_muzyki,
                "dlugosc_wideo_s": najlepsza_po_ts.dlugosc_wideo_s,
                "styl_napisow": najlepsza_po_ts.styl_napisow,
                "format_proporcji": najlepsza_po_ts.format_proporcji,
            },
            "przewidywany_ctr": najlepsza_po_ts.przewidywany_ctr,
            "przewidywany_zasieg": int(najlepsza_po_ts.przewidywane_watch_time * 1000),
        }

    async def _faza_ga(
        self,
    ) -> tuple[KonfiguracacjaWideo, list[list[KonfiguracacjaWideo]]]:
        """
        Faza 1: Algorytm genetyczny (PyGAD lub implementacja własna).

        W produkcji używa PyGAD 3.3.1:
            import pygad
            ga = pygad.GA(
                num_generations=self.liczba_generacji,
                num_parents_mating=4,
                fitness_func=self._funkcja_fitness,
                sol_per_pop=self.wielkosc_populacji,
                num_genes=9,
                gene_space=[range(len(g)) for g in DEFINICJE_GENOW.values()],
                crossover_type="uniform",
                mutation_type="adaptive",
                parent_selection_type="tournament",
                K_tournament=3,
            )
            ga.run()
        """
        try:
            return await self._faza_ga_pygad()
        except ImportError:
            logger.warning("PyGAD niedostępny – używam własnej implementacji GA")
            return await self._faza_ga_wlasna()

    async def _faza_ga_pygad(self) -> tuple[KonfiguracacjaWideo, list[list[KonfiguracacjaWideo]]]:
        """Faza GA z PyGAD 3.3.1."""
        import pygad

        historia: list[list[KonfiguracacjaWideo]] = []
        najlepsza = [KonfiguracacjaWideo()]

        def funkcja_fitness_pygad(ga_instance, rozwiazanie, idx_rozwiazania):
            konfiguracja = KonfiguracacjaWideo.z_chromosomu(list(rozwiazanie))
            konfiguracja.wynik_fitness = self._oblicz_fitness(konfiguracja)
            return konfiguracja.wynik_fitness

        def na_nowa_generacje(ga_instance):
            populacja = [
                KonfiguracacjaWideo.z_chromosomu(list(osobnik))
                for osobnik in ga_instance.population
            ]
            for k in populacja:
                k.wynik_fitness = self._oblicz_fitness(k)
            historia.append(populacja)
            najlepsza[0] = max(populacja, key=lambda k: k.wynik_fitness)

        ga = pygad.GA(
            num_generations=self.liczba_generacji,
            num_parents_mating=4,
            fitness_func=funkcja_fitness_pygad,
            sol_per_pop=self.wielkosc_populacji,
            num_genes=9,
            gene_space=[list(range(len(g))) for g in DEFINICJE_GENOW.values()],
            crossover_type="uniform",
            mutation_type="adaptive",
            mutation_percent_genes=[10, 5],  # adaptacyjna: 10% → 5%
            parent_selection_type="tournament",
            K_tournament=3,
            on_generation=na_nowa_generacje,
            suppress_warnings=True,
        )

        # PyGAD nie jest async – uruchamiamy w executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, ga.run)

        return najlepsza[0], historia

    async def _faza_ga_wlasna(self) -> tuple[KonfiguracacjaWideo, list[list[KonfiguracacjaWideo]]]:
        """Własna implementacja GA gdy PyGAD niedostępny."""
        # Inicjalizacja populacji losowej
        populacja = [self._losowa_konfiguracja() for _ in range(self.wielkosc_populacji)]
        historia = []

        for nr_gen in range(self.liczba_generacji):
            # Ocena fitness
            for konfiguracja in populacja:
                konfiguracja.wynik_fitness = self._oblicz_fitness(konfiguracja)

            # Sortowanie (najlepsi pierwsi)
            populacja.sort(key=lambda k: k.wynik_fitness, reverse=True)
            historia.append(populacja[:])

            # Selekcja elitarna (top 20%)
            elita = populacja[: max(2, self.wielkosc_populacji // 5)]

            # Generacja nowej populacji przez krzyżowanie i mutację
            nowa_populacja = elita[:]
            while len(nowa_populacja) < self.wielkosc_populacji:
                rodzic1 = random.choice(elita)
                rodzic2 = random.choice(elita)
                dziecko = self._krzyzuj(rodzic1, rodzic2)
                dziecko = self._mutuj(dziecko, generacja=nr_gen)
                nowa_populacja.append(dziecko)

            populacja = nowa_populacja

            if (nr_gen + 1) % 10 == 0:
                logger.debug(
                    "GA progres",
                    generacja=nr_gen + 1,
                    najlepszy=round(populacja[0].wynik_fitness, 4),
                )

        populacja.sort(key=lambda k: k.wynik_fitness, reverse=True)
        return populacja[0], historia

    def _oblicz_fitness(self, konfiguracja: KonfiguracacjaWideo) -> float:
        """
        Oblicza wartość przystosowania konfiguracji.

        W produkcji: wywołuje model przewidywania metryk (wytrenowany na
        historycznych danych z ClickHouse) lub używa API YouTube Test & Compare.

        Tu: heurystyka na podstawie znanych wzorców wiralności.
        """
        # Heurystyki wiralności oparte na badaniach
        wynik_hak = {
            "pytanie": 0.85, "szokujacy_fakt": 0.90, "historia": 0.75,
            "demonstracja": 0.80, "kontrowersja": 0.95, "obietnica": 0.88,
        }.get(konfiguracja.typ_haka, 0.70)

        wynik_miniatura = {
            "minimalistyczny": 0.70, "dramatyczny": 0.88, "twarz_zblizenie": 0.92,
            "tekst_duzy": 0.82, "kontrast_kolorów": 0.85,
        }.get(konfiguracja.styl_miniatury, 0.70)

        wynik_tempo = {
            "bardzo_wolne": 0.50, "wolne": 0.65, "srednie": 0.80,
            "szybkie": 0.90, "bardzo_szybkie": 0.85,
        }.get(konfiguracja.tempo_montazu, 0.70)

        wynik_napisy = {
            "brak": 0.60, "standardowe": 0.75, "tiktok_animowane": 0.92,
            "podswietlane_slowo": 0.88, "kinematograficzne": 0.82,
        }.get(konfiguracja.styl_napisow, 0.70)

        # Symuluj CTR i watch_time
        przewidywany_ctr = (wynik_miniatura * 0.6 + wynik_hak * 0.4) * 0.15
        przewidywany_wt = (wynik_tempo * 0.5 + wynik_napisy * 0.3 + konfiguracja.energia_muzyki * 0.2)
        przewidywane_zaangazowanie = (wynik_hak * 0.4 + wynik_miniatura * 0.3 + wynik_napisy * 0.3)

        konfiguracja.przewidywany_ctr = round(przewidywany_ctr, 4)
        konfiguracja.przewidywane_watch_time = round(przewidywany_wt, 4)
        konfiguracja.przewidywane_zaangazowanie = round(przewidywane_zaangazowanie, 4)

        # Funkcja fitness ważona
        fitness = (
            przewidywany_ctr * self.waga_ctr
            + przewidywany_wt * self.waga_watch_time
            + przewidywane_zaangazowanie * self.waga_zaangazowania
        )

        return round(fitness, 6)

    async def _faza_thompson_sampling(
        self,
        historia: list[list[KonfiguracacjaWideo]],
        liczba_prob: int = 100,
    ) -> KonfiguracacjaWideo:
        """
        Faza 2: Thompson Sampling na top kandydatach z GA.

        Wybiera top 5 konfiguracji z ostatniej generacji jako ramiona bandyty.
        Symuluje próbki z rozkładu Beta dla każdego ramienia.
        """
        if not historia:
            return self._losowa_konfiguracja()

        # Top 5 kandydatów jako ramiona bandyty
        ostatnia_gen = sorted(historia[-1], key=lambda k: k.wynik_fitness, reverse=True)
        top_kandydaci = ostatnia_gen[:min(5, len(ostatnia_gen))]

        self.ramiona_bandyty = [
            RamieThompson(
                konfiguracja=k,
                alpha=1.0 + k.wynik_fitness * 10,  # Prior oparty na fitness z GA
                beta=1.0 + (1.0 - k.wynik_fitness) * 10,
            )
            for k in top_kandydaci
        ]

        # Symulacja próbkowania Thompson (w produkcji: rzeczywiste A/B testy)
        for _ in range(liczba_prob):
            # Wybierz ramię z najwyższą próbką Beta
            probki = [(ramie.probkuj(), ramie) for ramie in self.ramiona_bandyty]
            _, najlepsze_ramie = max(probki, key=lambda x: x[0])

            # Symuluj nagrodę (w produkcji: rzeczywiste metryki z platformy)
            nagroda = najlepsze_ramie.konfiguracja.wynik_fitness + random.gauss(0, 0.05)
            nagroda = max(0.0, min(1.0, nagroda))

            najlepsze_ramie.aktualizuj(nagroda)

        # Zwróć ramię z najwyższą oczekiwaną nagrodą (alpha / (alpha + beta))
        ramie_zwycieskie = max(
            self.ramiona_bandyty,
            key=lambda r: r.alpha / (r.alpha + r.beta),
        )

        logger.info(
            "Thompson Sampling zakończony",
            liczba_prób=liczba_prob,
            zwycięski_styl_miniatury=ramie_zwycieskie.konfiguracja.styl_miniatury,
            zwycięski_typ_haka=ramie_zwycieskie.konfiguracja.typ_haka,
            oczekiwana_nagroda=round(
                ramie_zwycieskie.alpha / (ramie_zwycieskie.alpha + ramie_zwycieskie.beta), 4
            ),
        )

        return ramie_zwycieskie.konfiguracja

    def _losowa_konfiguracja(self) -> KonfiguracacjaWideo:
        """Generuje losową konfigurację wideo."""
        geny = DEFINICJE_GENOW
        return KonfiguracacjaWideo(
            styl_miniatury=random.choice(geny["styl_miniatury"]),
            typ_haka=random.choice(geny["typ_haka"]),
            dlugosc_intro_s=random.choice(geny["dlugosc_intro_s"]),
            tempo_montazu=random.choice(geny["tempo_montazu"]),
            energia_muzyki=random.choice(geny["energia_muzyki"]),
            dlugosc_wideo_s=random.choice(geny["dlugosc_wideo_s"]),
            styl_napisow=random.choice(geny["styl_napisow"]),
            cta_pozycja=random.choice(geny["cta_pozycja"]),
            format_proporcji=random.choice(geny["format_proporcji"]),
        )

    def _krzyzuj(
        self,
        rodzic1: KonfiguracacjaWideo,
        rodzic2: KonfiguracacjaWideo,
    ) -> KonfiguracacjaWideo:
        """Krzyżowanie jednorodne (uniform crossover)."""
        chromosom1 = rodzic1.jako_chromosom()
        chromosom2 = rodzic2.jako_chromosom()
        dziecko = [
            g1 if random.random() < self.wspolczynnik_krzyzowania else g2
            for g1, g2 in zip(chromosom1, chromosom2)
        ]
        return KonfiguracacjaWideo.z_chromosomu(dziecko)

    def _mutuj(
        self,
        konfiguracja: KonfiguracacjaWideo,
        generacja: int = 0,
    ) -> KonfiguracacjaWideo:
        """Mutacja adaptacyjna (prawdopodobieństwo maleje z generacją)."""
        wspolczynnik = self.wspolczynnik_mutacji * (1.0 - generacja / (2 * self.liczba_generacji))
        chromosom = konfiguracja.jako_chromosom()
        geny = list(DEFINICJE_GENOW.values())

        zmutowany = [
            random.randint(0, len(geny[i]) - 1) if random.random() < wspolczynnik else g
            for i, g in enumerate(chromosom)
        ]
        return KonfiguracacjaWideo.z_chromosomu(zmutowany)
