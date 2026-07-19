"""
Earth Engine readiness gate.

ee.Initialize() is a network call to Google's servers — on a cold Cloud Run
start it can take several seconds. If it blocks the FastAPI lifespan (the old
behavior), the WHOLE app refuses to answer any request, including /health,
until it finishes. main.py now runs it in a background thread instead and
opens the port immediately; this module is the shared handshake so any code
path that actually touches Earth Engine can wait for it specifically,
without holding up unrelated routes.

No FastAPI/ee imports here on purpose — kept dependency-free so both main.py
and gee/common.py can import it without any circularity risk.
"""

import threading

ready = threading.Event()
error: str | None = None

# Generous but bounded: a real GEE outage should surface as an error, not an
# indefinite hang.
DEFAULT_TIMEOUT_S = 25.0


def wait(timeout: float = DEFAULT_TIMEOUT_S) -> None:
    """
    Block the calling thread until Earth Engine finishes initializing.
    Cheap no-op after the first cold start (the Event is already set).
    """
    if not ready.wait(timeout):
        raise RuntimeError(
            "Kairos is still starting up (Earth Engine is initializing) — "
            "please try again in a few seconds."
        )
    if error:
        raise RuntimeError(f"Earth Engine failed to initialize: {error}")
