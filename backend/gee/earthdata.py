"""
NASA Earthdata Login access — credential plumbing for future InSAR.

Kairos's current analyses all run on Google Earth Engine's public catalog and
need no Earthdata login. This module exists for the NEXT capability: pulling
Sentinel-1 SLC (single-look complex) scenes from the Alaska Satellite Facility
(ASF), which carry the interferometric PHASE that GRD amplitude does not. That
phase is what true InSAR deformation mapping (millimetre subsidence,
landslides, volcano inflation) requires.

Important scope note: an Earthdata token unlocks the DATA. Turning SLC pairs
into a displacement map still needs an interferometric processor (ESA SNAP or
ISCE) running on dedicated compute, which is a separate infrastructure build
(see docs/JANUS.md). This module only manages the credential so that work is
ready to plug in.

SECURITY: the token is read ONLY from the EARTHDATA_TOKEN environment variable.
It is never hardcoded, logged, or committed. Set it in your deployment secrets.
"""

import os

# ASF's Sentinel-1 SLC search/download API (used once the InSAR backend exists).
ASF_SEARCH_URL = "https://api.daac.asf.alaska.edu/services/search/param"


def earthdata_token() -> str | None:
    """The Earthdata bearer token from the environment, or None if unset."""
    token = os.getenv("EARTHDATA_TOKEN")
    return token.strip() if token else None


def is_configured() -> bool:
    return earthdata_token() is not None


def auth_header() -> dict:
    """Authorization header for ASF/Earthdata requests. Empty if unconfigured."""
    token = earthdata_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


def status() -> dict:
    """
    Non-sensitive status for a health/readiness check. Never returns the token
    itself — only whether one is present and (harmlessly) its length.
    """
    token = earthdata_token()
    return {
        "earthdata_configured": token is not None,
        "token_length": len(token) if token else 0,
        "purpose": "Sentinel-1 SLC access for future InSAR (ASF).",
        "note": (
            "Data access only. InSAR processing (SNAP/ISCE on dedicated "
            "compute) is a separate build."
        ),
    }
