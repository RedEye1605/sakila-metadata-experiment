"""Run the explicitly authorized600trial Qwen3.5-9B replication, without pilots."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from sakila_experiment.analysis.report import analyze_run, audit_run
from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.config import load_config
from sakila_experiment.evaluation.fixtures import FIXTURE_CONTAINER
from sakila_experiment.evaluation.robustness import replay_fixtures
from sakila_experiment.experiment.direct_main import verify_main_sampler
from sakila_experiment.experiment.runner import run_main
from sakila_experiment.instrument import validate_instrument

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research/revision-03"))
from write_thesis import build_thesis


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/qwen35-9b-main.toml")
    parser.add_argument("--directory", type=Path, default=ROOT / "runs/qwen35-9b/main-01")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--freeze-only", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    output = args.directory.resolve()
    if not output.is_relative_to(ROOT / "runs/qwen35-9b"):
        raise ValueError("Use the separate Qwen3.5-9B replication workspace")
    validate_instrument(ROOT, config.resolve(config.benchmark_manifest))
    if args.dry_run:
        print(json.dumps({"status": "offline_amended_inputs_verified", "main_trials": 600,
                          "pilot_requests": 0, "smoke_requests": 0, "generation_requests": 0}), flush=True)
        return
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise ValueError("Commit the verified source before freezing main execution")
    output.mkdir(parents=True, exist_ok=True)
    backend = output / "backend/verification.json"
    benchmark = output / "benchmark"
    snapshots = ROOT / "runs/revision-02/metadata/preparation-03/snapshots"

    def event(stage, **values):
        value = {"stage": stage, "timestamp_utc": datetime.now(timezone.utc).isoformat(), **values}
        with (output / "driver-events.jsonl").open("ab") as stream:
            stream.write(canonical_json(value)); stream.flush(); os.fsync(stream.fileno())
        print(json.dumps(value, sort_keys=True), flush=True)

    def docker(*values):
        return subprocess.check_output(["docker", *values], cwd=ROOT, text=True, stderr=subprocess.STDOUT)

    count = 0
    def progress(text):
        nonlocal count
        row = json.loads(text)
        verify_main_sampler(config, backend, benchmark, row["trial_id"])
        count += 1
        if count == 1 or count % 10 == 0:
            event("main_trial_completed", trial_id=row["trial_id"], newly_completed=count, sampler_verified=True)

    try:
        running = set(docker("ps", "--format", "{{.Names}}").splitlines())
        if any(name.startswith("sakila-metadata-") for name in running):
            raise ValueError("Metadata services must remain stopped during local inference")
        if FIXTURE_CONTAINER in running:
            docker("stop", FIXTURE_CONTAINER)
        event("freeze_main_inputs", main_trials=600, pilot_requests=0, smoke_requests=0)
        run_main(config, snapshots, backend, benchmark, "qwen35-9b-main-01", None,
                 freeze_only=True, progress=progress)
        if args.freeze_only:
            event("main_frozen_without_generation", main_trials=600, generation_requests=0)
            return
        # On an explicit resume, completed trials remain completed. A missing
        # sampler observation can only be recovered if the live slot still
        # binds that exact response; no request is ever generated to repair it.
        ledger = benchmark / "ledger.sqlite3"
        if ledger.exists():
            import sqlite3
            with sqlite3.connect(ledger.resolve().as_uri() + "?mode=ro", uri=True) as connection:
                finished = connection.execute("SELECT trial_id FROM events WHERE kind='trial_completed'").fetchall()
            for (trial_id,) in finished:
                verify_main_sampler(config, backend, benchmark, trial_id)
        event("run_main", assigned_trials=600, pilot_requests=0, smoke_requests=0)
        run_main(config, snapshots, backend, benchmark, "qwen35-9b-main-01", None, progress=progress)
        manifest, rows = audit_run(benchmark)
        event("analyze_main_results", completed_trials=len(rows))
        if not (output / "analysis/report.json").exists():
            analyze_run(benchmark, output / "analysis")
        publish_artifact(output / "primary-completion.json", canonical_json({
            "status": "main_primary_analysis_complete", "completed_main_trials": 600,
            "pilot_generation_requests": 0, "smoke_generation_requests": 0,
            "manifest_sha256": sha256_bytes((benchmark / "manifest.json").read_bytes()),
            "report": "analysis/report.md", "actual_results_publication": "local_only"}))
        event("primary_analysis_complete", completed_main_trials=600, report="analysis/report.md")
        docker("compose", "-f", "infra/inference/compose.qwen35-9b.yaml", "stop")
        if not (output / "auxiliary/report.json").exists():
            event("replay_frozen_sql_on_auxiliary_cases", cases=8, generation_requests=0)
            replay_fixtures(config, benchmark, output / "auxiliary",
                            progress=lambda text: event("auxiliary_case_complete", **json.loads(text)))
        if not (output / "thesis/source-and-output-hashes.json").exists():
            event("write_bab_iv_and_bab_v")
            build_thesis(ROOT, output, output / "thesis", include_frozen_context=True)
        publish_artifact(output / "pipeline-completion.json", canonical_json({
            "status": "main_pipeline_complete", "main_trials": 600, "pilot_generation_requests": 0,
            "smoke_generation_requests": 0, "main_manifest_sha256": sha256_bytes((benchmark / "manifest.json").read_bytes()),
            "source_commit": manifest["source_version"]["git_commit"], "primary_EX_report": "analysis/report.md",
            "bab_iv": "thesis/BAB_IV.md", "bab_v": "thesis/BAB_V.md", "actual_results_publication": "local_only"}))
        event("pipeline_complete", main_trials=600, auxiliary_cases=8, pilot_requests=0)
    except Exception as error:
        event("pipeline_interrupted", error_type=type(error).__name__, error_message=str(error),
              automatic_retry=False, stored_responses_preserved=True)
        raise


if __name__ == "__main__":
    main()
