# ====================================================================
# NEXUS Backend — Dockerfile Multi-Stage
# Python 3.11 + FastAPI + FFmpeg
# ====================================================================

# --- Etap 1: Builder ---
FROM python:3.11-slim AS builder

WORKDIR /build

# Zależności systemowe
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Skopiuj requirements i zainstaluj
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Etap 2: Runtime ---
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Skopiuj zainstalowane pakiety z buildera
COPY --from=builder /install /usr/local

# Utwórz niepriwilejowanego użytkownika
RUN useradd -m -u 1000 nexus && \
    mkdir -p /app/dane/wideo /app/dane/chroma /tmp/nexus && \
    chown -R nexus:nexus /app /tmp/nexus

# Skopiuj kod aplikacji
COPY --chown=nexus:nexus . .

USER nexus

EXPOSE 8000

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/zdrowie || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
