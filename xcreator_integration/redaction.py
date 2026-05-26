"""Redaction helpers for XCreator integration diagnostics."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


SENSITIVE_KEY_RE = re.compile(
    r"(?:^|_|\b)(?:cwusertoken|cwapptoken|token|session|authorization|cookie|password|secret|auth)(?:$|_|\b)",
    re.IGNORECASE,
)
SENSITIVE_QUERY_RE = re.compile(
    r"([?&](?:cwUserToken|cwAppToken|userToken|token|session|sid|auth|authorization)=)([^&#]*)",
    re.IGNORECASE,
)


def redact(value: Any) -> Any:
    """Return a copy of *value* with tokens and raw auth data removed."""

    if isinstance(value, Mapping):
        return {
            key: "[REDACTED]" if _is_sensitive_key(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.replace("-", "_").replace(".", "_")
    return bool(SENSITIVE_KEY_RE.search(normalized))


def _redact_string(value: str) -> str:
    cleaned = SENSITIVE_QUERY_RE.sub(lambda match: f"{match.group(1)}[REDACTED]", value)
    cleaned = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(sid|sessionid)=([^;\s]+)", r"\1=[REDACTED]", cleaned, flags=re.IGNORECASE)
    return cleaned

