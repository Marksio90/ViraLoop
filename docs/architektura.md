# Architektura ViraLoop

## Przegląd systemu

ViraLoop to pięciowarstwowa platforma AI do generowania i optymalizacji treści wideo:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WARSTWA 1: FRONTEND                                                        │
│  Next.js 16 + shadcn/ui + Tremor + Recharts + TanStack Table               │
│  Diffusion Studio (WebGPU) + Liveblocks + Yjs (CRDT)                       │
│  Framer Motion + next-intl (20+ języków) + React Compiler (auto-memo)       │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ HTTPS + WebSocket
┌────────────────────────────────▼────────────────────────────────────────────┐
│  WARSTWA 2: API GATEWAY                                                     │
│  FastAPI + Uvicorn (4 workers) + CORS + GZip + JWT + Prometheus Metrics    │
│  Endpointy: /wideo /audio /analityka /projekty /uzytkownik /zgodnosc        │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│  WARSTWA 3: ORKIESTRACJA                                                    │
│                                                                             │
│  LangGraph 1.0 (GA październik 2025)                                        │
│  ├── Trwałe wykonanie (stan po restarcie serwera)                          │
│  ├── Human-in-the-loop bramy zatwierdzenia                                  │
│  ├── Cache wyników dla identycznych scen                                    │
│  └── LangSmith: śledzenie kosztów i obserwowalność                         │
│                                                                             │
│  DSPy v3.1.3 (MIPROv2 Bayesian Optimization)                               │
│  ├── Programatyczna optymalizacja promptów (nie ręczna)                    │
│  ├── GPT-4o-mini: 66% → 87% dokładność po optymalizacji                    │
│  ├── Koszt optymalizacji: ~$2-3, czas: ~20 minut                           │
│  └── Przy zmianie modelu: skompiluj ponownie, nie edytuj promptów          │
│                                                                             │
│  Protokoły: MCP (agent-narzędzie) + A2A (agent-agent, Linux Foundation)   │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│  WARSTWA 4: GENERACJA                                                       │
│                                                                             │
│  Wideo:                                                                     │
│  ├── Tier 1: Veo 3.1 (Vertex AI) / Sora 2 (OpenAI) / Runway Gen-4.5      │
│  ├── Tier 1.5: Kling 3.0 (4K@60fps!) / Seedance 2.0 (multimodal)          │
│  ├── Tier 2: Hailuo 02 (#2 benchmark, $14.99/mies) / Luma Ray 3           │
│  └── Open-source: Wan2.2 (MoE 14B, Apache 2.0) / HunyuanVideo 1.5        │
│                                                                             │
│  Głos (TTS):                                                               │
│  ├── ElevenLabs v3 (premium, 70+ języków, tagi emocji [excited])           │
│  ├── FishAudio S1 (#1 TTS Arena V2, WER 0.8%, 6x tańszy)                  │
│  ├── Chatterbox MIT (23 języki, 63% lepsz. niż ElevenLabs w testach)      │
│  └── Kokoro Apache 2.0 (82M params, CPU, <$1/milion znaków EN)            │
│                                                                             │
│  Muzyka:                                                                   │
│  ├── SOUNDRAW / Beatoven.ai (bezpieczne prawnie, licencja wieczysta)       │
│  ├── ACE-Step v1.5 (open-source, 4min w 20s na A100, styczeń 2026)        │
│  └── Mubert API (muzyka w czasie rzeczywistym, royalty-free)               │
│                                                                             │
│  Post-processing:                                                           │
│  ├── FFmpeg 8.0 (wbudowany Whisper, NVENC 5x szybszy od CPU)               │
│  ├── Remotion 4.x (React → wideo, 200 równoległych Lambda)                 │
│  └── Diffusion Studio (WebCodecs + WebGPU, podgląd przeglądarkowy)        │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│  WARSTWA 5: DANE I OPTYMALIZACJA                                            │
│                                                                             │
│  ClickHouse v26.1 (analityka):                                             │
│  ├── MergeTree ORDER BY (video_id, timestamp)                              │
│  ├── AggregatingMergeTree materialized views                               │
│  ├── LowCardinality(String) dla pól kategorycznych                         │
│  └── Sub-sekundowe zapytania nad miliardami wierszy metryk                 │
│                                                                             │
│  Qdrant (DNA wideo):                                                       │
│  ├── Multi-wektory: wizualne (CLIP 1024d) + audio (CLAP 512d) + treść     │
│  ├── Pre-filtering: zapytania metadanych PRZED wyszukiwaniem wektorów      │
│  ├── 12K QPS z kwantyzacją, Rust-native                                    │
│  └── ~$102/mies za 1M wektorów na AWS                                      │
│                                                                             │
│  Pętla ewolucyjna:                                                         │
│  ├── Faza 1: PyGAD GA (styl_miniatury, typ_haka, tempo → fitness)         │
│  ├── Faza 2: Thompson Sampling (top GA kandydaci jako ramiona bandyty)     │
│  ├── Faza 3: Rzeczywiste wyniki z platform → aktualizacja priorów          │
│  └── Netflix wzorzec: +11.88% i +44.85% wzrost zaangażowania              │
│                                                                             │
│  Integracje platform:                                                      │
│  ├── YouTube Data API v3 (10K jednostek/dzień, Test & Compare A/B)        │
│  ├── TikTok Research API (publiczne dane wideo, wymaga zatwierdzenia)      │
│  └── Instagram Graph API (Reels skip rate + repost counts od XII 2025)    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Warstwa obliczeniowa (GPU Infrastructure)

```
┌─────────────────────────────────────────────────────────────────┐
│  Ray 2.53.0 (KubeRay na Kubernetes)                            │
│                                                                 │
│  ┌──────────┐  ┌──────────────────┐  ┌─────────────────────┐  │
│  │ Ray Head │  │ H100 Workers     │  │ RTX 4090 Workers    │  │
│  │          │  │ (Wan2.2 14B MoE) │  │ (HunyuanVideo 1.5) │  │
│  │ GCS      │  │ 40-80GB VRAM     │  │ 14GB VRAM           │  │
│  │ Dashboard│  │ ~$2-4/hr         │  │ ~$1.5-2/hr          │  │
│  │ Serve    │  │ min: 0 max: 8    │  │ min: 2 max: 16      │  │
│  └──────────┘  └──────────────────┘  └─────────────────────┘  │
│                                                                 │
│  + fal.ai (chmura): Kling 3.0 / Runway / Luma / Hailuo        │
│  + Modal (serverless, sub-sekundowe zimne starty)              │
│  + Together AI / Lambda Labs (trenowanie, fine-tuning)         │
└─────────────────────────────────────────────────────────────────┘
```

## Przepływ danych (Pipeline generacji wideo)

```
Żądanie użytkownika
        │
        ▼
[FastAPI – walidacja i zlecenie]
        │
        ▼
[LangGraph Pipeline]
        │
        ├──[1. Analiza scenariusza (Claude)]
        │       └─ Podział na sceny, identyfikacja wymagań A/V
        │
        ├──[2. Optymalizacja promptów (DSPy MIPROv2)]
        │       └─ +21% poprawa jakości promptów
        │
        ├──[3. Generacja wideo (wybrany model)]
        │       └─ fal.ai / Vertex AI / Ray Serve (lokalne GPU)
        │
        ├──[4. Generacja audio (ElevenLabs / FishAudio)]
        │       └─ Synchronizacja ust, klonowanie głosu
        │
        ├──[5. Generacja muzyki (SOUNDRAW / ACE-Step)]
        │       └─ Dopasowanie nastroju i tempa do wideo
        │
        ├──[6. Post-processing (FFmpeg 8.0 + NVENC)]
        │       └─ Łączenie, napisy Whisper, kompresja
        │
        ├──[7. Moderacja treści (wielowarstwowa)]
        │       └─ NSFW / przemoc / prawa autorskie
        │
        └──[8. Znakowanie C2PA]
                └─ Kryptograficzny podpis, TikTok/EU AI Act
```

## Decyzje architektoniczne

### Dlaczego LangGraph nad CrewAI?
CrewAI: szybki prototyp (6-12 miesięcy), potem wymagany przepisanie do LangGraph.
LangGraph: trwałe wykonanie (stan przeżywa restart), human-in-the-loop, cache zadań.
Uber, LinkedIn, Klarna używają LangGraph w produkcji.

### Dlaczego ClickHouse nad PostgreSQL do analityki?
ClickHouse: setki milionów wierszy/s, sub-sekundowe odpowiedzi dla miliardów wierszy.
PostgreSQL: świetny do danych transakcyjnych (użytkownicy, projekty, metadane).
Używamy obu: PG dla OLTP, ClickHouse dla OLAP.

### Dlaczego Qdrant nad Pinecone/Weaviate?
Pre-filtering: Qdrant wykonuje złożone zapytania metadanych PRZED wyszukiwaniem wektorów.
Rust-native: 12K QPS, deterministyczne opóźnienia.
Multi-wektory: wizualne + audio + treść w jednym punkcie (unikalne dla naszego DNA wideo).
Cena: 100x tańszy niż Pinecone przy self-hosted.

### Dlaczego Kling 3.0 jako domyślny model?
Jedyny model z NATYWNYM 4K@60fps (nie upscaling).
Wielojęzyczna synchronizacja ust w 5 językach.
Łańcuchowanie 6 ujęć → 3-minutowe narracje.
Koszt: ~$0.07/s (3x tańszy niż Runway Gen-4.5).
