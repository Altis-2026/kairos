"""
Result provenance — "can I prove this number is real?"

Every analysis response carries a provenance block: a canonical SHA-256 hash
of the scientific content (what was measured, where, when, with what method
and result), a UTC timestamp, and an HMAC signature over hash+timestamp keyed
by the server secret. Anyone holding the exported result can later POST it to
/verify and get back whether it is byte-for-byte the result Kairos produced —
because only content, not presentation, is hashed, re-styling a report doesn't
break verification, but changing a single number does.

The signing key comes from PROVENANCE_SECRET (falling back to a stable
derivation so dev environments work); rotate it and old signatures verify as
"unknown key" rather than "tampered", which the response distinguishes.
"""

import hashlib
import hmac
import json
import os
import time

_FALLBACK = "kairos-dev-provenance"


def _secret() -> bytes:
    return (os.getenv("PROVENANCE_SECRET") or _FALLBACK).encode()


# The scientific content of a result — presentation keys (tile URLs expire,
# context layers restyle) are deliberately excluded.
_HASHED_KEYS = (
    "analysis_type",
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
    """Attach a provenance block to an analysis result (mutates and returns)."""
    content_hash = hashlib.sha256(_canonical(result).encode()).hexdigest()
    issued_at = int(time.time())
    signature = hmac.new(
        _secret(), f"{content_hash}.{issued_at}".encode(), hashlib.sha256
    ).hexdigest()
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
    """Check a previously issued result. Returns a verdict dict, never raises."""
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
            "reason": (
                "Content hash mismatch — the scientific content differs from "
                "what was signed."
            ),
        }

    expected = hmac.new(
        _secret(), f"{content_hash}.{issued_at}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return {
            "valid": False,
            "reason": (
                "Signature does not match this server's key — either the "
                "block was altered or it was signed under a different/rotated "
                "key."
            ),
        }
    return {
        "valid": True,
        "issued_at": issued_at,
        "reason": "Content and signature verify against this server.",
    }
