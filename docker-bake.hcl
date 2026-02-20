# ====================================================================
# NEXUS — Docker Bake Configuration
# AI Video Factory | docker buildx bake [target|group]
#
# Użycie:
#   docker buildx bake                        # zbuduj wszystko
#   docker buildx bake backend                # tylko backend
#   docker buildx bake backend-services       # backend + workery
#   docker buildx bake --set *.platform=linux/amd64,linux/arm64
#
# Ze zdalnym cache:
#   REGISTRY=ghcr.io/org docker buildx bake --push
# ====================================================================

# ─────────────────────────────────────────────────────────
#  ZMIENNE
# ─────────────────────────────────────────────────────────

variable "REGISTRY" {
  default = ""
}

variable "TAG" {
  default = "latest"
}

# ─────────────────────────────────────────────────────────
#  FUNKCJE POMOCNICZE
# ─────────────────────────────────────────────────────────

function "image_tag" {
  params = [service]
  result = REGISTRY != "" ? "${REGISTRY}/viraloop-${service}:${TAG}" : "viraloop-${service}:${TAG}"
}

# ─────────────────────────────────────────────────────────
#  GRUPY
# ─────────────────────────────────────────────────────────

# Domyślna grupa — buduje wszystkie obrazy
group "default" {
  targets = ["backend", "celery-worker", "celery-beat", "flower", "frontend"]
}

# Tylko serwisy backendowe (Python/Celery)
group "backend-services" {
  targets = ["backend", "celery-worker", "celery-beat", "flower"]
}

# ─────────────────────────────────────────────────────────
#  WSPÓLNA BAZA — Python 3.11 + FastAPI
#  Wszystkie serwisy backendowe dziedziczą ten target
# ─────────────────────────────────────────────────────────

target "_backend-base" {
  context    = "./backend"
  dockerfile = "Dockerfile"
  args = {
    BUILDKIT_INLINE_CACHE = "1"
  }
  cache-to = ["type=inline"]
}

# ─────────────────────────────────────────────────────────
#  BACKEND — FastAPI (API serwer, port 8000)
# ─────────────────────────────────────────────────────────

target "backend" {
  inherits = ["_backend-base"]
  tags     = [image_tag("backend")]
}

# ─────────────────────────────────────────────────────────
#  CELERY WORKER — Generacja wideo w tle
# ─────────────────────────────────────────────────────────

target "celery-worker" {
  inherits = ["_backend-base"]
  tags     = [image_tag("celery-worker")]
}

# ─────────────────────────────────────────────────────────
#  CELERY BEAT — Harmonogram zadań
# ─────────────────────────────────────────────────────────

target "celery-beat" {
  inherits = ["_backend-base"]
  tags     = [image_tag("celery-beat")]
}

# ─────────────────────────────────────────────────────────
#  FLOWER — Monitoring Celery (port 5555)
# ─────────────────────────────────────────────────────────

target "flower" {
  inherits = ["_backend-base"]
  tags     = [image_tag("flower")]
}

# ─────────────────────────────────────────────────────────
#  FRONTEND — Next.js 15, tryb produkcyjny (port 3000)
# ─────────────────────────────────────────────────────────

target "frontend" {
  context    = "./frontend"
  dockerfile = "Dockerfile"
  args = {
    BUILDKIT_INLINE_CACHE = "1"
  }
  tags     = [image_tag("frontend")]
  cache-to = ["type=inline"]
}

# ─────────────────────────────────────────────────────────
#  FRONTEND-DEV — Next.js 15 + Turbopack (hot-reload)
# ─────────────────────────────────────────────────────────

target "frontend-dev" {
  context    = "./frontend"
  dockerfile = "Dockerfile.dev"
  tags       = [image_tag("frontend-dev")]
}
