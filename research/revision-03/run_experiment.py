"""Twelve engineering requests,600 main trials,paired analysis and manuscripts."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from sakila_experiment.analysis.report import analyze_run, audit_run
from sakila_experiment.artifacts import canonical_json, publish_artifact
from sakila_experiment.config import load_config
from sakila_experiment.contracts import load_questions
from sakila_experiment.evaluation.fixtures import FIXTURE_CONTAINER
from sakila_experiment.evaluation.robustness import replay_fixtures
from sakila_experiment.experiment.execution_review import load_smoke
from sakila_experiment.experiment.runner import _prompt_budgets, run_engineering_smoke, run_main
from sakila_experiment.generation.runtime import verify_backend, verify_sampler
from sakila_experiment.instrument import read_manifest, validate_instrument
from write_thesis import build_thesis

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/revision03-main.toml")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    output = args.directory.resolve()
    if not output.is_relative_to(ROOT / "runs/revision-03"):
        raise ValueError("Output must be a local revision03 research workspace")
    manifest_path = config.resolve(config.benchmark_manifest)
    validate_instrument(ROOT, manifest_path)
    instrument, paths = read_manifest(ROOT, manifest_path)
    _, smoke_paths, _, _, _ = load_smoke(ROOT, instrument, paths)
    if args.dry_run:
        print(json.dumps({"status": "offline_review_and_inputs_verified", "smoke_requests": 12,
                          "main_requests": 600, "auxiliary_cases": 8, "generation_requests": 0,
                          "review_status": instrument.human_review_status, "reviewer_names_supplied": False}), flush=True)
        return
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise ValueError("Commit the verified implementation before freezing smoke/main source versions")
    output.mkdir(parents=True, exist_ok=True)

    def event(stage, **details):
        value = {"stage": stage, "timestamp_utc": datetime.now(timezone.utc).isoformat(), **details}
        encoded = canonical_json(value)
        with (output / "driver-events.jsonl").open("ab") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        print(encoded.decode().strip(), flush=True)

    completed = 0
    def progress(text):
        nonlocal completed
        row = json.loads(text)
        completed += 1
        if completed == 1 or completed % 10 == 0:
            event("assigned_trial_completed", trial_id=row["trial_id"], newly_completed_in_process=completed)

    def docker(*args):
        return subprocess.check_output(["docker", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT)

    snapshots = ROOT / "runs/revision-02/metadata/preparation-03/snapshots"
    backend = output / "backend"
    backend_path = backend / "verification.json"
    smoke, benchmark = output / "smoke", output / "benchmark"
    try:
        running = set(docker("ps", "--format", "{{.Names}}").splitlines())
        if any(name.startswith("sakila-metadata-") for name in running):
            raise ValueError("Stop the project DataHub services before GPU inference; preserve volumes")
        if FIXTURE_CONTAINER in running:
            docker("stop", FIXTURE_CONTAINER)
        event("start_selected_backend")
        docker("compose", "-f", "infra/inference/compose.coder7b.yaml", "up", "-d")
        deadline = time.monotonic() + 240
        with httpx.Client(timeout=5, trust_env=False) as client:
            while True:
                try:
                    if client.get(config.inference.base_url + "/health").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError("Backend health verification timed out before generation")
                time.sleep(2)
        if not backend_path.exists():
            verify_backend(config, ROOT / "runs/inference/coder7b/download.json",
                           ROOT / "infra/inference/compose.coder7b.yaml", "sakila-research-llama", snapshots, backend,
                           context_questions=smoke_paths["questions"])
        context_path = backend / "main-context-checks.json"
        if not context_path.exists():
            questions = {q.question_id: q for q in load_questions(paths["questions"])}
            budgets = _prompt_budgets(config, backend_path, questions, snapshots)
            if len(budgets) != 120:
                raise ValueError("Every30-by4main prompt must be checked")
            publish_artifact(context_path, canonical_json({"status": "all_main_contexts_verified", "generation_requests": 0,
                "prompt_checks": budgets, "maximum_input_tokens": max(b["input_tokens"] for b in budgets),
                "max_output_tokens": config.inference.max_output_tokens, "context_tokens": config.inference.context_tokens}))
        event("freeze_and_run_separate_smoke", assigned_trials=12)
        run_engineering_smoke(config, snapshots, backend_path, smoke, "revision03-smoke-01", freeze_only=True, progress=progress)
        run_engineering_smoke(config, snapshots, backend_path, smoke, "revision03-smoke-01", progress=progress)
        audit_run(smoke)
        sampler = backend / "sampler-verification.json"
        if not sampler.exists():
            verify_sampler(config, backend_path, smoke, sampler)
        event("freeze_all_main_inputs", assigned_trials=600)
        run_main(config, snapshots, backend_path, benchmark, "revision03-main-01", smoke, freeze_only=True, progress=progress)
        event("run_main", assigned_trials=600)
        run_main(config, snapshots, backend_path, benchmark, "revision03-main-01", smoke, progress=progress)
        audit_run(benchmark)
        event("analyze_main_results")
        analyze_run(benchmark, output / "analysis")
        docker("compose", "-f", "infra/inference/compose.coder7b.yaml", "stop")
        event("replay_frozen_sql_on_auxiliary_cases", cases=8, generation_requests=0)
        replay_fixtures(config, benchmark, output / "auxiliary",
                        progress=lambda text: event("auxiliary_case_complete", **json.loads(text)))
        event("write_bab_iv_and_bab_v")
        build_thesis(ROOT, output, output / "thesis")
        publish_artifact(output / "pipeline-completion.json", canonical_json({"status": "main_pipeline_complete",
            "main_trials": 600, "engineering_requests": 12, "review_status": "user_attested_complete",
            "reviewer_identity_status": "pending_user_entry", "primary_EX_report": str((output / "analysis/report.md").relative_to(ROOT)),
            "bab_iv": str((output / "thesis/BAB_IV.md").relative_to(ROOT)), "bab_v": str((output / "thesis/BAB_V.md").relative_to(ROOT)),
            "actual_results_publication": "local_only"}))
        event("pipeline_complete", main_trials=600, auxiliary_cases=8)
    except Exception as error:
        event("pipeline_interrupted", error_type=type(error).__name__, error_message=str(error),
              automatic_retry=False, stored_responses_preserved=True)
        raise


if __name__ == "__main__":
    main()
