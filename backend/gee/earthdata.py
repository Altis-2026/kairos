import os

ASF_SEARCH_URL = "https://api.daac.asf.alaska.edu/services/search/param"


def earthdata_token() -> str | None:
    token = os.getenv("EARTHDATA_TOKEN")
    return token.strip() if token else None


def is_configured() -> bool:
    return earthdata_token() is not None


def auth_header() -> dict:
    token = earthdata_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


def status() -> dict:
    token = earthdata_token()
    return {
        "earthdata_configured": token is not None,
        "token_length": len(token) if token else 0,
        "purpose": "Sentinel-1 SLC access for future InSAR (ASF).",
        "note": ("Data access only. InSAR processing (SNAP/ISCE on dedicated compute) is a separate build."),
    }
