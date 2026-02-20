"""
NEXUS — WebSocket: Live Progress
==================================
Real-time śledzenie postępu generacji wideo przez WebSocket.

Protokół:
1. Client łączy się: ws://localhost/ws/wideo/{sesja_id}
2. Serwer subskrybuje kanał Redis: nexus:progress:{sesja_id}
3. Każde zdarzenie postępu → przesłane do klienta
4. Połączenie trwa do zakończenia generacji lub timeout

Wiadomości JSON:
{
    "sesja_id": "abc123",
    "krok": "pisarz_scenariuszy",
    "procent": 30,
    "wiadomosc": "Pisarz Scenariuszy tworzy scenariusz...",
    "timestamp": 1234567890.123
}
"""

import json
import asyncio
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from konfiguracja import konf

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/wideo/{sesja_id}")
async def websocket_postep(websocket: WebSocket, sesja_id: str):
    """
    WebSocket endpoint dla live tracking postępu generacji wideo.

    Subskrybuje kanał Redis i przesyła zdarzenia postępu do klienta.
    Timeout: 600 sekund (10 minut na generację).
    """
    await websocket.accept()
    log = logger.bind(sesja_id=sesja_id, endpoint="ws_postep")
    log.info("WebSocket połączony")

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(konf.REDIS_URL, decode_responses=True)

        # Sprawdź czy jest już zapisany stan
        stan_zapisany = await r.get(f"nexus:stan:{sesja_id}")
        if stan_zapisany:
            await websocket.send_text(stan_zapisany)

        # Subskrybuj kanał postępu
        pubsub = r.pubsub()
        await pubsub.subscribe(f"nexus:progress:{sesja_id}")

        # Wyślij potwierdzenie połączenia
        await websocket.send_text(json.dumps({
            "typ": "polaczony",
            "sesja_id": sesja_id,
            "wiadomosc": "Połączono z pipeline'em NEXUS",
        }))

        try:
            # Nasłuchuj przez max 600s
            timeout = 600
            czas_start = asyncio.get_event_loop().time()

            while (asyncio.get_event_loop().time() - czas_start) < timeout:
                try:
                    wiadomosc = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    # Ping co 30s
                    czas_aktualny = asyncio.get_event_loop().time()
                    if (czas_aktualny - czas_start) % 30 < 1:
                        try:
                            await websocket.send_text(json.dumps({"typ": "ping"}))
                        except Exception:
                            break
                    continue

                if wiadomosc and wiadomosc.get("type") == "message":
                    dane = wiadomosc.get("data", "")
                    await websocket.send_text(dane)

                    # Zakończ po dotarciu do 100%
                    try:
                        parsowane = json.loads(dane)
                        if parsowane.get("procent", 0) >= 100 or parsowane.get("krok") in ["gotowe", "blad", "blad_krytyczny"]:
                            log.info("Pipeline zakończony — zamykam WebSocket")
                            await asyncio.sleep(0.5)
                            break
                    except json.JSONDecodeError:
                        pass

        finally:
            await pubsub.unsubscribe(f"nexus:progress:{sesja_id}")
            await pubsub.close()
            await r.aclose()

        await websocket.send_text(json.dumps({
            "typ": "rozlaczony",
            "sesja_id": sesja_id,
            "wiadomosc": "Pipeline zakończony",
        }))

    except WebSocketDisconnect:
        log.info("WebSocket rozłączony przez klienta")
    except Exception as e:
        log.error("Błąd WebSocket", blad=str(e))
        try:
            await websocket.send_text(json.dumps({
                "typ": "blad",
                "wiadomosc": f"Błąd serwera: {str(e)}",
            }))
        except Exception:
            pass
    finally:
        log.info("WebSocket zamknięty")


@router.websocket("/ws/zdrowie")
async def websocket_zdrowie(websocket: WebSocket):
    """Testowy WebSocket — sprawdza czy WebSocket działa."""
    await websocket.accept()
    await websocket.send_text(json.dumps({"status": "ok", "platforma": "NEXUS"}))
    await websocket.close()
