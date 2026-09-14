"""Pure browser observation helpers. No browser handles or application vocabulary."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from urllib.parse import unquote, urlsplit

from capability_runner.contracts.browser_discovery import (
    BrowserObservation,
    BrowserScope,
    InteractiveElement,
    ObservationDelta,
)

OBSERVATION_LIMITS = {
    "max_elements": 64,
    "max_headings": 8,
    "max_frames": 4,
    "max_nearby_characters": 200,
    "max_text_characters": 8192,
    "max_serialized_bytes": 65536,
    "max_model_characters": 16000,
}


def _stable_text(text: str) -> str:
    # Ignore recognizable clocks/UUIDs, not member IDs or monetary amounts.
    text = re.sub(r"\b\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:\.\d+)?Z?\b", "<time>", text)
    text = re.sub(r"\b\d\d:\d\d(?::\d\d)?\b", "<time>", text)
    return re.sub(r"\b[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}\b", "<id>", text)


def _element_state(element: InteractiveElement) -> tuple[object, ...]:
    return (
        element.role,
        _stable_text(element.accessible_name),
        _stable_text(element.label),
        element.enabled,
        element.current_value_state,
        _stable_text(element.text),
        _stable_text(element.nearby_text_summary),
        _stable_text(element.structural_context),
    )


def _element_states(observation: BrowserObservation) -> dict[str, tuple[object, ...]]:
    return {
        f"{element.frame_identity}:{element.structural_fingerprint}": _element_state(element)
        for element in observation.elements
    }


def normalized_fingerprint(observation: BrowserObservation) -> str:
    return fingerprint(
        json.dumps(
            [
                observation.origin,
                observation.path,
                _stable_text(observation.title),
                [_stable_text(item) for item in observation.headings],
                _element_states(observation),
            ],
            sort_keys=True,
            ensure_ascii=True,
        )
    )


def observation_delta(
    previous: BrowserObservation, current: BrowserObservation
) -> ObservationDelta:
    before, after = _element_states(previous), _element_states(current)
    heading_change = tuple(map(_stable_text, previous.headings)) != tuple(
        map(_stable_text, current.headings)
    )
    text_change = _stable_text(previous.visible_text_summary) != _stable_text(
        current.visible_text_summary
    )
    page_change = (previous.page_identity, previous.origin, previous.path) != (
        current.page_identity,
        current.origin,
        current.path,
    )
    added, removed = len(after.keys() - before.keys()), len(before.keys() - after.keys())
    changed = sum(before[key] != after[key] for key in before.keys() & after.keys())
    return ObservationDelta(
        previous_generation=previous.generation,
        current_generation=current.generation,
        added_count=added,
        removed_count=removed,
        changed_count=changed,
        headings_changed=heading_change,
        meaningful_text_changed=text_change,
        page_identity_changed=page_change,
        meaningful_change=bool(
            added or removed or changed or heading_change or text_change or page_change
        ),
    )


def bound_observation(observation: BrowserObservation) -> BrowserObservation:
    remaining = OBSERVATION_LIMITS["max_text_characters"]
    truncated = observation.truncated

    def bounded(text: str) -> str:
        nonlocal remaining, truncated
        result = text[:remaining]
        remaining -= len(result)
        truncated |= result != text
        return result

    title = bounded(observation.title)
    headings = tuple(bounded(item) for item in observation.headings)
    elements = [
        element.model_copy(
            update={
                key: bounded(getattr(element, key))
                for key in (
                    "accessible_name",
                    "label",
                    "text",
                    "nearby_text_summary",
                    "structural_context",
                )
            }
        )
        for element in observation.elements
    ]
    summary_text = " | ".join([*headings, *(item.text for item in elements if item.text)])
    truncated |= len(summary_text) > 512
    summary = bounded(summary_text[:512])
    result = observation.model_copy(
        update={
            "title": title,
            "headings": headings,
            "elements": tuple(elements),
            "visible_text_summary": summary,
            "observation_limits": dict(OBSERVATION_LIMITS),
            "truncated": truncated,
        }
    )
    # Reserve room for the fingerprint and bounded delta added after distillation.
    while (
        len(result.model_dump_json().encode("utf-8"))
        > OBSERVATION_LIMITS["max_serialized_bytes"] - 1024
    ):
        elements.pop()
        result = result.model_copy(update={"elements": tuple(elements), "truncated": True})
    return result.model_copy(update={"observation_fingerprint": normalized_fingerprint(result)})


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
