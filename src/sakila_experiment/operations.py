"""Small operational commands around existing research components."""

from __future__ import annotations

import argparse
import json
import sqlite3
import urllib.error
from pathlib import Path

from .artifacts import canonical_json, publish_artifact, sha256_bytes


def add_commands(subcommands):
    for name in ("model", "backend", "metadata", "review", "experiment", "instrument"):
        parser = subcommands.add_parser(name, help=f"Auditable {name} operations")
        children = parser.add_subparsers(dest="operation", required=True)
        if name == "instrument":
            command = children.add_parser("validate", help="Verify a versioned instrument without inference or review approval")
            command.add_argument("--manifest", type=Path, required=True)
            command.add_argument("--output", type=Path, required=True)
        elif name == "model":
            command = children.add_parser("fetch")
            command.add_argument("--spec", type=Path, required=True)
            command.add_argument("--receipt", type=Path, required=True)
        elif name == "backend":
            command = children.add_parser("verify")
            command.add_argument("--model-receipt", type=Path, required=True)
            command.add_argument("--compose-file", type=Path, required=True)
            command.add_argument("--container", required=True)
            command.add_argument("--snapshot-root", type=Path, default=Path("snapshots/candidates-v2"))
            command.add_argument("--output-directory", type=Path, required=True)
            command.add_argument("--config", type=Path, default=Path("configs/local.toml"))
            command = children.add_parser("verify-sampler")
            command.add_argument("--backend-evidence", type=Path, required=True)
            command.add_argument("--pilot-directory", type=Path, required=True)
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--config", type=Path, default=Path("configs/local.toml"))
            command = children.add_parser("probe")
            command.add_argument("--backend-evidence", type=Path, required=True)
            command.add_argument("--snapshot-root", type=Path, default=Path("snapshots/candidates-v2"))
            command.add_argument("--output-directory", type=Path, required=True)
            command.add_argument("--question-id", default="P007")
            command.add_argument("--scenario", default="S3")
            command.add_argument("--allow-unreviewed", action="store_true")
        elif name == "metadata":
            command = children.add_parser("reconcile")
            command.add_argument("--events", type=Path, required=True)
            command.add_argument("--audit", type=Path, required=True)
            command.add_argument("--output-directory", type=Path, required=True)
            command.add_argument("--config", type=Path, default=Path("configs/local.toml"))
            command = children.add_parser("snapshot-build")
            command.add_argument("--first-export", type=Path, required=True)
            command.add_argument("--second-export", type=Path, required=True)
            command.add_argument("--audit", type=Path, required=True)
            command.add_argument("--spec", type=Path, required=True)
            command.add_argument("--output-directory", type=Path, required=True)
            command.add_argument("--config", type=Path, default=Path("configs/local.toml"))
            command = children.add_parser("validate-set")
            command.add_argument("--snapshot-root", type=Path, required=True)
            command.add_argument("--output", type=Path, required=True)
        elif name == "review":
            command = children.add_parser("package")
            command.add_argument("--output-directory", type=Path, required=True)
            command.add_argument("--main-results", type=Path)
            command.add_argument("--pilot-results", type=Path)
            command.add_argument("--config", type=Path, default=Path("configs/local.toml"))
            command = children.add_parser("annotation-round")
            command.add_argument("--output-directory", type=Path, required=True)
            command.add_argument("--config", type=Path, default=Path("configs/local.toml"))
            command = children.add_parser("consolidate")
            command.add_argument("--package", type=Path, required=True)
            command.add_argument("--a01", type=Path, required=True)
            command.add_argument("--a02", type=Path, required=True)
            command.add_argument("--output-directory", type=Path, required=True)
        else:
            command = children.add_parser("replay-fixtures", help="Evaluate existing revision-02 SQL on isolated auxiliary data; no inference")
            command.add_argument("--source-run", type=Path, required=True)
            command.add_argument("--output-directory", type=Path, required=True)
            command.add_argument("--config", type=Path, default=Path("configs/local.toml"))
            command = children.add_parser("reevaluate")
            command.add_argument("--source-run", type=Path, required=True)
            command.add_argument("--gold", type=Path, required=True)
            command.add_argument("--questions", type=Path, required=True)
            command.add_argument("--snapshot-root", type=Path, required=True)
            command.add_argument("--review-package", type=Path, required=True)
            command.add_argument("--adjudication-file", type=Path, required=True)
            command.add_argument("--receipt", type=Path, required=True)
            command.add_argument("--output-directory", type=Path, required=True)
            command.add_argument("--config", type=Path, default=Path("configs/local.toml"))
            command = children.add_parser("recover")
            command.add_argument("--run-directory", type=Path, required=True)
            command.add_argument("--trial-id", required=True)
            command.add_argument("--attempt-id", type=int, required=True)
            command.add_argument("--operator", required=True)
            command.add_argument("--note", required=True)
        command.add_argument("--config", type=Path, default=Path("configs/local.toml"))


def dispatch(args, config) -> dict:
    if args.command == "instrument":
        from .instrument import validate_instrument
        report = validate_instrument(config.project_root, args.manifest, args.output)
        return {key: report[key] for key in ("status", "benchmark_id", "question_count", "generation_requests", "main_experiment_allowed")}
    if args.command == "model":
        from .generation.model_assets import fetch_model
        try:
            record = fetch_model(config.project_root, args.spec, args.receipt, progress=lambda s: print(s, flush=True))
        except urllib.error.URLError:
            raise ValueError("Model download failed; no model was published. Resume with the same pinned specification") from None
        return {"status": record["status"], "model_id": record["model_id"], "main_experiment_allowed": False}
    if args.command == "backend":
        from .generation.runtime import verify_backend, verify_sampler
        if args.operation == "verify":
            return verify_backend(config, args.model_receipt, args.compose_file, args.container, args.snapshot_root, args.output_directory)
        if args.operation == "verify-sampler":
            return verify_sampler(config, args.backend_evidence, args.pilot_directory, args.output)
        from .generation.probe import repetition_probe
        return repetition_probe(config, args.snapshot_root, args.backend_evidence, args.output_directory, question_id=args.question_id, scenario=args.scenario, allow_unreviewed=args.allow_unreviewed)
    if args.command == "review":
        from .annotations import build_annotation_round, consolidate
        if args.operation == "annotation-round":
            return build_annotation_round(config.project_root, args.output_directory)
        if args.operation == "consolidate":
            return consolidate(args.package, args.a01, args.a02, args.output_directory)
        from .review import build_review_package
        record = build_review_package(config.project_root, args.output_directory, main_results=args.main_results, pilot_results=args.pilot_results)
        return {key: record[key] for key in ("status", "questions", "annotations", "business_terms")}
    if args.command == "experiment":
        if args.operation == "replay-fixtures":
            from .evaluation.robustness import RobustnessError, replay_fixtures
            from .evaluation.fixtures import FixtureError
            try:
                return replay_fixtures(config, args.source_run, args.output_directory, progress=lambda text: print(text, flush=True))
            except (RobustnessError, FixtureError) as exc:
                raise ValueError(str(exc)) from None
        if args.operation == "reevaluate":
            from .evaluation.reevaluate import reevaluate
            return reevaluate(config, args.source_run, args.gold, args.questions, args.snapshot_root, args.receipt,
                              args.output_directory, review_package=args.review_package, adjudication_file=args.adjudication_file)
        from .experiment.ledger import Ledger, LedgerError
        manifest_path, ledger_path = args.run_directory / "manifest.json", args.run_directory / "ledger.sqlite3"
        if not manifest_path.is_file() or not ledger_path.is_file():
            raise LedgerError("Recovery requires an existing experiment manifest and ledger")
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        with sqlite3.connect(ledger_path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
            row = connection.execute("SELECT manifest_sha256 FROM experiments WHERE experiment_id=?", (manifest["experiment_id"],)).fetchone()
        if row != (sha256_bytes(manifest_bytes),):
            raise LedgerError("Recovery manifest differs from the registered experiment")
        with Ledger(ledger_path) as ledger:
            ledger.recover_dispatch(manifest["experiment_id"], args.trial_id, args.attempt_id, operator=args.operator, note=args.note)
        return {"status": "incident_classified", "trial_id": args.trial_id, "attempt_id": args.attempt_id, "generation_requests": 0}
    if args.operation == "reconcile":
        from .metadata.ingestion_audit import reconcile_native_types
        events, receipt = reconcile_native_types(json.loads(args.events.read_bytes()), json.loads(args.audit.read_bytes()))
        publish_artifact(args.output_directory / "validated-ingestion.json", canonical_json(events))
        publish_artifact(args.output_directory / "fidelity-receipt.json", canonical_json(receipt))
        return receipt["validation"]
    if args.operation == "snapshot-build":
        from .metadata.snapshots import build_candidate
        return build_candidate(args.first_export, args.second_export, json.loads(args.audit.read_bytes()), json.loads(args.spec.read_bytes()), args.output_directory)
    from .metadata.snapshots import validate_scenario_set
    record = validate_scenario_set(args.snapshot_root)
    publish_artifact(args.output, canonical_json(record))
    return record
