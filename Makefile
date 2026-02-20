# ============================================================
#  NEXUS — AI Video Factory
#  Jedno polecenie. Cała platforma.
#  Użycie: make help
# ============================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Kolory w terminalu
BOLD   := $(shell tput bold)
GREEN  := $(shell tput setaf 2)
YELLOW := $(shell tput setaf 3)
CYAN   := $(shell tput setaf 6)
RESET  := $(shell tput sgr0)

# Konfiguracja
COMPOSE      := docker compose
COMPOSE_DEV  := docker compose -f docker-compose.yml -f docker-compose.dev.yml
API_URL      := http://localhost
BRIEF        ?= "Pokaż jak 10 minut medytacji rano zmienia produktywność całego dnia"

# ─────────────────────────────────────────────────────────────
#  URUCHAMIANIE
# ─────────────────────────────────────────────────────────────

.PHONY: start
start: _sprawdz_env ## 🚀  Uruchom NEXUS (tryb produkcyjny)
	@echo "$(BOLD)$(GREEN)🚀 Uruchamiam platformę NEXUS...$(RESET)"
	@$(COMPOSE) up -d --remove-orphans
	@echo ""
	@echo "$(BOLD)$(GREEN)✅ NEXUS gotowy!$(RESET)"
	@echo ""
	@echo "  $(CYAN)🌐 Studio         $(RESET)→ http://localhost"
	@echo "  $(CYAN)📖 API Docs       $(RESET)→ http://localhost/docs"
	@echo "  $(CYAN)🌸 Flower (jobs)  $(RESET)→ http://localhost:5555"
	@echo "  $(CYAN)📊 Grafana        $(RESET)→ http://localhost:3001  (admin/nexus)"
	@echo "  $(CYAN)📡 Prometheus     $(RESET)→ http://localhost:9090"
	@echo ""

.PHONY: dev
dev: _sprawdz_env ## 🔧  Tryb deweloperski (hot-reload)
	@echo "$(BOLD)$(YELLOW)🔧 Tryb deweloperski NEXUS...$(RESET)"
	@$(COMPOSE_DEV) up

.PHONY: stop
stop: ## ⏹  Zatrzymaj wszystkie serwisy
	@echo "$(YELLOW)⏹ Zatrzymuję NEXUS...$(RESET)"
	@$(COMPOSE) down

.PHONY: restart
restart: ## 🔄  Zrestartuj wszystkie serwisy
	@$(COMPOSE) restart

.PHONY: restart-backend
restart-backend: ## 🔄  Zrestartuj tylko backend
	@$(COMPOSE) restart backend celery-worker

# ─────────────────────────────────────────────────────────────
#  BUILD
# ─────────────────────────────────────────────────────────────

.PHONY: build
build: ## 🔨  Zbuduj obrazy Docker
	@echo "$(BOLD)$(YELLOW)🔨 Buduję obrazy...$(RESET)"
	@$(COMPOSE) build

.PHONY: rebuild
rebuild: ## 🔨  Zbuduj od zera (bez cache)
	@echo "$(BOLD)$(YELLOW)🔨 Buduję bez cache...$(RESET)"
	@$(COMPOSE) build --no-cache --pull

.PHONY: pull
pull: ## ⬇  Pobierz najnowsze obrazy bazowe
	@$(COMPOSE) pull

# ─────────────────────────────────────────────────────────────
#  LOGI
# ─────────────────────────────────────────────────────────────

.PHONY: logs
logs: ## 📜  Pokaż wszystkie logi (live)
	@$(COMPOSE) logs -f

.PHONY: logs-backend
logs-backend: ## 📜  Logi backendu
	@$(COMPOSE) logs -f backend

.PHONY: logs-worker
logs-worker: ## 📜  Logi Celery worker
	@$(COMPOSE) logs -f celery-worker

.PHONY: logs-nginx
logs-nginx: ## 📜  Logi Nginx
	@$(COMPOSE) logs -f nginx

.PHONY: logs-frontend
logs-frontend: ## 📜  Logi frontendu
	@$(COMPOSE) logs -f frontend

# ─────────────────────────────────────────────────────────────
#  GENERACJA WIDEO
# ─────────────────────────────────────────────────────────────

.PHONY: wideo
wideo: ## 🎬  Wygeneruj wideo (make wideo BRIEF="Twój temat")
	@echo "$(BOLD)$(GREEN)🎬 Uruchamiam pipeline generacji wideo...$(RESET)"
	@echo "   Brief: $(BRIEF)"
	@echo ""
	@curl -s -X POST $(API_URL)/api/v1/wideo/generuj \
		-H "Content-Type: application/json" \
		-d "{\"brief\":$(BRIEF),\"platforma\":[\"tiktok\",\"youtube\"],\"dlugosc_sekund\":60,\"glos\":\"nova\"}" \
		| python3 -m json.tool
	@echo ""

.PHONY: wiralnosc
wiralnosc: ## 🔮  Analizuj wiralność briefu (make wiralnosc BRIEF="...")
	@echo "$(BOLD)$(CYAN)🔮 Analizuję wiralność...$(RESET)"
	@curl -s -X POST $(API_URL)/api/v1/wideo/wiralnosc \
		-H "Content-Type: application/json" \
		-d "{\"brief\":$(BRIEF),\"platforma\":[\"tiktok\",\"youtube\"],\"dlugosc_sekund\":60}" \
		| python3 -m json.tool

.PHONY: historia
historia: ## 📚  Historia wygenerowanych wideo
	@curl -s $(API_URL)/api/v1/wideo/historia | python3 -m json.tool

# ─────────────────────────────────────────────────────────────
#  STATUS I MONITORING
# ─────────────────────────────────────────────────────────────

.PHONY: status
status: ## 📊  Status wszystkich serwisów
	@echo "$(BOLD)NEXUS — Status Serwisów$(RESET)"
	@$(COMPOSE) ps

.PHONY: health
health: ## 🏥  Health check platformy
	@echo "$(BOLD)$(CYAN)🏥 Sprawdzam zdrowie NEXUS...$(RESET)"
	@curl -s $(API_URL)/api/zdrowie | python3 -m json.tool

.PHONY: modele
modele: ## 🤖  Lista modeli AI i kosztów
	@curl -s $(API_URL)/api/modele | python3 -m json.tool

.PHONY: stats
stats: ## 📈  Statystyki zasobów Docker
	@docker stats --no-stream $(shell $(COMPOSE) ps -q)

.PHONY: top
top: ## 🔝  Live monitoring zasobów
	@docker stats $(shell $(COMPOSE) ps -q)

# ─────────────────────────────────────────────────────────────
#  BAZA DANYCH
# ─────────────────────────────────────────────────────────────

.PHONY: db-shell
db-shell: ## 🗄  Konsola PostgreSQL
	@$(COMPOSE) exec postgres psql -U nexus nexus

.PHONY: db-backup
db-backup: ## 💾  Backup bazy danych
	@echo "$(YELLOW)💾 Tworzę backup...$(RESET)"
	@mkdir -p backups
	@$(COMPOSE) exec postgres pg_dump -U nexus nexus > backups/nexus_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Backup zapisany w backups/$(RESET)"

.PHONY: redis-cli
redis-cli: ## 🔴  Konsola Redis
	@$(COMPOSE) exec redis redis-cli

.PHONY: redis-flush
redis-flush: ## 🔴  Wyczyść cache Redis (zachowaj zadania Celery)
	@$(COMPOSE) exec redis redis-cli FLUSHDB

# ─────────────────────────────────────────────────────────────
#  POWŁOKI
# ─────────────────────────────────────────────────────────────

.PHONY: shell-backend
shell-backend: ## 💻  Shell w kontenerze backendu
	@$(COMPOSE) exec backend bash

.PHONY: shell-frontend
shell-frontend: ## 💻  Shell w kontenerze frontendu
	@$(COMPOSE) exec frontend sh

.PHONY: shell-nginx
shell-nginx: ## 💻  Shell w kontenerze Nginx
	@$(COMPOSE) exec nginx sh

# ─────────────────────────────────────────────────────────────
#  TESTY
# ─────────────────────────────────────────────────────────────

.PHONY: test
test: ## 🧪  Uruchom testy
	@$(COMPOSE) exec backend pytest tests/ -v --color=yes

.PHONY: test-api
test-api: ## 🧪  Test API (wszystkie endpointy)
	@echo "$(BOLD)$(CYAN)🧪 Testuję API...$(RESET)"
	@echo "\n→ Health check:"
	@curl -sf $(API_URL)/api/zdrowie | python3 -m json.tool
	@echo "\n→ Modele:"
	@curl -sf $(API_URL)/api/modele | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Liczba modeli: {len(d[\"modele\"])}')"
	@echo "\n→ Historia wideo:"
	@curl -sf $(API_URL)/api/v1/wideo/historia | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Wideo w historii: {d[\"total\"]}')"
	@echo "\n$(GREEN)✅ API działa poprawnie$(RESET)"

# ─────────────────────────────────────────────────────────────
#  CZYSZCZENIE
# ─────────────────────────────────────────────────────────────

.PHONY: clean-videos
clean-videos: ## 🗑  Usuń wygenerowane wideo
	@echo "$(YELLOW)🗑 Usuwam wygenerowane wideo...$(RESET)"
	@rm -rf dane/wideo/*
	@echo "$(GREEN)✅ Wideo usunięte$(RESET)"

.PHONY: clean
clean: ## ⚠️   Usuń kontenery i volumes (UWAGA: kasuje dane!)
	@echo "$(YELLOW)⚠️  Usuwam całą platformę NEXUS (dane zostaną usunięte)...$(RESET)"
	@read -p "Czy na pewno? [y/N] " -n 1 -r; echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(COMPOSE) down -v --remove-orphans; \
		echo "$(GREEN)✅ Gotowe$(RESET)"; \
	else \
		echo "$(YELLOW)Anulowano$(RESET)"; \
	fi

.PHONY: prune
prune: ## ⚠️   Docker system prune (zwalnia miejsce)
	@docker system prune -f

# ─────────────────────────────────────────────────────────────
#  KONFIGURACJA
# ─────────────────────────────────────────────────────────────

.PHONY: setup
setup: ## ⚙️   Pierwsza konfiguracja (kopiuje .env, tworzy katalogi)
	@echo "$(BOLD)$(CYAN)⚙️  Konfiguracja NEXUS...$(RESET)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✅ Stworzono .env — uzupełnij OPENAI_API_KEY!$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  .env już istnieje$(RESET)"; \
	fi
	@mkdir -p dane/wideo dane/chroma backups
	@echo "$(GREEN)✅ Katalogi stworzone$(RESET)"

.PHONY: _sprawdz_env
_sprawdz_env:
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)⚠️  Brak pliku .env — uruchom: make setup$(RESET)"; \
		exit 1; \
	fi
	@if ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then \
		echo "$(YELLOW)⚠️  Brak klucza OpenAI w .env$(RESET)"; \
		echo "   Edytuj .env i dodaj: OPENAI_API_KEY=sk-proj-..."; \
	fi

# ─────────────────────────────────────────────────────────────
#  POMOC
# ─────────────────────────────────────────────────────────────

.PHONY: help
help: ## 📖  Pokaż tę pomoc
	@echo ""
	@echo "$(BOLD)$(CYAN)╔════════════════════════════════════════════╗$(RESET)"
	@echo "$(BOLD)$(CYAN)║        NEXUS — AI Video Factory            ║$(RESET)"
	@echo "$(BOLD)$(CYAN)║   Bezkonkurencyjna platforma wideo AI      ║$(RESET)"
	@echo "$(BOLD)$(CYAN)╚════════════════════════════════════════════╝$(RESET)"
	@echo ""
	@echo "$(BOLD)Dostępne komendy:$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-22s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)Przykłady:$(RESET)"
	@echo "  make setup                              # Pierwsza konfiguracja"
	@echo "  make start                              # Uruchom platformę"
	@echo "  make wideo BRIEF='Temat wideo'          # Wygeneruj wideo"
	@echo "  make wiralnosc BRIEF='Temat wideo'      # Sprawdź wiralność"
	@echo "  make logs-backend                       # Logi backendu"
	@echo "  make health                             # Sprawdź zdrowie"
	@echo ""
	@echo "$(BOLD)URLs po uruchomieniu:$(RESET)"
	@echo "  $(CYAN)http://localhost$(RESET)         Studio wideo"
	@echo "  $(CYAN)http://localhost/docs$(RESET)    API Documentation"
	@echo "  $(CYAN)http://localhost:5555$(RESET)    Flower (monitoring zadań)"
	@echo "  $(CYAN)http://localhost:3001$(RESET)    Grafana (metryki)"
	@echo "  $(CYAN)http://localhost:9090$(RESET)    Prometheus"
	@echo ""
