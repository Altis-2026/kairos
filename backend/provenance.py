import hashlib
import hmac
import json
import os
import time

_FALLBACK = "kairos-dev-provenance"


def _secret() -> bytes:
    return (os.getenv("PROVENANCE_SECRET") or _FALLBACK).encode()


_HASHED_KEYS = (
    "analysis_type",
    "mode",
    "bbox",
    "start_date",
    "end_date",
    "data_date",
    "confidence",
    "headline_stat",
    "stats",
)


def _canonical(result: dict) -> str:
    core = {k: result.get(k) for k in _HASHED_KEYS if k in result}
    return json.dumps(core, sort_keys=True, separators=(",", ":"))


def stamp(result: dict) -> dict:
    content_hash = hashlib.sha256(_canonical(result).encode()).hexdigest()
    issued_at = int(time.time())
    signature = hmac.new(_secret(), f"{content_hash}.{issued_at}".encode(), hashlib.sha256).hexdigest()
    result["provenance"] = {
        "content_hash": content_hash,
        "issued_at": issued_at,
        "signature": signature,
        "note": (
            "SHA-256 over the scientific content (method, area, dates, "
            "results), HMAC-signed by Kairos at issue time. POST the full "
            "result to /verify to check integrity."
        ),
    }
    return result


def verify(result: dict) -> dict:
    prov = result.get("provenance") or {}
    content_hash = prov.get("content_hash")
    issued_at = prov.get("issued_at")
    signature = prov.get("signature")
    if not (content_hash and issued_at and signature):
        return {"valid": False, "reason": "No provenance block present."}

    recomputed = hashlib.sha256(_canonical(result).encode()).hexdigest()
    if recomputed != content_hash:
        return {
            "valid": False,
            "reason": ("Content hash mismatch. The scientific content differs from what was signed."),
        }

    expected = hmac.new(_secret(), f"{content_hash}.{issued_at}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return {
            "valid": False,
            "reason": (
                "Signature does not match this server's key, either the "
                "block was altered or it was signed under a different/rotated "
                "key."
            ),
        }
    return {
        "valid": True,
        "issued_at": issued_at,
        "reason": "Content and signature verify against this server.",
    }
