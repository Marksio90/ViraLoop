# Modele cenowe i analiza kosztów ViraLoop

## Plany subskrypcji

| Plan | Cena PLN | Cena USD | Kredyty | Rozdzielczość | Komercyjne | API |
|------|----------|----------|---------|---------------|------------|-----|
| **Darmowy** | 0 zł/mies | $0 | 10/mies | 480p (watermark) | ❌ | ❌ |
| **Twórca** | 29 zł/mies | ~$7 | 100/mies | 1080p | ✅ | ❌ |
| **Profesjonalny** | 99 zł/mies | ~$25 | 500/mies | 4K | ✅ | ❌ |
| **Enterprise** | od 2000 zł/mies | od ~$500 | Nieogr. | 4K@60fps | ✅ | ✅ |

*1 kredyt = 1 wideo (do 60s). Dodatkowe kredyty do kupienia.*

## Koszt generacji wideo (za sekundę)

| Model | Koszt/s | Rekomendacja |
|-------|---------|-------------|
| LTX-Video (open-source) | ~$0.01 | Prototypy, masowe testy |
| HunyuanVideo 1.5 (open-source) | ~$0.015 | Ekonomiczne wideo 720p |
| Wan2.2 (open-source) | ~$0.02 | Najlepsza jakość open-source |
| Kling 3.0 (via fal.ai) | ~$0.07 | **Rekomendowany domyślny** |
| Runway Gen-4 Turbo | $0.05 | Szybkie 1080p |
| Sora 2 Standard | $0.10 | Narracja, 720p |
| Veo 3.1 Fast | $0.15 | Szybkie z audio |
| Hailuo 02 | ~$0.05 | Ekonomiczny #2 bench |
| Runway Gen-4.5 | $0.25 | Premium bez audio |
| Sora 2 Pro | $0.50 | Najwyższa jakość Sora |
| Veo 3.1 Standard | $0.40 | Premium z audio |

## Analiza rentowności

### Scenariusz: Plan Twórca (29 zł/mies, 100 kredytów)

Zakładając średnio 15s wideo na kredyt:
- Koszt generacji Kling 3.0: 15s × $0.07 = **$1.05/wideo**
- 100 kredytów = **$105 koszt API**
- Przychód: **29 zł ≈ $7.25** (przelicznik 1 USD = 4 PLN)

**Wniosek**: Plan Twórca jest deficytowy przy modelu premium. Rozwiązania:
1. Użyj HunyuanVideo 1.5 ($0.015/s → $0.225/wideo) dla niższych planów
2. Ogranicz długość wideo na planie Twórca do 8s max
3. Użyj kolejkowania i wsadowania przez własny klaster GPU

### Scenariusz z własnym klastrem GPU (H100)

Dzierżawa H100: **$2-4/godzinę** (RunPod/Lambda Labs)
Wan2.2: ~1.5 minuty na 10s wideo → 40 wideo/godzinę
Koszt wideo: $3 / 40 = **$0.075/wideo (własne GPU)**
vs $0.07-1.05 za wideo API

Przy 60%+ obciążeniu GPU: zarezerwuj instancje → **$1.5-2/h**

### Ścieżka do $100M ARR

Walidacja rynkowa:
- Synthesia: **$146M ARR**, 70% z Fortune 100
- HeyGen: **$95M ARR** w 30 miesiącach (PLG)
- Runway: **$90M ARR** (ale przy dużych stratach $155M EBITDA)

Model hybrydowy: **subskrypcje + kredyty + marketplace**

Dodatkowe strumienie przychodu:
1. **Marketplace szablonów AI**: 65/35 podział (twórca/platforma)
2. **Licencjonowanie API**: jak HeyGen w integracji z HubSpot/Canva
3. **White-label Enterprise**: dla branż regulowanych
4. **Program podziału przychodów**: 55/45 (jak YouTube) dla monetyzowanych treści

### TAM (Total Addressable Market)

| Segment | Wartość 2025 | CAGR | Wartość 2033 |
|---------|-------------|------|-------------|
| AI generowanie wideo | ~$700M | 20-32% | $2.6B+ |
| Cały ekosystem AI wideo | $5B | 25% | $42B |

**Kluczowe spostrzeżenie Synthesia**: Średni klient enterprise tworzy treści w 7 językach.
40% wszystkich wideo to tłumaczenia. Wielojęzyczność = mnożnik przychodów.

## Porównanie dostawców GPU

| Dostawca | H100 $/hr | Serverless | Najlepszy do |
|----------|-----------|-----------|-------------|
| **fal.ai** ($4.5B) | Per-output | ✅ | API generacji wideo |
| **Modal** ($1.1B) | $3.95 | ✅ | Własne modele, DX |
| **RunPod** | $1.99-2.72 | ✅ | Budżetowe wnioskowanie |
| **Together AI** | $1.76-2.39 | Tylko wnioskowanie | Trenowanie/fine-tuning |
| **Lambda Labs** | $2.99 | ❌ | Klastry treningowe, 0 egress |
| **CoreWeave** | $4.25-6.15 | ❌ | Enterprise K8s, InfiniBand |
| **Vast.ai** | $1.49-2.00 | ❌ | Badania (brak SLA) |

*Ceny H100 spadły z $8/h (2023) do $2-4/h (2025) – trend korzystny dla builderów.*
