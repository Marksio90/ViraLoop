"""
NEXUS — Celery: Asynchroniczne Kolejkowanie Zadań
==================================================
Celery + Redis = Nieblokująca generacja wideo.

Endpoint /generuj zwraca task_id natychmiast → Celery generuje w tle
→ Frontend polluje status LUB łączy się WebSocket dla live updates.

Konfiguracja:
- Broker: Redis (kolejka zadań)
- Backend: Redis (wyniki)
- Concurrency: 2 workerów (optymalne dla laptopa)
- Task timeout: 600s (dla długich generacji)
"""

from celery import Celery
from konfiguracja import konf

# Konfiguracja Celery
celery_app = Celery(
    "nexus",
    broker=konf.REDIS_URL,
    backend=konf.REDIS_URL,
    include=["zadania.generacja"],
)

# Konfiguracja zaawansowana
celery_app.conf.update(
    # ─── Serializacja ─────────────────────────────────────────
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Warsaw",
    enable_utc=True,

    # ─── Wydajność na laptopie ────────────────────────────────
    worker_concurrency=2,               # 2 zadania równolegle
    worker_prefetch_multiplier=1,       # 1 zadanie na workera (bez przedwczesnego pobierania)
    task_acks_late=True,                # ACK po wykonaniu (nie po otrzymaniu)
    task_reject_on_worker_lost=True,    # Ponów gdy worker padnie

    # ─── Timeouty ────────────────────────────────────────────
    task_soft_time_limit=480,           # Soft limit: 8 min (generacja + DALL-E)
    task_time_limit=600,                # Hard limit: 10 min
    result_expires=86400,               # Wyniki ważne 24h

    # ─── Retry policy ────────────────────────────────────────
    task_max_retries=3,
    task_default_retry_delay=30,        # 30s przerwa między próbami

    # ─── Routing zadań ───────────────────────────────────────
    task_routes={
        "zadania.generacja.generuj_wideo_task": {"queue": "wideo"},
        "zadania.generacja.analizuj_wiralnosc_task": {"queue": "analityka"},
    },

    # ─── Kolejki ─────────────────────────────────────────────
    task_queues={
        "wideo": {
            "exchange": "wideo",
            "routing_key": "wideo",
            "queue_arguments": {"x-max-priority": 10},
        },
        "analityka": {
            "exchange": "analityka",
            "routing_key": "analityka",
        },
    },
    task_default_queue="wideo",

    # ─── Monitoring ──────────────────────────────────────────
    worker_send_task_events=True,
    task_send_sent_event=True,

    # ─── Redis ───────────────────────────────────────────────
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 3600,
        "max_retries": 3,
    },
)

# Import zadań
celery_app.autodiscover_tasks(["zadania"])
