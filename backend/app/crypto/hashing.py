from __future__ import annotations

import hashlib


def sha256_hash(data: str | bytes | dict) -> str:
    if isinstance(data, dict):
        import json
        data = json.dumps(data, sort_keys=True)
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha256_file(filepath: str, chunk_size: int = 8192) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
