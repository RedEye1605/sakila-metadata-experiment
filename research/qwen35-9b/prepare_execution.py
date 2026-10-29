"""Bind the researcher's direct-main amendment without inventing pilot approval."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.experiment.execution_review import stimulus_identity, stimulus_scope
from sakila_experiment.instrument import ArtifactReference, BenchmarkManifest, validate_instrument

ROOT = Path(__file__).resolve().parents[2]
STATEMENT = "okay, mari kita lock jadi pakai qwen3.5 9b aja. dan ga usah pilot lagi, langsung saja 600 trial. saya pengen lanjut nullis. dan juga kamu ga usah monitor. biarin saya aja yang melihat dan beritahu kalau sudah. mari lock di qwen3.5 9b"


def ref(path: Path) -> dict:
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_bytes(path.read_bytes())}


def main():
    original_path = ROOT / "data/benchmarks/revision-03/execution-01/manifest.json"
    original = BenchmarkManifest.model_validate_json(original_path.read_bytes())
    proof = ROOT / "runs/qwen35-9b/reference-checks-01"
    amendment_path = ROOT / "data/amendments/qwen35-9b-direct-main-01.json"
    compose = ROOT / "infra/inference/compose.qwen35-9b.yaml"
    # Compose is deliberately simple: every list item after command and before
    # mem_limit is one string. Compare actual runtime Cmd against this exact list.
    command = []
    in_command = False
    for line in compose.read_text().splitlines():
        if line == "    command:":
            in_command = True
        elif in_command and line.startswith("      - "):
            command.append(line[8:].strip().strip('"'))
        elif in_command:
            break
    if not command or command[0] != "--model":
        raise ValueError("The versioned Compose command could not be read exactly")
    amendment = {
        "amendment_version": 1, "status": "user_authorized_direct_main", "source": "direct_user_statement",
        "statement": STATEMENT, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "upstream_model": "Qwen/Qwen3.5-9B", "selection_basis": "researcher_selected_after_prior_results",
        "source_instrument": ref(original_path),
        "model_specification": ref(ROOT / "configs/models/qwen35-9b-q4km.json"),
        "configuration": ref(ROOT / "configs/qwen35-9b-main.toml"), "compose": ref(compose),
        "prior_main_manifest": ref(ROOT / "runs/revision-03/main-01/benchmark/manifest.json"),
        "prior_candidate_completion": ref(ROOT / "runs/model-selection/qwen3-8b-01/completion.json"),
        "scope": stimulus_scope(original), "stimulus_identity": stimulus_identity(original),
        "backend_command": command, "capability_pilot": "waived_by_researcher",
        "generation_smoke": "waived_by_researcher", "preflight_generation_requests": 0,
        "main_trial_count": 600,
        "sampler_policy": "verify_each_completed_main_request_without_new_generation",
        "monitoring": "researcher_only_after_launch", "actual_results_publication": "local_only",
        "limitations": [
            "Selected after earlier main and candidate results; no retrospective preregistration or capability admission claim.",
            "New model/inference package on the known fixed30question benchmark; retain all prior results and report this history.",
            "Reasoning budget2048 and output4096 are bounded local settings, not a reproduction of publisher leaderboard conditions.",
            "Additional pilot/smoke generation explicitly waived; zero-generation engineering preflight and per-main-request sampler checks remain mandatory.",
        ],
    }
    if amendment_path.exists():
        existing = json.loads(amendment_path.read_bytes())
        amendment["recorded_at_utc"] = existing["recorded_at_utc"]
    publish_artifact(amendment_path, canonical_json(amendment))
    updated = original.model_copy(update={
        "benchmark_id": "sakila-revision03-qwen35-9b", "smoke_test": None,
        "execution_amendment": ArtifactReference.model_validate(ref(amendment_path)),
        "reference_validation": ArtifactReference.model_validate(ref(proof / "summary.json")),
        "reference_validation_lock": ArtifactReference.model_validate(ref(proof / "input-lock.json")),
    })
    destination = ROOT / "data/benchmarks/revision-03/qwen35-9b-execution-01/manifest.json"
    publish_artifact(destination, canonical_json(updated.model_dump(mode="json")))
    report = validate_instrument(ROOT, destination, destination.parent / "validation.json")
    print(json.dumps({"status": report["status"], "generation_requests": 0,
                      "main_trials": 600, "additional_pilot_requests": 0,
                      "amendment_sha256": sha256_bytes(amendment_path.read_bytes())}))


if __name__ == "__main__":
    main()
