"""Hash-bound capability pilots: separate questions, no significance selection."""
from __future__ import annotations

import importlib.metadata
import json
import math
import platform
import random
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from ..artifacts import canonical_json, sha256_bytes
from ..contracts import DatasetError, load_gold, load_questions
from ..db.inspect import inspect_database, verify_fingerprint
from ..evaluation.structure import profile_sql
from ..generation.backend import check_live_backend, load_backend_evidence
from ..generation.model_assets import ModelSpec
from ..instrument import ArtifactReference, validate_reference_code, validate_permutation_witnesses
from ..metadata.snapshots import validate_scenario_set
from .schedule import TrialAssignment, inference_seed

SCENARIOS = ("S0", "S1", "S2", "S3")


def candidate_schedule(questions, protocol):
    if (len(questions) != 12 or len({q.question_id for q in questions}) != 12
            or any(not q.question_id.startswith("P3") for q in questions)
            or protocol.get("repetitions") != 2 or protocol.get("scenario_ids") != list(SCENARIOS)
            or protocol.get("question_count") != 12 or protocol.get("assigned_trials_per_candidate") != 96):
        raise DatasetError("Capability pilot requires12separateP3questions by4conditions by2repetitions")
    generator = random.Random(protocol["order_seed"])
    assignments = []
    for repetition in (1, 2):
        block = [(q, s) for q in sorted(questions, key=lambda q: q.question_id) for s in SCENARIOS]
        generator.shuffle(block)
        for question, scenario in block:
            assignments.append(TrialAssignment(f"{question.question_id}-{scenario}-r{repetition:02d}",
                question.question_id, question.complexity, scenario, repetition,
                inference_seed(protocol["inference_seed_base"], question.question_id, repetition), len(assignments) + 1))
    return tuple(assignments)


def load_candidate_bundle(root: Path, path: Path):
    definition = json.loads(path.read_bytes())
    if (definition.get("status") != "frozen_AI_checked_engineering_pilot"
            or definition.get("main_experiment_allowed") is not False
            or definition.get("human_review_complete") is not False):
        raise DatasetError("Capability evidence must not impersonate reviewed main approval")
    paths = {key: ArtifactReference.model_validate(value).verified_path(root)
             for key, value in definition["artifacts"].items()}
    required = {"questions", "gold", "contracts", "protocol", "independent_gold", "independent_receipt",
                "reference_summary", "reference_lock", "mutations", "fixture_specification",
                "candidate_models", "independent_correction", "reference_correction", "canonical_gold"}
    if set(paths) != required:
        raise DatasetError("Capability pilot provenance is incomplete")
    questions, gold = load_questions(paths["questions"]), load_gold(paths["gold"])
    canonical = load_gold(paths["canonical_gold"])
    ids = {q.question_id for q in questions}
    contract_rows = [json.loads(x) for x in paths["contracts"].read_bytes().splitlines() if x.strip()]
    contracts = {x["question_id"]: x for x in contract_rows}
    if (set(gold) != ids or set(canonical) != ids or set(contracts) != ids or len(contract_rows) != len(contracts)
            or any(g.column_order != "permutation" for g in gold.values())
            or any(profile_sql(canonical[q.question_id].sql).complexity != q.complexity for q in questions)):
        raise DatasetError("Capability question/reference/contract identities differ")
    optimized = {qid for qid in ids if gold[qid].sql != canonical[qid].sql}
    if optimized != {"P309"}:
        raise DatasetError("Only the declaredP309execution optimization may differ from canonical profiling")
    protocol = json.loads(paths["protocol"].read_bytes())
    assignments = candidate_schedule(questions, protocol)
    if (protocol.get("status") != "engineering_only_no_main_authorization"
            or protocol.get("reasoning_mode") != "on" or protocol.get("reasoning_token_budget") != 2048):
        raise DatasetError("Unexpected declared pilot protocol")
    summary, lock, independent = (json.loads(paths[k].read_bytes()) for k in
                                  ("reference_summary", "reference_lock", "independent_receipt"))
    correction = json.loads(paths["independent_correction"].read_bytes())
    if (correction.get("locked_interpretations_unchanged") is not True
            or correction.get("business_rules_or_wording_changed") is not False
            or correction.get("reference_artifact_sha256", {}).get(paths["independent_gold"].name)
                != sha256_bytes(paths["independent_gold"].read_bytes())
            or correction.get("original_artifact_sha256", {}).get("receipt.json")
                != sha256_bytes(paths["independent_receipt"].read_bytes())):
        raise DatasetError("Independent reference correction lost its original interpretation binding")
    if (independent.get("gold_A_read") is not False or independent.get("contracts_A_read") is not False
            or independent.get("engineering_review_complete") is not True
            or independent.get("execution_readiness", {}).get("material_wording_ambiguity_found") is not False
            or independent.get("input_sha256", {}).get("data/benchmarks/model-pilot-01/questions.jsonl")
                != sha256_bytes(paths["questions"].read_bytes())):
        raise DatasetError("Independent interpretation is missing or belongs to another pilot")
    validate_reference_code(root, lock)
    if (lock["questions_sha256"] != sha256_bytes(paths["questions"].read_bytes())
            or lock["gold_a_sha256"] != sha256_bytes(paths["gold"].read_bytes())
            or lock["gold_b_files"] != [{"path": str(paths["independent_gold"].relative_to(root)),
                                        "sha256": sha256_bytes(paths["independent_gold"].read_bytes())}]
            or lock["fixture_definition_sha256"] != sha256_bytes(paths["fixture_specification"].read_bytes())
            or lock["mutations_artifact"] != {"path": str(paths["mutations"].relative_to(root)),
                                             "sha256": sha256_bytes(paths["mutations"].read_bytes())}
            or summary.get("input_lock_sha256") != sha256_bytes(paths["reference_lock"].read_bytes())
            or summary.get("primary_database_unchanged") is not True):
        raise DatasetError("Reference agreement receipt has stale inputs")
    mutations = json.loads(paths["mutations"].read_bytes())
    rows = {x["question_id"]: x for x in summary["records"]}
    cases = summary["cases"]
    fixture_ids = [x["fixture_id"] for x in json.loads(paths["fixture_specification"].read_bytes())["cases"]]
    if (set(rows) != ids or set(mutations) != ids or len(cases) != 10
            or len(set(cases)) != 10 or "baseline" not in cases
            or len(fixture_ids) != 9 or len(set(fixture_ids)) != 9 or cases != ["baseline", *fixture_ids]
            or any(not row["reference_agreement_all_checked"] or not row["reference_execution_valid"]
                   or not row["all_predeclared_mutants_distinguished"] for row in rows.values())):
        raise DatasetError("Capability references require complete agreement and distinguishing witnesses")
    validate_permutation_witnesses(paths["reference_summary"], paths["reference_lock"], summary, mutations, ids)
    return definition, paths, protocol, questions, gold, contracts, assignments, lock


def candidate_inputs(config, snapshots, backend_path, definition_path):
    from .runner import _prompt_budgets, source_version
    root = config.project_root
    definition, paths, protocol, questions, gold, contracts, assignments, lock = load_candidate_bundle(root, definition_path)
    if config.benchmark_manifest or config.diagnostic_manifest:
        raise DatasetError("A capability pilot cannot inherit main or diagnostic manifests")
    if lock["database_config"] != config.database.model_dump(mode="json"):
        raise DatasetError("Reference validation database policy differs")
    settings = config.inference.model_dump(mode="json")
    for key in ("temperature", "top_p", "top_k", "max_output_tokens", "context_tokens"):
        if settings[key] != protocol[key]:
            raise DatasetError("Candidate inference settings differ from the predeclared protocol")
    if config.prompt_template != protocol["prompt_template"]:
        raise DatasetError("Candidate prompt differs from the declared common template")
    validation = validate_scenario_set(snapshots)
    if validation["snapshot_sha256"] != definition["snapshot_sha256"]:
        raise DatasetError("Candidate snapshot set differs from frozen metadata")
    evidence, backend = load_backend_evidence(backend_path)
    check_live_backend(config.inference, backend)
    model_order = json.loads(paths["candidate_models"].read_bytes())
    specs = [ModelSpec.model_validate_json(ArtifactReference.model_validate(x).verified_path(root).read_bytes())
             for x in model_order["order"]]
    if (model_order.get("status") != "pinned_before_any_candidate_generation" or len(specs) != 2
            or len({x.model_sha256 for x in specs}) != 2
            or not any(s.model_sha256 == evidence.model_sha256 and s.alias == evidence.model_id
                       and s.model_id == backend["model_repository"] for s in specs)):
        raise DatasetError("Backend is not one of the two predeclared pinned candidates")
    command = backend["command"]
    for flag, value in (("--reasoning", "on"), ("--reasoning-format", "deepseek"), ("--reasoning-budget", "2048")):
        if flag not in command or command[command.index(flag) + 1] != value:
            raise DatasetError("Candidate reasoning mode/budget differs from protocol")
    baseline = json.loads((root / "runs/database/baseline.json").read_bytes())
    actual = inspect_database(config)
    verify_fingerprint(actual, baseline)
    if any(lock["database_" + key] != actual[key] for key in ("schema_sha256", "data_sha256")):
        raise DatasetError("Candidate reference database changed")
    prompts = _prompt_budgets(config, backend_path, {q.question_id: q for q in questions}, snapshots)
    manifest = {"manifest_version": 1, "mode": "candidate_pilot", "evaluation_status": "engineering_draft_reference",
        "main_experiment_allowed": False, "human_review_status": "pending", "allow_unreviewed": True,
        "public_results_embargo": True, "trial_count": 96, "candidate_manifest_sha256": sha256_bytes(definition_path.read_bytes()),
        "candidate_manifest": str(definition_path.relative_to(root)), "candidate_protocol": protocol,
        "questions_sha256": sha256_bytes(paths["questions"].read_bytes()), "gold_sha256": sha256_bytes(paths["gold"].read_bytes()),
        "gold_review_status": ["draft"], "inference_config": settings, "database_config": config.database.model_dump(mode="json"),
        "fixed_request_parameters": protocol["fixed_request_parameters"], "experiment_config": protocol,
        "python_version": platform.python_version(),
        "package_versions": {name: importlib.metadata.version(name) for name in ("pydantic", "httpx", "pymysql", "sqlglot")},
        "database_schema_sha256": actual["schema_sha256"], "database_data_sha256": actual["data_sha256"],
        "mysql_version": actual["server"]["version"], "backend_evidence_sha256": evidence.verification_artifact_sha256,
        "backend_evidence": backend, "model_id": evidence.model_id, "model_version_or_hash": evidence.model_sha256,
        "backend_revision": evidence.backend_revision, "snapshots": validation,
        "snapshot_manifest_sha256": {s: sha256_bytes((snapshots / s / "manifest.json").read_bytes()) for s in SCENARIOS},
        "prompt_template_sha256": sha256_bytes(config.resolve(config.prompt_template).read_bytes()),
        "trial_plan_sha256": sha256_bytes(canonical_json([asdict(x) for x in assignments])),
        "comparator_version": "ex-results-v3-column-permutation", "source_version": source_version(root),
        "metadata_provenance": [json.loads((snapshots / s / "manifest.json").read_bytes()) for s in SCENARIOS],
        "complete_candidate_prompt_budgets": prompts,
        "question_attributes": {q: {"primary_need": c["primary_need"], "semantic_family": c["domain_family"] or q,
                                     "spider_level": c["profile"]["spider_level"]} for q, c in contracts.items()},
        "note": "Engineering capability evidence against independently checked AI draft references; not main research results or human approval."}
    return manifest, assignments, {q.question_id: q for q in questions}, gold


def capability_decision(records, attributes):
    """Admission uses only S3 capability; no condition difference or p-value."""
    s3 = [x for x in records if x["scenario_id"] == "S3"]
    identifiers = {r["question_id"] for r in records}
    cells = {(r["question_id"], r["scenario_id"], r["repetition_id"]) for r in records}
    if (len(records) != 96 or len(s3) != 24 or len(identifiers) != 12 or set(attributes) != identifiers
            or cells != {(q, s, r) for q in identifiers for s in SCENARIOS for r in (1, 2)}
            or any(type(x["execution_accuracy"]) is not int or x["execution_accuracy"] not in (0, 1) for x in records)):
        raise DatasetError("Complete96trial capability evidence is required")
    domain = [x for x in s3 if attributes[x["question_id"]]["primary_need"] == "domain_integration"]
    if len(domain) != 12:
        raise DatasetError("All six domain questions require both repetitions")
    families = Counter(attributes[x["question_id"]]["semantic_family"] for x in domain if x["execution_accuracy"])
    checks = {"S3_correct_at_least18of24": sum(x["execution_accuracy"] for x in s3) >= 18,
              "S3_domain_correct_at_least6of12": sum(x["execution_accuracy"] for x in domain) >= 6,
              "S3_each_of3families_has_correct_trial": len(families) == 3,
              "S3_SQL_success_at_least23of24": sum(x["execution_status"] == "success" for x in s3) >= 23}
    return {"status": "capability_pass" if all(checks.values()) else "capability_not_demonstrated",
            "checks": checks, "S3_correct": sum(x["execution_accuracy"] for x in s3),
            "S3_domain_correct": sum(x["execution_accuracy"] for x in domain),
            "domain_family_successes": dict(families), "main_experiment_allowed": False,
            "selection_uses_p_values_or_condition_differences": False,
            "limits": "Small AI-reference engineering pilot; passing does not establish main EX, significance or human review."}


def validate_candidate_sampler(proof, manifest, records, manifest_sha256):
    """An existing file is not evidence until its complete run binding is checked."""
    last = max(records, key=lambda r: r["schedule_position"])
    settings = manifest["inference_config"]
    expected = {"seed": last["inference_seed"], "temperature": settings["temperature"],
                "top_p": settings["top_p"], "top_k": settings["top_k"], "min_p": 0.0,
                "repeat_penalty": 1.0, "max_tokens": settings["max_output_tokens"]}
    if (proof.get("status") != "sampler_seed_cache_verified"
            or proof.get("model_sha256") != manifest["model_version_or_hash"]
            or proof.get("backend_evidence_sha256") != manifest["backend_evidence_sha256"]
            or proof.get("pilot_manifest_sha256") != manifest_sha256
            or proof.get("source_trial") != last["trial_id"]
            or proof.get("generation_requests") != 0
            or proof.get("expected_request_settings") != expected):
        raise DatasetError("Sampler proof does not identify the complete candidate run/settings")
    slots = proof.get("observed_slots")
    if (not isinstance(slots, list) or len(slots) != 1 or not isinstance(slots[0], dict)
            or slots[0].get("is_processing") is not False or slots[0].get("n_prompt_tokens_cache") != 0):
        raise DatasetError("Candidate sampler proof lacks an idle uncached observed slot")
    params = slots[0].get("params", {})
    for key, value in expected.items():
        observed = params.get(key)
        if (type(observed) not in (int, float)
                or (observed != value if type(value) is int else not math.isclose(observed, value, rel_tol=1e-6))):
            raise DatasetError("Observed candidate sampler/seed differs from frozen request")
