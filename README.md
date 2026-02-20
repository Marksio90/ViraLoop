# NEXUS — AI Video Factory

**Bezkonkurencyjna, wieloagentowa platforma do tworzenia wirusowych krótkich wideo.**
Na kluczu OpenAI. W pełni po polsku. ~$0.14/wideo. ~90 sekund generacji.

> Poprzednia wersja (ViraLoop) używała 10+ zewnętrznych API za $1.07/wideo.
> NEXUS osiąga to samo **wyłącznie na kluczu OpenAI za ~$0.147/wideo**.

---

## Architektura Multi-Agentowa (LangGraph)

```
Brief użytkownika
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│           ORKIESTRATOR (LangGraph v1.0)                  │
│  State Machine + Checkpoint + Auto-Retry (max 3x)        │
├──────────┬──────────┬──────────────┬────────────────────┤
│  Strateg │  Pisarz  │   Reżyser    │   Producent        │
│  Treści  │Scenariuszy│   Głosu     │   Wizualny         │
│          │          │              │                    │
│GPT-4o-mini│GPT-4o-mini│ TTS-1     │   DALL-E 3         │
│  + RAG   │  + Brand │  6 głosów   │   9:16 Pionowy     │
│ ~$0.001  │ ~$0.002  │  ~$0.018    │   ~$0.120          │
└──────────┴──────────┴──────────────┴────────────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  Recenzent Jakości   │
         │     GPT-4o           │
         │     ~$0.005          │
         │                      │
         │  wynik >= 60 → ✅    │
         │  wynik <  60 → 🔁    │ (auto-retry, max 3x)
         └────────┬─────────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │     COMPOSITOR       │
         │     FFmpeg           │
         │  Ken Burns + Fade    │
         │  MP4 1080x1920       │
         └────────┬─────────────┘
                  │
                  ▼
       Gotowe wideo + NVS Score
```

---

## Koszt na Wideo

| Komponent | Model OpenAI | Koszt |
|---|---|---|
| Strategia + Scenariusz | GPT-4o-mini | ~$0.003 |
| Narracja audio | OpenAI TTS-1 | ~$0.018 |
| Obrazy (3 sceny) | DALL-E 3 | ~$0.120 |
| Recenzja jakości | GPT-4o | ~$0.005 |
| Embeddingi RAG | text-embedding-3-small | ~$0.001 |
| **RAZEM** | | **~$0.147** |

**7x taniej** niż poprzednia architektura ($1.07/wideo).

---

## NEXUS Viral Score (NVS)

- 🔥 **85-100** — Wysoki potencjał wiralny
- ✅ **60-84** — Dobry content, publikuj
- ⚠️ **<60** — Auto-retry (max 3 próby)

---

## Szybki Start

```bash
git clone <repo> && cd ViraLoop
cp .env.example .env
# Ustaw OPENAI_API_KEY w .env

# Backend
cd backend && pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

API Docs: http://localhost:8000/docs
Studio: http://localhost:3000/studio
Analityka NVS: http://localhost:3000/analityka

---

## Kluczowe możliwości

- **Generowanie wideo klasy kinematograficznej** – integracja z Kling 3.0, Veo 3.1, Runway Gen-4.5 i modelami open-source (Wan2.2, HunyuanVideo 1.5)
- **Synteza głosu i muzyki** – ElevenLabs Eleven v3, FishAudio S1, ACE-Step 1.5
- **Wielojęzyczny pipeline** – tłumaczenie i klonowanie głosu w 20+ językach
- **Ewolucyjna optymalizacja treści** – algorytmy genetyczne (PyGAD) + bandyci Thompsona
- **Analityka w czasie rzeczywistym** – ClickHouse + Qdrant + integracje z YouTube/TikTok/Instagram
- **Orkiestracja agentów AI** – LangGraph 1.0 + DSPy + protokoły MCP/A2A
- **Zgodność z C2PA** – znakowanie wodne i weryfikacja autentyczności treści

## Architektura systemu

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 16)                    │
│  Dashboard │ Studio Wideo │ Analityka │ Biblioteka │ Ustawienia  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ API REST / WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                     BACKEND (FastAPI + Python)                  │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Orkiestracja│  │  Generacja   │  │      Analityka         │ │
│  │  LangGraph  │  │  Wideo/Audio │  │  ClickHouse + Qdrant   │ │
│  │    DSPy     │  │    Muzyki    │  │  Alg. Genetyczne       │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  WARSTWA OBLICZENIOWA                           │
│   Ray (KubeRay) │ fal.ai │ Modal │ Together AI │ Lambda Labs   │
└─────────────────────────────────────────────────────────────────┘
```

## Stos technologiczny

### Generowanie wideo
| Warstwa | Technologia | Zastosowanie |
|---------|-------------|--------------|
| Tier 1 (premium) | Kling 3.0, Veo 3.1, Runway Gen-4.5 | Produkcja finalna |
| Tier 2 (ekonomiczny) | Hailuo 02, Luma Ray 3 | Masowe generowanie |
| Open-source | Wan2.2, HunyuanVideo 1.5, LTX-Video | Samodzielny hosting |

### Infrastruktura
| Komponent | Technologia |
|-----------|-------------|
| Orkiestracja agentów | LangGraph 1.0 |
| Optymalizacja promptów | DSPy v3.1.3 (MIPROv2) |
| Obliczenia rozproszone | Ray 2.53.0 (KubeRay) |
| Baza danych analitycznych | ClickHouse v26.1 |
| Baza wektorowa | Qdrant |
| Frontend | Next.js 16 + shadcn/ui |
| Renderowanie | Remotion 4.x + FFmpeg 8.0 |
| Przeglądarkowy podgląd | Diffusion Studio (WebGPU) |
| Współpraca w czasie rzeczywistym | Liveblocks + Yjs |

## Instalacja i uruchomienie

### Wymagania
- Docker 24+ i Docker Compose 2.x
- Node.js 20+ (dla frontendu)
- Python 3.11+ (dla backendu)
- CUDA 12.x + GPU z min. 16GB VRAM (dla lokalnych modeli)

### Szybki start

```bash
# Sklonuj repozytorium
git clone https://github.com/Marksio90/ViraLoop.git
cd ViraLoop

# Skonfiguruj zmienne środowiskowe
cp .env.example .env
# Wypełnij .env kluczami API

# Uruchom przez Docker Compose
docker compose up -d

# Frontend (tryb deweloperski)
cd frontend && npm install && npm run dev

# Backend (tryb deweloperski)
cd backend && pip install -r requirements.txt && uvicorn api.main:app --reload
```

### Wymagane klucze API

```bash
# Generowanie wideo
FAL_API_KEY=          # fal.ai (Kling, Luma, Runway)
RUNWAYML_API_KEY=     # Runway Gen-4.5 bezpośrednio
GOOGLE_API_KEY=       # Veo 3.1 przez Vertex AI

# Głos i muzyka
ELEVENLABS_API_KEY=   # ElevenLabs v3
FISHAUDIO_API_KEY=    # FishAudio S1

# LLM i orkiestracja
ANTHROPIC_API_KEY=    # Claude (tłumaczenia, scenariusze)
OPENAI_API_KEY=       # GPT-4o (orkiestracja DSPy)

# Analityka platform
YOUTUBE_API_KEY=      # YouTube Data API v3
TIKTOK_API_KEY=       # TikTok Research API
```

## Modele cenowe

| Plan | Cena | Kredyty wideo | Rozdzielczość | Użycie komercyjne |
|------|------|---------------|---------------|-------------------|
| Darmowy | 0 zł/mies | 10/mies | 480p (z watermarkiem) | ❌ |
| Twórca | 29 zł/mies | 100/mies | 1080p | ✅ |
| Profesjonalny | 99 zł/mies | 500/mies | 4K | ✅ |
| Enterprise | od 2000 zł/mies | Nielimitowane | 4K@60fps | ✅ + API |

## Struktura projektu

```
ViraLoop/
├── backend/                    # Backend Python (FastAPI)
│   ├── orchestration/          # LangGraph, DSPy
│   ├── generation/             # Generowanie wideo, audio, muzyki
│   ├── analytics/              # ClickHouse, Qdrant, alg. ewolucyjne
│   ├── api/                    # Endpointy REST i WebSocket
│   ├── compliance/             # C2PA, moderacja treści
│   └── utils/                  # Narzędzia pomocnicze
├── frontend/                   # Frontend Next.js 16
│   ├── app/                    # Routing App Router
│   ├── components/             # Komponenty React
│   ├── lib/                    # Biblioteki pomocnicze
│   └── hooks/                  # Hooki React
├── infrastructure/             # Infrastruktura
│   ├── docker/                 # Pliki Docker
│   ├── kubernetes/             # Manifesty K8s
│   └── scripts/                # Skrypty operacyjne
└── docs/                       # Dokumentacja (PL)
```

## Licencja

Copyright © 2026 ViraLoop. Wszelkie prawa zastrzeżone.

Kod źródłowy na licencji MIT. Szczegóły w pliku [LICENSE](LICENSE).

---

*Zbudowano z ❤️ w Polsce. Obsługa 20+ języków, pełna zgodność z przepisami EU AI Act.*
