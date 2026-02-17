# Zgodność prawna i regulacje – ViraLoop

## Wymagania platform (stan na luty 2026)

### YouTube
- **Ujawnienie AI wymagane**: TAK (od listopada 2023)
- **Demonetyzacja masowych treści AI**: TAK (od lipca 2025)
- **Wyjątek**: treści z "znaczącym ludzkim wkładem twórczym" zachowują monetyzację
- **Test & Compare**: do 3 wariantów tytułu/miniatury, optymalizacja dla watch time (od XII 2025)
- **ViraLoop action**: Etykieta AI w metadanych + dokumentacja wkładu ludzkiego

### TikTok
- **Ujawnienie AI wymagane**: TAK (natychmiastowy strike za brak)
- **C2PA auto-detekcja**: TAK (wykrywa treści z 47 platform AI od stycznia 2025)
- **Wzrost usunięć vs 2024**: +340%
- **Trwałe bany**: 8600 kont za naruszenia AI
- **ViraLoop action**: Obowiązkowy C2PA manifest na wszystkich wideo

### Instagram (Meta)
- **Ujawnienie AI wymagane**: TAK
- **Nowe metryki Reels**: skip rate + repost counts (od grudnia 2025)
- **ViraLoop action**: Etykieta AI, integracja nowych metryk w analityce

### Facebook (Meta)
- **Ujawnienie AI wymagane**: TAK (szczególnie dla podobizn w reklamach)
- **ViraLoop action**: FTC compliance dla reklam z AI-generated likenesses

## Standard C2PA (Content Credentials)

### Co to jest?
C2PA (Coalition for Content Provenance and Authenticity) – standard kryptograficznego podpisywania treści cyfrowych z informacją o ich pochodzeniu.

### Kto to stosuje?
Google, Meta, TikTok, Adobe, Microsoft, BBC, Associated Press.

### Status standaryzacji
- Oczekiwana standaryzacja ISO w 2026
- Google SynthID: oznaczył >10 miliardów treści

### Implementacja w ViraLoop
```python
# Każde wygenerowane wideo otrzymuje manifest C2PA:
{
    "standard": "C2PA 2.1",
    "generator": "ViraLoop AI Platform/1.0",
    "data_generacji": "2026-02-17T10:00:00Z",
    "model_ai": "kling-3.0",
    "typ_zrodla": "trainedAlgorithmicMedia",
    "podpis_kryptograficzny": "sha256:..."
}
```

## EU AI Act (obowiązuje od 2 sierpnia 2026)

### Wymagania dla ViraLoop
1. **Etykietowanie**: Wszystkie treści AI muszą być wyraźnie oznaczone
2. **Transparentność**: Użytkownicy muszą wiedzieć, że rozmawiają/oglądają AI
3. **Rejestr systemów AI wysokiego ryzyka**: ViraLoop może być klasyfikowany jako system "ograniczonego ryzyka"
4. **Obowiązki dostawcy**: Dokumentacja techniczna, ocena ryzyka, mechanizmy nadzoru

### Kary za naruszenia
- Do **€35 000 000** lub **7% globalnego rocznego obrotu** (co wyższe)
- Dotyczy od 2 sierpnia 2026

### Działania prewencyjne ViraLoop
- [x] C2PA Content Credentials na wszystkich wideo
- [x] Panel zgodności w API (`/api/v1/zgodnosc/`)
- [ ] Dokumentacja techniczna systemów AI (do uzupełnienia)
- [ ] Ocena ryzyka EU AI Act (do uzupełnienia)
- [ ] Mechanizm zgłaszania incydentów

## FTC (USA) – Regulacje dotyczące AI

### Zakazy obowiązujące od 2025
- **Zakaz fałszywych recenzji AI**: Kara $51,744 za incydent
- **Obowiązkowe ujawnienie podobizn AI w reklamach**: TAK
- **Wymagane oznaczenie**: Wszystkie treści AI generowane dla celów reklamowych

## Prawa autorskie (stan na luty 2026)

### USA – US Copyright Office
- Proste prompty **nie** ustanawiają autorstwa
- **Ludzki wkład twórczy** (edycja, selekcja, kompozycja elementów AI) KWALIFIKUJE się do ochrony
- ViraLoop: zachęcaj użytkowników do dokumentowania procesu twórczego

### Ryzyko prawne modeli muzycznych
| Model | Ryzyko prawne | Zalecenie |
|-------|-------------|-----------|
| Suno v5 | WYSOKIE (pozwy Sony/Universal/Warner) | Unikaj dla komercji |
| MusicGen (Meta) | ŚREDNIE (modele: niekomercyjne) | Tylko do prototypów |
| SOUNDRAW | NISKIE (własne dane, licencja wieczysta) | ✅ Rekomendowany |
| Beatoven.ai | NISKIE (licencjonowane dane) | ✅ Rekomendowany |
| ACE-Step | NIEZNANE (niejasny status danych) | Skonsultuj prawnika |

## Moderacja treści

### Wielowarstwowy system ViraLoop

```
Warstwa 1: Filtrowanie promptów wejściowych
  ↓ (blokowanie treści zakazanych: CSAM, terroryzm, etc.)
Warstwa 2: Bezpieczeństwo modelu (wbudowane w modele AI)
  ↓ (instrukcje bezpieczeństwa w promptach systemowych)
Warstwa 3: Klasyfikatory wyjścia
  ↓ NSFW (próg: 0.7) | Przemoc (0.6) | Nienawiść (0.5) | Copyright (0.8)
Warstwa 4: Eskalacja do recenzji człowieka
  ↓ (przypadki graniczne, treści wrażliwe)
Warstwa 5: C2PA znakowanie (log proweniencji)
```

### Narzędzia moderacji
- **Azure AI Content Safety**: komercyjny, wielojęzyczny
- **Własne klasyfikatory**: fine-tuned CLIP/ViT dla domen specyficznych
- **Human review**: interfejs moderatora w panelu administracyjnym

## Lista kontrolna zgodności przed uruchomieniem produkcji

- [ ] Implementacja C2PA na wszystkich wygenerowanych wideo
- [ ] Automatyczne etykiety "Treść wygenerowana przez AI" na platformach
- [ ] Dokumentacja techniczna systemów AI (EU AI Act)
- [ ] Polityka prywatności zgodna z RODO (PL) / GDPR (EU)
- [ ] Regulamin użytkowania z klauzulami o treściach AI
- [ ] Mechanizm DMCA takedown dla naruszeń praw autorskich
- [ ] Proces weryfikacji tożsamości dla kont Enterprise
- [ ] Szkolenie moderatorów (treści AI + przepisy)
- [ ] Ocena ryzyka EU AI Act (Artykuł 9)
- [ ] Audyt bezpieczeństwa (penetration testing)
