"""Auditable review requirements; checking readiness never calls a model."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

from ..artifacts import canonical_json, sha256_bytes
from ..config import AppConfig
from ..contracts import load_gold, load_questions
from ..metadata.snapshots import SnapshotError, validate_scenario_set
from ..analysis.report import IntegrityError, audit_run


def main_readiness(config: AppConfig, snapshots: Path, backend_path: Path, pilot_directory: Path) -> dict:
    root = config.project_root.resolve()
    snapshots, backend_path, pilot_directory = snapshots.resolve(), backend_path.resolve(), pilot_directory.resolve()
    blockers, requirements, checks = [], [], []
    def check(name, passed, message, evidence=None):
        checks.append({"check": name, "status": "passed" if passed else "failed", "message": "Verified: " + name if passed else message, "evidence": evidence})
        if not passed:
            blockers.append(message)
    def requirement(name, paths, extra=None):
        hashes = {}
        for path in paths:
            if not path.is_file():
                check("artifact:" + str(path), False, "Missing artifact: " + str(path))
            else:
                hashes[str(path.relative_to(root)) if path.is_relative_to(root) else str(path)] = sha256_bytes(path.read_bytes())
        digest = sha256_bytes(canonical_json({"files": hashes, "extra": extra}))
        requirements.append({"component": name, "artifact_sha256": digest, "files": hashes, "extra": extra})
    questions = load_questions(root / "data/public/main.questions.jsonl")
    gold = load_gold(root / "data/private/main.gold.jsonl")
    pilot = load_questions(root / "data/pilot/questions.jsonl")
    pilot_gold = load_gold(root / "data/pilot/gold.jsonl")
    check("pilot_gold_semantic_status", all(r.review_status == "approved" for r in pilot_gold.values()), "Pilot gold semantic review is still draft")
    check("main_dataset_design", len(questions) == 30 and {q.question_id for q in questions} == gold.keys()
          and Counter(q.complexity for q in questions) == {c: 10 for c in ("simple", "medium", "complex")}
          and all(q.question_id.startswith("Q") for q in questions), "Main dataset must match the 30-question 10/10/10 design")
    check("gold_semantic_status", all(r.review_status == "approved" for r in gold.values()), "Main gold semantic review is still draft")
    normalized = lambda q: " ".join(q.question.casefold().split())
    check("pilot_exact_separation", not ({normalized(q) for q in questions} & {normalized(q) for q in pilot}),
          "Pilot/main exact question overlap detected; paraphrase review remains human-owned")
    try:
        validation = validate_scenario_set(snapshots)
        check("snapshot_set", True, "Four snapshot payloads and controls validated", validation)
    except (OSError, ValueError, KeyError, SnapshotError) as error:
        validation = None
        check("snapshot_set", False, "Snapshot set validation failed: " + type(error).__name__)
    requirement("benchmark", [root / "data/public/main.questions.jsonl", root / "data/private/main.gold.jsonl",
                               root / "data/pilot/questions.jsonl", root / "data/pilot/gold.jsonl", root / "docs/evaluation-protocol.md"])
    requirement("metadata", [root / "data/annotations/specification.json"] + [snapshots / s / "manifest.json" for s in ("S0", "S1", "S2", "S3")], validation)
    requirement("generation", [root / "prompts/generation.txt", backend_path, pilot_directory / "completion.json",
                                pilot_directory / "manifest.json", backend_path.parent / "sampler-verification.json"], config.inference.model_dump(mode="json"))
    requirement("analysis", [root / "docs/analysis-plan.md", root / "src/sakila_experiment/analysis/statistics.py"])
    try:
        backend = json.loads(backend_path.read_bytes())
        sampler = json.loads((backend_path.parent / "sampler-verification.json").read_bytes())
        check("sampler_evidence", sampler.get("status") == "sampler_seed_cache_verified"
              and sampler.get("model_sha256") == backend["model_sha256"]
              and sampler.get("backend_evidence_sha256") == sha256_bytes(backend_path.read_bytes())
              and sampler.get("pilot_manifest_sha256") == sha256_bytes((pilot_directory / "manifest.json").read_bytes()),
              "Sampler evidence must belong to the selected backend and audited pilot")
    except (OSError, ValueError, KeyError, TypeError) as error:
        check("sampler_evidence", False, "Selected-backend sampler evidence unavailable or invalid: " + type(error).__name__)
    try:
        pilot_manifest, records = audit_run(pilot_directory)
        check("pilot_integrity", True, "Pilot ledger, exports, prompts and result hashes verified")
        expected = {(q.question_id, s, 1) for q in pilot for s in config.experiment.scenario_ids}
        actual = {(r["question_id"], r["scenario_id"], r["repetition_id"]) for r in records}
        check("pilot_completeness", len(pilot) == 9 and len(records) == 36 and actual == expected
              and pilot_manifest["mode"] == "pilot", "A complete nine-question, 36-trial pilot is required")
        backend = json.loads(backend_path.read_bytes())
        check("pilot_configuration", pilot_manifest["inference_config"] == config.inference.model_dump(mode="json")
              and pilot_manifest["model_version_or_hash"] == backend["model_sha256"]
              and pilot_manifest["backend_evidence_sha256"] == sha256_bytes(backend_path.read_bytes())
              and pilot_manifest["prompt_template_sha256"] == sha256_bytes((root / "prompts/generation.txt").read_bytes())
              and pilot_manifest["snapshots"]["snapshot_sha256"] == (validation or {}).get("snapshot_sha256")
              and pilot_manifest["questions_sha256"] == sha256_bytes((root / "data/pilot/questions.jsonl").read_bytes())
              and pilot_manifest["gold_sha256"] == sha256_bytes((root / "data/pilot/gold.jsonl").read_bytes()),
              "Pilot evidence must match the selected model, backend, prompt, snapshots and pilot dataset")
        baseline = json.loads((root / "runs/database/baseline.json").read_bytes())
        check("pilot_database", pilot_manifest["database_schema_sha256"] == baseline["schema_sha256"] and pilot_manifest["database_data_sha256"] == baseline["data_sha256"],
              "Pilot database fingerprints must match the current frozen baseline")
        check("snapshot_database", all(json.loads((snapshots / s / "manifest.json").read_bytes()).get("database_schema_sha256") == baseline["schema_sha256"] for s in config.experiment.scenario_ids),
              "Scenario snapshots must refer to the frozen database schema")
        critical = ("generation/llama.py", "generation/prompt.py", "db/connection.py", "db/execute.py", "evaluation/compare.py", "evaluation/safety.py", "experiment/runner.py", "experiment/schedule.py")
        source = {row["path"]: row["sha256"] for row in pilot_manifest["source_version"]["source_files"]}
        changed = [p for p in critical if source.get("src/sakila_experiment/" + p) != sha256_bytes((root / "src/sakila_experiment" / p).read_bytes())]
        check("pilot_runtime_source", not changed, "Pilot generation/evaluation runtime source must match the final implementation", changed)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, IntegrityError) as error:
        check("pilot_integrity", False, "Pilot audit unavailable or invalid: " + type(error).__name__)
    decisions_path = root / "data/reviews/decisions.json"
    decisions = json.loads(decisions_path.read_bytes())["decisions"]
    for needed in requirements:
        matches = [d for d in decisions if d.get("component") == needed["component"] and d.get("artifact_sha256") == needed["artifact_sha256"]]
        approved = len(matches) == 1 and matches[0].get("status") == "approved" and bool(matches[0].get("reviewed_by")) and bool(matches[0].get("reviewed_at_utc"))
        needed["review_status"] = "approved" if approved else "pending"
        if not approved:
            blockers.append("Human review pending or stale: " + needed["component"])
    return {"format_version": 2, "status": "blocked" if blockers else "review_gates_passed", "main_experiment_allowed": False,
            "automated_checks": checks,
            "generation_executed": False, "blockers": blockers, "required_reviews": requirements,
            "next_gate": "freeze-main verifies all main prompt budgets and gold execution; run-main requires the unchanged frozen manifest and approved artifact hashes"}
