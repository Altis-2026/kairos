import threading

ready = threading.Event()
error: str | None = None

DEFAULT_TIMEOUT_S = 25.0


def wait(timeout: float = DEFAULT_TIMEOUT_S) -> None:
    if not ready.wait(timeout):
        raise RuntimeError(
            "Kairos is still starting up (Earth Engine is initializing), please try again in a few seconds."
        )
    if error:
        raise RuntimeError(f"Earth Engine failed to initialize: {error}")
