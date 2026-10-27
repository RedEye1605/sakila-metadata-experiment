"""Read and recheck evidence against the actual local llama-server instance."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import httpx

from ..artifacts import canonical_json, sha256_bytes
from ..config import InferenceConfig
from .llama import BackendEvidence, LLMServiceError


def load_backend_evidence(path: Path) -> tuple[BackendEvidence, dict]:
    content = path.read_bytes()
    record = json.loads(content)
    if record.get("status") != "runtime_verified" or record.get("quantization_runtime") != "Q4_K - Medium":
        raise LLMServiceError("backend_verification_record_invalid")
    if not record.get("container_name") or not record.get("command") or not record.get("model_mount_source"):
        raise LLMServiceError("backend_deployment_evidence_missing_reverify_with_parameterized_cli")
    return BackendEvidence(record["model_id"], record["model_sha256"], record["backend_revision"],
                           record["effective_context_tokens"], sha256_bytes(content)), record


def check_live_backend(settings: InferenceConfig, record: dict) -> None:
    try:
        process = subprocess.run(["docker", "inspect", record["container_name"]], capture_output=True, text=True, timeout=10, check=True)
        container = json.loads(process.stdout)[0]
        mounts = [m for m in container["Mounts"] if m["Destination"] == "/models"]
        if (not container["State"]["Running"] or container["Image"] != record["container_image_id"]
                or container["Config"]["Cmd"] != record["command"]
                or container["HostConfig"]["Memory"] != record["host_memory_limit_bytes"]
                or len(mounts) != 1 or mounts[0]["RW"] or mounts[0]["Source"] != record["model_mount_source"]):
            raise LLMServiceError("live_backend_deployment_differs_from_verification")
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError, TypeError):
        raise LLMServiceError("backend_deployment_preflight_unavailable") from None
    try:
        with httpx.Client(timeout=10, trust_env=False) as client:
            response = client.get(settings.base_url + "/props")
            response.raise_for_status()
            props = response.json()
    except (httpx.HTTPError, ValueError):
        raise LLMServiceError("backend_preflight_unavailable") from None
    if (props.get("model_alias") != record["model_id"]
            or props.get("build_info") != record["build_info"]
            or props.get("model_ftype") != record["quantization_runtime"]
            or props.get("total_slots") != 1
            or props.get("default_generation_settings", {}).get("n_ctx") != record["effective_context_tokens"]
            or sha256_bytes(props.get("chat_template", "").encode()) != record["chat_template_sha256"]):
        raise LLMServiceError("live_backend_differs_from_verification")
