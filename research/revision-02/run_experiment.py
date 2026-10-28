"""Execute the frozen exploratory protocol; stop on any incident, never repair.

All selection/annotation/review work must already be complete. This driver does
not inspect accuracy to choose inputs, change settings, or decide to continue.
It keeps the exact same Git/source version across diagnostic and benchmark.
"""
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
from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.config import load_config
from sakila_experiment.evaluation.fixtures import FIXTURE_CONTAINER
from sakila_experiment.evaluation.robustness import replay_fixtures
from sakila_experiment.experiment.diagnostics import load_diagnostic
from sakila_experiment.experiment.runner import run_diagnostic, run_preliminary
from sakila_experiment.generation.runtime import verify_backend, verify_sampler
from sakila_experiment.instrument import validate_instrument

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/revision02.toml")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--allow-unreviewed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.allow_unreviewed and not args.dry_run:
        raise ValueError("Explicit --allow-unreviewed is required; human review remains pending")
    config = load_config(args.config)
    output = args.directory.resolve()
    if not output.is_relative_to(ROOT / "runs/revision-02"):
        raise ValueError("Driver output must be inside the local revision-02 run workspace")
    validate_instrument(ROOT, config.resolve(config.benchmark_manifest))
    diagnostic_manifest = config.resolve(config.diagnostic_manifest)
    load_diagnostic(ROOT, diagnostic_manifest, config.experiment)
    if args.dry_run:
        print(json.dumps({"status": "offline_driver_plan_validated", "diagnostic_trials": 180,
                          "benchmark_trials": 600, "auxiliary_cases": 8, "generation_requests": 0,
                          "human_review_complete": False}), flush=True)
        return
    output.mkdir(parents=True, exist_ok=True)

    def event(stage, **details):
        row = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "stage": stage, **details}
        encoded = canonical_json(row)
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
        # No score-based gate or per-trial accuracy broadcast. Durable raw
        # responses/scores remain in the experiment ledger and local reports.
        if completed == 1 or completed % 10 == 0:
            event("assigned_trial_completed", trial_id=row["trial_id"], newly_completed_in_process=completed)

    def docker(*arguments):
        return subprocess.run(["docker", *arguments], cwd=ROOT, check=True, capture_output=True, text=True).stdout

    snapshots = ROOT / "runs/revision-02/metadata/preparation-03/snapshots"
    backend_directory = output / "backend"
    backend_path = backend_directory / "verification.json"
    diagnostic_directory, benchmark_directory = output / "diagnostic", output / "benchmark"
    try:
        running = set(docker("ps", "--format", "{{.Names}}").splitlines())
        if any(name.startswith("sakila-metadata-") for name in running):
            raise ValueError("Stop the project DataHub stack before inference; preserve its volumes")
        if FIXTURE_CONTAINER in running:
            docker("stop", FIXTURE_CONTAINER)
        event("start_verified_inference")
        docker("compose", "-f", "infra/inference/compose.coder7b.yaml", "up", "-d")
        deadline = time.monotonic() + 240
        with httpx.Client(timeout=5, trust_env=False) as client:
            while True:
                try:
                    response = client.get(config.inference.base_url + "/health")
                    if response.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() > deadline:
                    raise RuntimeError("Selected backend did not become healthy; no generation dispatched")
                time.sleep(2)
        if not backend_path.exists():
            verify_backend(config, ROOT / "runs/inference/coder7b/download.json",
                           ROOT / "infra/inference/compose.coder7b.yaml", "sakila-research-llama", snapshots, backend_directory)
        event("freeze_diagnostic", assigned_trials=180)
        run_diagnostic(config, snapshots, backend_path, diagnostic_directory, "revision02-diagnostic-01",
                       freeze_only=True, allow_unreviewed=True, progress=progress)
        event("run_diagnostic", assigned_trials=180)
        run_diagnostic(config, snapshots, backend_path, diagnostic_directory, "revision02-diagnostic-01",
                       allow_unreviewed=True, progress=progress)
        audit_run(diagnostic_directory)
        sampler_path = backend_directory / "sampler-verification.json"
        if not sampler_path.exists():
            verify_sampler(config, backend_path, diagnostic_directory, sampler_path)
        event("diagnostic_complete_freeze_benchmark", assigned_trials=600)
        run_preliminary(config, snapshots, backend_path, benchmark_directory, "revision02-benchmark-01",
                        pilot_directory=diagnostic_directory, freeze_only=True, allow_unreviewed=True, progress=progress)
        event("run_benchmark", assigned_trials=600)
        run_preliminary(config, snapshots, backend_path, benchmark_directory, "revision02-benchmark-01",
                        pilot_directory=diagnostic_directory, allow_unreviewed=True, progress=progress)
        audit_run(benchmark_directory)
        event("analyze_complete_runs")
        analyze_run(diagnostic_directory, output / "analysis/diagnostic")
        analyze_run(benchmark_directory, output / "analysis/benchmark")
        docker("compose", "-f", "infra/inference/compose.coder7b.yaml", "stop")
        event("replay_all_predictions_on_auxiliary_cases", cases=8, generation_requests=0)
        replay_fixtures(config, benchmark_directory, output / "auxiliary", progress=lambda text: event("auxiliary_case_complete", **json.loads(text)))
        report = {"status": "exploratory_pipeline_complete", "human_review_complete": False,
                  "main_experiment_allowed": False, "diagnostic_trials": 180, "benchmark_trials": 600,
                  "benchmark_manifest_sha256": sha256_bytes((benchmark_directory / "manifest.json").read_bytes()),
                  "primary_EX_report": str((output / "analysis/benchmark/report.md").relative_to(ROOT)),
                  "auxiliary_report": str((output / "auxiliary/report.json").relative_to(ROOT)), "public_results_embargo": True}
        publish_artifact(output / "pipeline-completion.json", canonical_json(report))
        event("pipeline_complete", diagnostic_trials=180, benchmark_trials=600)
    except Exception as error:
        event("pipeline_interrupted", error_type=type(error).__name__, error_message=str(error),
              automatic_retry=False, stored_responses_preserved=True)
        raise


if __name__ == "__main__":
    main()
