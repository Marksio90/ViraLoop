-- ============================================================
--  NEXUS — Inicjalizacja Bazy Danych PostgreSQL
--  Uruchamiane automatycznie przy pierwszym starcie kontenera
-- ============================================================

-- Włącz rozszerzenia
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ─── Użytkownicy ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uzytkownicy (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    nazwa       VARCHAR(100) NOT NULL,
    plan        VARCHAR(20) DEFAULT 'darmowy' CHECK (plan IN ('darmowy', 'tworca', 'pro', 'enterprise')),
    aktywny     BOOLEAN DEFAULT TRUE,
    stworzony   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    zaktualizowany TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── Projekty ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projekty (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    uzytkownik_id UUID REFERENCES uzytkownicy(id) ON DELETE CASCADE,
    nazwa       VARCHAR(200) NOT NULL,
    opis        TEXT,
    marka       JSONB DEFAULT '{}',
    stworzony   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── Zadania Wideo ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS zadania_wideo (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sesja_id        VARCHAR(20) UNIQUE NOT NULL,
    task_id         VARCHAR(100),               -- Celery task ID
    projekt_id      UUID REFERENCES projekty(id) ON DELETE SET NULL,
    uzytkownik_id   UUID REFERENCES uzytkownicy(id) ON DELETE SET NULL,

    -- Wejście
    brief           TEXT NOT NULL,
    platforma       JSONB DEFAULT '["tiktok"]',
    marka           JSONB DEFAULT '{}',
    parametry       JSONB DEFAULT '{}',

    -- Status
    status          VARCHAR(30) DEFAULT 'w_kolejce'
                    CHECK (status IN ('w_kolejce', 'w_trakcie', 'sukces', 'czesciowy', 'blad', 'anulowane')),
    procent         SMALLINT DEFAULT 0 CHECK (procent BETWEEN 0 AND 100),

    -- Wyniki
    wynik_json      JSONB,                      -- Pełny wynik pipeline
    plan_tresci     JSONB,
    scenariusz      JSONB,
    ocena_jakosci   JSONB,
    ocena_wiralnosci JSONB,
    nwv_score       SMALLINT,                   -- NEXUS Viral Score 0-100
    wideo_sciezka   TEXT,
    miniatura_sciezka TEXT,

    -- Finanse
    koszt_usd       DECIMAL(10, 4) DEFAULT 0,

    -- Czasy
    czas_generacji_s DECIMAL(10, 1),
    stworzony       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    rozpoczety      TIMESTAMP WITH TIME ZONE,
    zakonczony      TIMESTAMP WITH TIME ZONE,

    -- Błędy
    bledy           JSONB DEFAULT '[]'
);

-- ─── Analityka Wideo ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analityka_wideo (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zadanie_id      UUID REFERENCES zadania_wideo(id) ON DELETE CASCADE,
    platforma       VARCHAR(30) NOT NULL,

    -- Metryki (aktualizowane po publikacji)
    wyswietlenia    BIGINT DEFAULT 0,
    polubienia      BIGINT DEFAULT 0,
    komentarze      BIGINT DEFAULT 0,
    udostepnienia   BIGINT DEFAULT 0,
    zasieg          BIGINT DEFAULT 0,
    czas_ogladania_s BIGINT DEFAULT 0,
    wspolczynnik_ukonczenia DECIMAL(5, 2),      -- completion rate %

    -- Timestamp
    pobrano_o       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── Indeksy ─────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_zadania_sesja_id ON zadania_wideo(sesja_id);
CREATE INDEX IF NOT EXISTS idx_zadania_status ON zadania_wideo(status);
CREATE INDEX IF NOT EXISTS idx_zadania_stworzony ON zadania_wideo(stworzony DESC);
CREATE INDEX IF NOT EXISTS idx_zadania_nwv ON zadania_wideo(nwv_score DESC) WHERE nwv_score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_analityka_zadanie ON analityka_wideo(zadanie_id);

-- ─── Widoki ──────────────────────────────────────────────────
CREATE OR REPLACE VIEW v_statystyki_platformy AS
SELECT
    DATE_TRUNC('day', stworzony) AS dzien,
    COUNT(*) AS liczba_wideo,
    COUNT(*) FILTER (WHERE status = 'sukces') AS udane,
    COUNT(*) FILTER (WHERE status = 'blad') AS nieudane,
    AVG(nwv_score) AS sredni_nwv,
    AVG(koszt_usd) AS sredni_koszt_usd,
    SUM(koszt_usd) AS calkowity_koszt_usd,
    AVG(czas_generacji_s) AS sredni_czas_s
FROM zadania_wideo
GROUP BY DATE_TRUNC('day', stworzony)
ORDER BY dzien DESC;

-- ─── Dane testowe ────────────────────────────────────────────
INSERT INTO uzytkownicy (email, nazwa, plan)
VALUES
    ('admin@nexus.local', 'Admin NEXUS', 'enterprise'),
    ('tworca@nexus.local', 'Testowy Twórca', 'pro')
ON CONFLICT (email) DO NOTHING;

-- Potwierdzenie
DO $$
BEGIN
    RAISE NOTICE 'NEXUS — Baza danych zainicjalizowana pomyślnie!';
    RAISE NOTICE 'Tabele: uzytkownicy, projekty, zadania_wideo, analityka_wideo';
    RAISE NOTICE 'Widoki: v_statystyki_platformy';
END $$;
