"""Revision-pinned model assets with bounded, verified, resumable downloads."""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path

from pydantic import Field, field_validator

from ..artifacts import canonical_json, publish_artifact, sha256_bytes
from ..config import StrictModel


class ModelSpec(StrictModel):
    model_id: str = Field(pattern=r"^[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+$")
    repository_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    filename: str = Field(pattern=r"^[A-Za-z0-9_.-]+\.gguf$")
    model_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)
    quantization_declared: str = "Q4_K_M"
    alias: str = Field(pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("filename")
    @classmethod
    def plain_filename(cls, value):
        if value.startswith("."):
            raise ValueError("Hidden or relative model paths are not allowed")
        return value


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_model(root: Path, specification: Path, receipt: Path, *, progress=print) -> dict:
    spec = ModelSpec.model_validate_json(specification.read_bytes())
    directory = root / "downloads/models" / spec.repository_revision
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / spec.filename
    url = f"https://huggingface.co/{spec.model_id}/resolve/{spec.repository_revision}/{spec.filename}?download=true"
    if not destination.exists():
        partial = directory / (spec.filename + ".part")
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > spec.size_bytes:
            raise ValueError("Partial model exceeds its pinned expected size")
        if offset < spec.size_bytes:
            headers = {"User-Agent": "curl/8.5.0", "Cache-Control": "no-cache"}
            if offset:
                headers["Range"] = f"bytes={offset}-"
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
                append = offset > 0 and response.status == 206 and response.headers.get("Content-Range", "").startswith(f"bytes {offset}-")
                written = offset if append else 0
                checkpoint = written
                with partial.open("ab" if append else "wb") as handle:
                    while chunk := response.read(8 * 1024 * 1024):
                        if written + len(chunk) > spec.size_bytes:
                            raise ValueError("Model transfer exceeds its pinned expected size")
                        handle.write(chunk)
                        written += len(chunk)
                        if written - checkpoint >= 256 * 1024 * 1024:
                            progress(json.dumps({"downloaded_mib": round(written / 2**20), "expected_mib": round(spec.size_bytes / 2**20)}))
                            checkpoint = written
                    handle.flush()
                    os.fsync(handle.fileno())
        if partial.stat().st_size != spec.size_bytes or file_sha256(partial) != spec.model_sha256:
            raise ValueError("Model bytes do not match the pinned size/SHA-256; no model was published")
        partial.chmod(0o444)
        os.link(partial, destination)
        partial.unlink()
    if destination.stat().st_size != spec.size_bytes or file_sha256(destination) != spec.model_sha256:
        raise ValueError("Existing model bytes differ from the pinned specification")
    record = {**spec.model_dump(), "status": "download_verified", "source_url": url,
              "local_file": str(destination.relative_to(root)), "specification_sha256": sha256_bytes(specification.read_bytes()),
              "main_experiment_allowed": False}
    publish_artifact(receipt, canonical_json(record))
    return record
