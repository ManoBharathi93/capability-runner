"""Pure browser observation helpers. No browser handles or application vocabulary."""

from __future__ import annotations

import hashlib
import posixpath
import re
from urllib.parse import unquote, urlsplit

from capability_runner.contracts.browser_discovery import BrowserScope


def origin_of(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("HTTP/HTTPS application URL required")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Credentials and fragments are not allowed in application URLs")
    port = parsed.port
    suffix = f":{port}" if port and port != (443 if parsed.scheme == "https" else 80) else ""
    return f"{parsed.scheme}://{parsed.hostname.lower()}{suffix}"


def within_scope(url: str, scope: BrowserScope) -> bool:
    try:
        path = urlsplit(url).path or "/"
        for _ in range(3):
            decoded = unquote(path)
            if decoded == path:
                break
            path = decoded
        if "\\" in path or path.startswith("//"):
            return False
        path = posixpath.normpath(path)
        return origin_of(url) == scope.origin and any(
            path == prefix or path.startswith(prefix.rstrip("/") + "/")
            for prefix in scope.read_only_paths
        )
    except ValueError:
        return False


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def method_allowed(method: str, url: str, scope: BrowserScope) -> bool:
    return within_scope(url, scope) and (
        method == "GET" or (method == "POST" and urlsplit(url).path in scope.read_only_post_paths)
    )


def safe_slug(value: str) -> str:
    normalized = re.sub(r"[^a-z]+", "_", value.casefold()).strip("_")[:38].rstrip("_")
    return normalized or "element"
