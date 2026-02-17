#!/bin/bash
# ============================================================
# ViraLoop – Skrypt uruchamiania środowiska deweloperskiego
# Użycie: ./infrastructure/scripts/uruchom-dev.sh
# ============================================================

set -euo pipefail

ZIELONY='\033[0;32m'
ZOLTY='\033[1;33m'
CZERWONY='\033[0;31m'
RESET='\033[0m'

log_info() { echo -e "${ZIELONY}[INFO]${RESET} $1"; }
log_warn() { echo -e "${ZOLTY}[UWAGA]${RESET} $1"; }
log_blad() { echo -e "${CZERWONY}[BŁĄD]${RESET} $1"; }

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     ViraLoop – Uruchamianie środowiska deweloperskiego   ║"
echo "║     Platforma AI do generowania wirusowych treści wideo  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Sprawdź wymagania
log_info "Sprawdzam wymagania systemowe..."

if ! command -v docker &> /dev/null; then
    log_blad "Docker nie jest zainstalowany. Zainstaluj Docker 24+."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    log_blad "Docker Compose v2 nie jest zainstalowany."
    exit 1
fi

if ! command -v node &> /dev/null; then
    log_warn "Node.js nie znaleziony. Frontend nie będzie dostępny w trybie hot-reload."
fi

if ! command -v python3 &> /dev/null; then
    log_warn "Python 3 nie znaleziony. Backend nie będzie dostępny w trybie hot-reload."
fi

# Sprawdź plik .env
if [ ! -f ".env" ]; then
    log_warn "Plik .env nie istnieje. Kopiuję z .env.example..."
    cp .env.example .env
    log_warn "Wypełnij plik .env własnymi kluczami API przed użyciem w produkcji!"
fi

# Uruchom serwisy infrastruktury przez Docker Compose
log_info "Uruchamianie serwisów infrastruktury..."
docker compose up -d \
    clickhouse \
    qdrant \
    redis \
    postgres \
    minio

# Poczekaj na gotowość baz danych
log_info "Oczekiwanie na gotowość baz danych..."
sleep 5

docker compose exec clickhouse clickhouse-client \
    --query "SELECT 'ClickHouse gotowy'" 2>/dev/null \
    && log_info "ClickHouse: OK" \
    || log_warn "ClickHouse: nie odpowiada jeszcze"

docker compose exec redis redis-cli ping 2>/dev/null \
    && log_info "Redis: OK" \
    || log_warn "Redis: nie odpowiada jeszcze"

# Instrukcje uruchamiania backendu i frontendu
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Infrastruktura uruchomiona. Uruchom ręcznie:"
echo ""
echo "  Backend (terminal 1):"
echo "    cd backend"
echo "    pip install -r requirements.txt"
echo "    uvicorn backend.api.main:aplikacja --reload"
echo ""
echo "  Frontend (terminal 2):"
echo "    cd frontend"
echo "    npm install"
echo "    npm run dev"
echo ""
echo "  Dostęp:"
echo "    Frontend:       http://localhost:3000"
echo "    API:            http://localhost:8000/api/docs"
echo "    ClickHouse:     http://localhost:8123/play"
echo "    Qdrant:         http://localhost:6333/dashboard"
echo "    MinIO:          http://localhost:9002"
echo "    Grafana:        http://localhost:3001  (admin/admin123)"
echo "    Prometheus:     http://localhost:9090"
echo "════════════════════════════════════════════════════════════"
echo ""

log_info "Środowisko deweloperskie gotowe!"
