import json
from types import SimpleNamespace

import httpx
import pytest

from sakila_experiment.artifacts import sha256_bytes
from sakila_experiment.config import InferenceConfig
from sakila_experiment.generation import backend
from sakila_experiment.generation.llama import LLMServiceError


def test_changed_gpu_offload_is_rejected_despite_identical_props(monkeypatch):
    record = {"container_name": "fixture", "container_image_id": "fixture-image", "command": ["--n-gpu-layers", "24"], "host_memory_limit_bytes": 7 * 2**30,
              "model_mount_source": "/fixture/models", "model_id": "fixture", "build_info": "fixture", "quantization_runtime": "Q4_K - Medium", "effective_context_tokens": 16384, "chat_template_sha256": sha256_bytes(b"template")}
    container = {"State": {"Running": True}, "Image": "fixture-image", "Config": {"Cmd": ["--n-gpu-layers", "20"]},
                 "HostConfig": {"Memory": 7 * 2**30}, "Mounts": [{"Destination": "/models", "RW": False, "Source": "/fixture/models"}]}
    monkeypatch.setattr(backend.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=json.dumps([container])))
    monkeypatch.setattr(backend.httpx, "Client", lambda *a, **k: pytest.fail("Changed deployment must stop before endpoint checks"))
    with pytest.raises(LLMServiceError, match="deployment_differs"):
        backend.check_live_backend(InferenceConfig(model_id="fixture"), record)
