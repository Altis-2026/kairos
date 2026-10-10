import ipaddress
import json
import socket
import urllib.parse
import urllib.request

_TIMEOUT_S = 6


def validate_webhook_url(url: str) -> str:
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
                raise ValueError("Webhook host resolves to a private/loopback address, which is not allowed.")
    except socket.gaierror:
        raise ValueError("Webhook host does not resolve.")
    return url


def post_event(url: str, event: dict) -> bool:
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
    from janus import store

    url = store.get_webhook(owner)
    if not url:
        return False
    return post_event(url, event)
