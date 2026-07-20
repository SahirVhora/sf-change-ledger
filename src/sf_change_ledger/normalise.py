from __future__ import annotations

from typing import Any

NOISE_KEYS = {
    "__metadata",
    "lastModifiedDateTime",
    "lastModifiedOn",
    "createdDateTime",
    "createdOn",
    "mdfSystemCreatedDate",
    "mdfSystemLastModifiedDate",
}


def normalise_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): normalise_value(val)
            for key, val in sorted(value.items())
            if key not in NOISE_KEYS and val not in ("", None, [], {})
        }
    if isinstance(value, list):
        return sorted((normalise_value(item) for item in value), key=repr)
    if isinstance(value, str):
        stripped = value.strip()
        lowered = stripped.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered in {"none", "null"}:
            return None
        return stripped
    return value


def flatten_properties(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        return {prefix: value}

    flattened: dict[str, Any] = {}
    for key, item in sorted(value.items()):
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(item, dict):
            flattened.update(flatten_properties(item, path))
        else:
            flattened[path] = item
    return flattened
