import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.generation.model_assets import ModelSpec, fetch_model


def spec(tmp_path, content=b"synthetic gguf bytes"):
    document = {"model_id": "Qwen/fixture", "repository_revision": "a" * 40, "filename": "fixture.gguf", "model_sha256": sha256_bytes(content), "size_bytes": len(content), "alias": "fixture"}
    path = tmp_path / "model.json"
    path.write_bytes(canonical_json(document))
    return path, document


class Response(io.BytesIO):
    status = 200
    headers = {}


def test_partial_transfer_is_resumed_and_published_only_after_hash(tmp_path, monkeypatch):
    content = b"synthetic gguf bytes"
    path, document = spec(tmp_path, content)
    directory = tmp_path / "downloads/models" / document["repository_revision"]
    directory.mkdir(parents=True)
    (directory / "fixture.gguf.part").write_bytes(content[:5])
    def transfer(request, timeout):
        assert request.get_header("Range") == "bytes=5-"
        response = Response(content[5:]); response.status = 206; response.headers = {"Content-Range": f"bytes 5-{len(content)-1}/{len(content)}"}
        return response
    monkeypatch.setattr("urllib.request.urlopen", transfer)
    record = fetch_model(tmp_path, path, tmp_path / "receipt.json")
    assert (tmp_path / record["local_file"]).read_bytes() == content
    assert record["main_experiment_allowed"] is False
    assert not (directory / "fixture.gguf.part").exists()


def test_corrupt_transfer_never_publishes_a_model(tmp_path, monkeypatch):
    path, document = spec(tmp_path)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: Response(b"x" * document["size_bytes"]))
    with pytest.raises(ValueError, match="SHA-256"):
        fetch_model(tmp_path, path, tmp_path / "receipt.json")
    assert not (tmp_path / "receipt.json").exists()
    assert not list((tmp_path / "downloads").rglob("fixture.gguf"))


def test_relative_model_path_is_rejected():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ModelSpec(model_id="Qwen/fixture", repository_revision="a" * 40, filename="../escape.gguf", model_sha256="b" * 64, size_bytes=1, alias="fixture")
