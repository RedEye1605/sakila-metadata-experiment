"""Verify selected backend/model and full pilot budgets, without generation."""

from __future__ import annotations

import json
import re
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ..artifacts import canonical_json, publish_artifact, sha256_bytes
from ..config import AppConfig
from ..contracts import load_questions
from ..metadata.snapshots import validate_scenario_set
from .llama import BackendEvidence, LlamaClient, LLMServiceError
from .model_assets import file_sha256
from .prompt import build_prompt


def verify_backend(config: AppConfig, model_receipt: Path, compose_file: Path, container_name: str,
                   snapshots: Path, output: Path, *, context_questions: Path | None = None) -> dict:
    if (output / "verification.json").exists():
        raise ValueError("Backend verification exists; choose a new output directory")
    candidate = json.loads(model_receipt.read_bytes())
    if candidate.get("status") != "download_verified":
        raise ValueError("Verified model download receipt is required")
    model_path = (config.project_root / candidate["local_file"]).resolve()
    if not model_path.is_relative_to(config.project_root.resolve()) or file_sha256(model_path) != candidate["model_sha256"]:
        raise ValueError("Local model bytes/path differ from the verified receipt")
    def docker(*arguments):
        return json.loads(subprocess.run(["docker", *arguments], check=True, capture_output=True, text=True).stdout)
    container = docker("inspect", container_name)[0]
    image = docker("image", "inspect", container["Image"])[0]
    command = container["Config"]["Cmd"]
    def option(name):
        try:
            return command[command.index(name) + 1]
        except (ValueError, IndexError):
            raise ValueError("Missing required fixed backend option: " + name) from None
    if not container["State"]["Running"] or "@sha256:" not in container["Config"]["Image"]:
        raise ValueError("A running digest-pinned inference container is required")
    if any(flag not in command for flag in ("--no-cache-prompt", "--no-context-shift", "--no-cont-batching")):
        raise ValueError("Required request-isolation settings are missing")
    if (option("--fit") != "off" or option("--cache-ram") != "0" or option("--parallel") != "1"
            or int(option("--ctx-size")) != config.inference.context_tokens
            or option("--alias") != config.inference.model_id
            or option("--model") != "/models/" + candidate["filename"]):
        raise ValueError("Actual execution options differ from the selected experiment settings")
    mount = [m for m in container["Mounts"] if m["Destination"] == "/models"]
    if len(mount) != 1 or mount[0]["RW"] or Path(mount[0]["Source"]).resolve() != model_path.parent:
        raise ValueError("The selected model is not mounted read-only from the verified directory")
    labels = image["Config"].get("Labels", {})
    revision = labels.get("org.opencontainers.image.revision", "")
    build = labels.get("org.opencontainers.image.version", "")
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or not build:
        raise ValueError("Image source revision/build labels are incomplete")
    documents = {}
    try:
        with httpx.Client(timeout=15, trust_env=False) as client:
            for endpoint in ("/health", "/v1/models", "/props", "/slots"):
                response = client.get(config.inference.base_url + endpoint)
                response.raise_for_status()
                documents[endpoint] = response.json()
    except (httpx.HTTPError, ValueError):
        raise LLMServiceError("backend_verification_endpoint_unavailable") from None
    props = documents["/props"]
    if (props.get("total_slots") != 1 or props.get("model_alias") != config.inference.model_id
            or props.get("default_generation_settings", {}).get("n_ctx") != config.inference.context_tokens
            or props.get("model_ftype") != "Q4_K - Medium"
            or props.get("build_info") != build + "-" + revision[:9]
            or config.inference.model_id not in {m["id"] for m in documents["/v1/models"]["data"]}):
        raise ValueError("Observed backend/model response differs from the verified deployment")
    validate_scenario_set(snapshots)
    record = {"status": "runtime_verified", "verified_at_utc": datetime.now(timezone.utc).isoformat(),
              "model_id": config.inference.model_id, "model_repository": candidate["model_id"],
              "model_repository_revision": candidate["repository_revision"], "model_file": candidate["local_file"],
              "model_sha256": candidate["model_sha256"], "quantization_runtime": props["model_ftype"],
              "backend_revision": revision, "build_info": props["build_info"], "effective_context_tokens": config.inference.context_tokens,
              "chat_template_sha256": sha256_bytes(props["chat_template"].encode()), "container_image_id": container["Image"],
              "container_image_reference": container["Config"]["Image"], "command": command,
              "container_name": container_name, "host_memory_limit_bytes": container["HostConfig"]["Memory"], "model_mount_source": mount[0]["Source"],
              "compose_sha256": sha256_bytes(compose_file.read_bytes()), "model_receipt_sha256": sha256_bytes(model_receipt.read_bytes()),
              "runtime_documents": documents, "main_experiment_allowed": False, "generation_requests": 0,
              "gpu_layers": int(option("--n-gpu-layers")), "threads": int(option("--threads")),
              "batch_size": int(option("--batch-size")), "ubatch_size": int(option("--ubatch-size"))}
    evidence = BackendEvidence(config.inference.model_id, candidate["model_sha256"], revision,
                               config.inference.context_tokens, sha256_bytes(canonical_json(record)))
    budgets = []
    questions_path = context_questions or config.project_root / "data/pilot/questions.jsonl"
    if config.diagnostic_manifest and context_questions is None:
        from ..experiment.diagnostics import DiagnosticManifest
        selected = DiagnosticManifest.model_validate_json(config.resolve(config.diagnostic_manifest).read_bytes())
        questions_path = selected.questions.verified_path(config.project_root)
    with LlamaClient(config.inference, evidence) as client:
        for question in load_questions(questions_path):
            for scenario in ("S0", "S1", "S2", "S3"):
                folder = snapshots / scenario
                manifest = json.loads((folder / "manifest.json").read_bytes())
                prompt = build_prompt(question.generation_input(), json.loads((folder / manifest["payload_file"]).read_bytes()),
                                      manifest["snapshot_sha256"], config.resolve(config.prompt_template))
                checked = client.prepare(prompt)
                budgets.append({"question_id": question.question_id, "scenario_id": scenario, "input_tokens": checked.input_tokens,
                                "output_reserve": config.inference.max_output_tokens, "safety_margin": config.inference.safety_margin_tokens,
                                "prompt_sha256": prompt.prompt_sha256})
    record["pilot_context_checks"] = budgets
    record["context_questions_sha256"] = sha256_bytes(questions_path.read_bytes())
    record["resource_observations"] = {
        "gpu": subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,temperature.gpu", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip(),
        "memory_kib": {key: int(value.split()[0]) for line in Path("/proc/meminfo").read_text().splitlines()
                       for key, value in [line.split(":", 1)] if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}}}
    publish_artifact(output / "chat-template.jinja", props["chat_template"].encode())
    publish_artifact(output / "verification.json", canonical_json(record))
    return {"status": record["status"], "model_id": config.inference.model_id, "pilot_prompts_checked": len(budgets),
            "maximum_input_tokens": max(b["input_tokens"] for b in budgets), "generation_requests": 0, "main_experiment_allowed": False}


def verify_sampler(config: AppConfig, backend_path: Path, pilot_directory: Path, output: Path) -> dict:
    from ..analysis.report import audit_run
    from .backend import check_live_backend, load_backend_evidence
    evidence, backend = load_backend_evidence(backend_path)
    check_live_backend(config.inference, backend)
    manifest, records = audit_run(pilot_directory)
    if (manifest["inference_config"] != config.inference.model_dump(mode="json")
            or manifest["backend_evidence_sha256"] != evidence.verification_artifact_sha256):
        raise ValueError("Pilot and selected backend/settings differ")
    last = max(records, key=lambda r: r["schedule_position"])
    with httpx.Client(timeout=10, trust_env=False) as client:
        response = client.get(config.inference.base_url + "/slots")
        response.raise_for_status()
        slots = response.json()
    expected = {"seed": last["inference_seed"], "temperature": config.inference.temperature, "top_p": config.inference.top_p,
                "top_k": config.inference.top_k, "min_p": 0.0, "repeat_penalty": 1.0, "max_tokens": config.inference.max_output_tokens}
    if len(slots) != 1 or slots[0].get("is_processing") or slots[0].get("n_prompt_tokens_cache") != 0:
        raise ValueError("Backend is active or prompt caching is not zero")
    params = slots[0].get("params", {})
    if any(type(params.get(k)) not in (int, float)
           or (params[k] != v if type(v) is int else not math.isclose(params[k], v, rel_tol=1e-6))
           for k, v in expected.items()):
        raise ValueError("Actual sampler/seed differs from the last audited pilot request")
    record = {"status": "sampler_seed_cache_verified", "model_sha256": evidence.model_sha256,
              "backend_evidence_sha256": evidence.verification_artifact_sha256, "source_trial": last["trial_id"],
              "pilot_manifest_sha256": sha256_bytes((pilot_directory / "manifest.json").read_bytes()),
              "expected_request_settings": expected, "observed_slots": slots, "generation_requests": 0}
    publish_artifact(output, canonical_json(record))
    return {k: record[k] for k in ("status", "source_trial", "generation_requests")}
