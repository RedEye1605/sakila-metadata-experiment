"""Small research CLI; main inference execution is intentionally gated."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .artifacts import canonical_json, publish_artifact
from .config import ConfigurationError, load_config
from .doctor import inspect_environment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sakila-experiment")
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    from .operations import add_commands
    add_commands(subcommands)
    doctor = subcommands.add_parser("doctor", help="Inspect the environment without changing services")
    doctor.add_argument("--config", type=Path, default=Path("configs/local.toml"))
    doctor.add_argument("--output", type=Path, help="Publish a non-overwriting JSON report")
    doctor.add_argument("--offline", action="store_true", help="Skip service network probes")
    doctor.add_argument("--require-services", action="store_true")
    database = subcommands.add_parser("database", help="Set up or audit the isolated research database")
    database_commands = database.add_subparsers(dest="database_command", required=True)
    bootstrap = database_commands.add_parser("bootstrap", help="Import official Sakila into the dedicated local instance")
    bootstrap.add_argument("--config", type=Path, default=Path("configs/local.toml"))
    bootstrap.add_argument("--container-name", default="sakila-research-mysql", help="Default research container or a separately named sakila-repro-...-mysql")
    inspection = database_commands.add_parser("inspect", help="Audit installed schema and hash all base-table records")
    inspection.add_argument("--config", type=Path, default=Path("configs/local.toml"))
    inspection.add_argument("--output", type=Path, required=True)
    verification = database_commands.add_parser("verify", help="Verify schema/data against an existing audit")
    verification.add_argument("--config", type=Path, default=Path("configs/local.toml"))
    verification.add_argument("--baseline", type=Path, required=True)
    schedule = subcommands.add_parser("schedule", help="Create a deterministic trial plan without calling any model")
    schedule.add_argument("--config", type=Path, default=Path("configs/local.toml"))
    schedule.add_argument("--questions", type=Path, required=True)
    schedule.add_argument("--output", type=Path, required=True)
    schedule.add_argument("--pilot", action="store_true")
    gold = subcommands.add_parser("validate-gold", help="Execute private draft references and create a human review package")
    gold.add_argument("--config", type=Path, default=Path("configs/local.toml"))
    gold.add_argument("--questions", type=Path, required=True)
    gold.add_argument("--gold", type=Path, required=True)
    gold.add_argument("--output-directory", type=Path, required=True)
    pilot = subcommands.add_parser("pilot", help="Run separate engineering questions; main execution remains unavailable")
    pilot.add_argument("--config", type=Path, default=Path("configs/pilot.toml"))
    pilot.add_argument("--snapshot-root", type=Path, default=Path("snapshots/candidates-v2"))
    pilot.add_argument("--backend-evidence", type=Path, default=Path("runs/inference/backend-01/verification.json"))
    pilot.add_argument("--output-directory", type=Path, required=True)
    pilot.add_argument("--experiment-id", required=True)
    pilot.add_argument("--smoke", action="store_true", help="Use only pilot question P001 across all four scenarios")
    pilot.add_argument("--dry-run", action="store_true", help="Verify dependencies and publish manifest/plan without generation")
    analysis = subcommands.add_parser("analyze", help="Audit a complete run; pilot receives descriptive results only")
    analysis.add_argument("--config", type=Path, default=Path("configs/local.toml"))
    analysis.add_argument("--run-directory", type=Path, required=True)
    analysis.add_argument("--output-directory", type=Path, required=True)
    readiness = subcommands.add_parser("readiness", help="Report exact review hashes and blockers without generation")
    readiness.add_argument("--config", type=Path, default=Path("configs/pilot.toml"))
    readiness.add_argument("--snapshot-root", type=Path, default=Path("snapshots/candidates-v2"))
    readiness.add_argument("--backend-evidence", type=Path, default=Path("runs/inference/backend-01/verification.json"))
    readiness.add_argument("--pilot-directory", type=Path, required=True)
    readiness.add_argument("--output", type=Path, required=True)
    for name, help_text in (("freeze-main", "Freeze reviewed main inputs, all prompt budgets and gold results; no generation"),
                            ("run-main", "Run/resume only an unchanged, reviewed frozen main experiment"),
                            ("freeze-preliminary", "Freeze provisional 600-trial inputs without approving references"),
                            ("run-preliminary", "Explicitly run provisional pilot or frozen 600-trial evaluation")):
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument("--config", type=Path, default=Path("configs/pilot.toml"))
        command.add_argument("--snapshot-root", type=Path, default=Path("snapshots/candidates-v2"))
        command.add_argument("--backend-evidence", type=Path, default=Path("runs/inference/backend-01/verification.json"))
        command.add_argument("--pilot-directory", type=Path, required=name in {"freeze-main", "run-main"})
        command.add_argument("--output-directory", type=Path, required=True)
        command.add_argument("--experiment-id", required=True)
        if "preliminary" in name:
            command.add_argument("--allow-unreviewed", action="store_true", help="Acknowledge provisional EX against unreviewed references; never creates approval")
            if name == "run-preliminary":
                command.add_argument("--pilot", action="store_true", help="Use the separate nine-question, 36-trial pilot")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor" and args.offline and args.require_services:
        print("--offline and --require-services cannot be combined", file=sys.stderr)
        return 2
    try:
        config = load_config(args.config)
        if args.command in {"freeze-preliminary", "run-preliminary"}:
            from .experiment.runner import RunError, run_preliminary
            from .experiment.ledger import LedgerError
            from .generation.llama import LLMServiceError
            from .metadata.snapshots import SnapshotError
            from .contracts import DatasetError
            try:
                report = run_preliminary(config, args.snapshot_root, args.backend_evidence, args.output_directory, args.experiment_id,
                                         pilot_directory=args.pilot_directory, pilot=getattr(args, "pilot", False),
                                         freeze_only=args.command == "freeze-preliminary", allow_unreviewed=args.allow_unreviewed,
                                         progress=lambda text: print(text, flush=True))
            except (RunError, LedgerError, LLMServiceError, SnapshotError, DatasetError) as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(canonical_json(report).decode(), end="")
            return 0
        if args.command in {"model", "backend", "metadata", "review", "experiment"}:
            from .operations import dispatch
            from .experiment.ledger import LedgerError
            from .generation.llama import LLMServiceError
            from .metadata.snapshots import SnapshotError
            try:
                report = dispatch(args, config)
            except (ValueError, LedgerError, LLMServiceError, SnapshotError) as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(canonical_json(report).decode(), end="")
            return 0
        if args.command in {"freeze-main", "run-main"}:
            from .experiment.runner import RunError, run_main
            from .experiment.ledger import LedgerError
            from .generation.llama import LLMServiceError
            from .metadata.snapshots import SnapshotError
            from .contracts import DatasetError
            try:
                report = run_main(config, args.snapshot_root, args.backend_evidence, args.output_directory, args.experiment_id,
                                  args.pilot_directory, freeze_only=args.command == "freeze-main", progress=lambda text: print(text, flush=True))
            except (RunError, LedgerError, LLMServiceError, SnapshotError, DatasetError) as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(canonical_json(report).decode(), end="")
            return 0
        if args.command == "analyze":
            from .analysis.report import IntegrityError, analyze_run
            try:
                report = analyze_run(args.run_directory, args.output_directory)
            except IntegrityError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(canonical_json({k: report[k] for k in ("mode", "experiment_id", "integrity_verified", "main_research_results")}).decode(), end="")
            return 0
        if args.command == "readiness":
            from .experiment.readiness import main_readiness
            report = main_readiness(config, args.snapshot_root, args.backend_evidence, args.pilot_directory)
            publish_artifact(args.output, canonical_json(report))
            print(canonical_json(report).decode(), end="")
            return 0 if report["status"] == "review_gates_passed" else 1
        if args.command == "pilot":
            from .contracts import DatasetError
            from .experiment.runner import RunError, run_pilot
            from .experiment.ledger import LedgerError
            from .generation.llama import LLMServiceError
            from .metadata.snapshots import SnapshotError
            try:
                report = run_pilot(config, args.snapshot_root, args.backend_evidence, args.output_directory, args.experiment_id,
                                   smoke=args.smoke, dry_run=args.dry_run, progress=lambda text: print(text, flush=True))
            except (RunError, LedgerError, LLMServiceError, SnapshotError, DatasetError) as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(canonical_json(report).decode(), end="")
            return 0
        if args.command == "validate-gold":
            from .contracts import DatasetError
            from .evaluation.gold import validate_gold_dataset

            try:
                report = validate_gold_dataset(config, args.questions, args.gold, args.output_directory)
            except DatasetError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            print(canonical_json({key: report[key] for key in ("status", "question_count", "human_review_complete", "llm_generation_trials")}).decode(), end="")
            return 0
        if args.command == "schedule":
            from .artifacts import sha256_bytes
            from .contracts import DatasetError, load_questions
            from .experiment.schedule import build_schedule, schedule_document

            try:
                questions = load_questions(args.questions)
                assignments = build_schedule(questions, config.experiment, pilot=args.pilot)
            except DatasetError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            document = schedule_document(assignments, config.experiment, pilot=args.pilot)
            document["questions_sha256"] = sha256_bytes(args.questions.read_bytes())
            publish_artifact(args.output, canonical_json(document))
            print(canonical_json({"status": "planned_only", "trial_count": len(assignments), "generation_executed": False}).decode(), end="")
            return 0
        if args.command == "database":
            from .bootstrap import BootstrapError, bootstrap_database

            try:
                if args.database_command == "bootstrap":
                    result = bootstrap_database(config, container_name=args.container_name)
                else:
                    from .db.connection import DatabasePolicyError
                    from .db.inspect import inspect_database, verify_fingerprint

                    import pymysql

                    try:
                        audit = inspect_database(config)
                        if args.database_command == "verify":
                            verify_fingerprint(audit, json.loads(args.baseline.read_text()))
                        else:
                            publish_artifact(args.output, canonical_json(audit))
                        result = {"status": "verified" if args.database_command == "verify" else "audited", "base_tables": len(audit["technical_schema"]["tables"]), "schema_sha256": audit["schema_sha256"], "data_sha256": audit["data_sha256"]}
                    except (pymysql.MySQLError, DatabasePolicyError):
                        print("Database audit failed: check service, reader grants, and baseline integrity", file=sys.stderr)
                        return 1
            except BootstrapError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(canonical_json(result).decode(), end="")
            return 0
        report = inspect_environment(config, services=not args.offline)
        content = canonical_json(report)
        if args.output:
            publish_artifact(args.output, content)
        sys.stdout.buffer.write(content) if hasattr(sys.stdout, "buffer") else print(content.decode(), end="")
        if args.require_services and any(item["status"] not in {"ok", "reachable"} for item in report.get("services", {}).values()):
            return 1
        return 0
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except FileExistsError:
        print("Output artifact already exists with different content; choose a new path", file=sys.stderr)
        return 2
    except OSError:
        print("Local inspection or artifact publication failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

