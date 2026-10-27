"""Stable serialization and atomic, non-overwriting artifact publication."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def publish_artifact(path: Path, content: bytes) -> str:
    """Publish complete bytes atomically; an existing artifact is never overwritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError("An artifact with different content already exists")
        return sha256_bytes(content)
    fd, temporary = tempfile.mkstemp(prefix=".artifact-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o444)
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != content:
                raise FileExistsError("Concurrent publication with different content") from None
        directory_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return sha256_bytes(content)

