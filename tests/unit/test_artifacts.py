import pytest

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes


def test_canonical_content_is_order_independent_and_rejects_nan():
    assert canonical_json({"b": 2, "a": "Indonesia"}) == canonical_json({"a": "Indonesia", "b": 2})
    with pytest.raises(ValueError):
        canonical_json({"value": float("nan")})


def test_publication_never_overwrites_a_different_artifact(tmp_path):
    path = tmp_path / "artifact.json"
    first = b'{"first":true}\n'
    assert publish_artifact(path, first) == sha256_bytes(first)
    assert publish_artifact(path, first) == sha256_bytes(first)
    with pytest.raises(FileExistsError):
        publish_artifact(path, b'{"different":true}\n')
    assert path.read_bytes() == first

