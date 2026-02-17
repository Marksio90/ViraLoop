"""Eksportuje wszystkie routery API ViraLoop."""

from backend.api.routes.wideo import router as router_wideo
from backend.api.routes.audio import router as router_audio
from backend.api.routes.analityka import router as router_analityka
from backend.api.routes.projekty import router as router_projekty
from backend.api.routes.uzytkownik import router as router_uzytkownik
from backend.api.routes.zgodnosc import router as router_zgodnosc

__all__ = [
    "router_wideo",
    "router_audio",
    "router_analityka",
    "router_projekty",
    "router_uzytkownik",
    "router_zgodnosc",
]
