from __future__ import annotations

import hashlib
import json
import re


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(*parts: object) -> str:
    return digest(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode())[:32]


def terms(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", text.lower(), re.UNICODE)


def slug(text: str) -> str:
    return "-".join(terms(text))


def exact_slice(data: bytes, start: int, end: int) -> str:
    if not 0 <= start <= end <= len(data):
        raise ValueError("range outside source bytes")
    if start < len(data) and data[start] & 0xC0 == 0x80:
        raise ValueError("range start splits a UTF-8 code point")
    return data[start:end].decode("utf-8")
