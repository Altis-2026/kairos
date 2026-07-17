"""
Outbound alerting — push watch findings to the user's own systems.

A user registers one webhook URL; every proactive-watch insight for their
projects is POSTed to it. Slack incoming webhooks are auto-detected (payload
becomes {"text": ...} as Slack requires); anything else receives the full
JSON event, so Discord relays, n8n/Zapier flows, and custom services all work
from the same field.

Fire-and-forget with a short timeout: an unreachable webhook must never slow
or break the watch cycle that triggered it. Failures are swallowed by design;
the /alerts/webhook/test endpoint exists precisely so users can prove their
URL works before trusting it.

Guardrail: only http(s) URLs are accepted, and localhost/private-network
targets are rejected at registration time to keep the server from being used
to probe its own network (basic SSRF hygiene).
"""

import ipaddress
import json
import socket
import urllib.parse
import urllib.request

_TIMEOUT_S = 6


def validate_webhook_url(url: str) -> str:
    """Return the URL if acceptable; raise ValueError with a reason if not."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Webhook must be an http(s) URL.")
    host = parsed.hostname or ""
    if not host:
        raise ValueError("Webhook URL has no host.")
    try:
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                raise ValueError(
                    "Webhook host resolves to a private/loopback address, "
                    "which is not allowed."
                )
    except socket.gaierror:
        raise ValueError("Webhook host does not resolve.")
    return url


def post_event(url: str, event: dict) -> bool:
    """POST one event. Returns success; never raises."""
    try:
        if "hooks.slack.com" in url:
            lines = [f"*{event.get('title', 'Kairos alert')}*"]
            if event.get("summary"):
                lines.append(event["summary"])
            if event.get("link"):
                lines.append(event["link"])
            body = {"text": "\n".join(lines)}
        else:
            body = {"source": "kairos", **event}
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def notify_owner(owner: str, event: dict) -> bool:
    """Look up the owner's webhook and post; False when none registered."""
    from janus import store

    url = store.get_webhook(owner)
    if not url:
        return False
    return post_event(url, event)
