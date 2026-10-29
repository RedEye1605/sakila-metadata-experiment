"""Pilot orchestration with durable responses and no semantic repair or retries.

Main execution is guarded by artifact-specific human reviews, complete pilot
evidence and a separate frozen manifest. Pilot uses separate P-prefixed inputs.
"""

from __future__ import annotations

import importlib.metadata
import json
import platform
import re
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ..artifacts import canonical_json, publish_artifact, sha256_bytes
from ..config import AppConfig
from ..contracts import DatasetError, load_gold, load_questions
from ..db.execute import execute_sql
from ..db.inspect import inspect_database, verify_fingerprint
from ..evaluation.compare import COMPARATOR_VERSION, EvaluationError, compare_results, comparison_spec
from ..evaluation.safety import extract_sql
from ..generation.backend import check_live_backend, load_backend_evidence
from ..generation.llama import GenerationResponse, LlamaClient, LLMServiceError
from ..generation.prompt import build_prompt
from ..metadata.snapshots import validate_scenario_set
from .ledger import Ledger, LedgerError
from .schedule import build_schedule


class RunError(RuntimeError):
    pass


def source_version(root: Path) -> dict:
    files = []
    for pattern in ("src/**/*.py", "infra/**/*.py", "research/**/*.py", "tests/**/*.py", "prompts/*", "pyproject.toml", "uv.lock"):
        for path in sorted(root.glob(pattern)):
            files.append({"path": str(path.relative_to(root)), "sha256": sha256_bytes(path.read_bytes())})
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    return {"git_commit": git.stdout.strip() if git.returncode == 0 else None,
            "source_files": files, "source_tree_sha256": sha256_bytes(canonical_json(files))}


def _build_inputs(config: AppConfig, snapshots: Path, backend_path: Path, *, smoke: bool = False, mode: str = "pilot", allow_unreviewed: bool = False) -> tuple[dict, tuple, dict, dict]:
    root = config.project_root
    if mode not in {"pilot", "main", "preliminary", "preliminary_pilot", "diagnostic", "engineering_smoke"} or (mode in {"main", "preliminary", "diagnostic", "engineering_smoke"} and smoke):
        raise RunError("Unsupported run mode")
    provisional = mode.startswith("preliminary") or mode == "diagnostic"
    if provisional and not allow_unreviewed:
        raise RunError("Preliminary evaluation requires explicit --allow-unreviewed; references remain draft")
    benchmark = mode in {"main", "preliminary"}
    questions_path = root / ("data/public/main.questions.jsonl" if benchmark else "data/pilot/questions.jsonl")
    gold_path = root / ("data/private/main.gold.jsonl" if benchmark else "data/pilot/gold.jsonl")
    specification_path = root / "data/annotations/specification.json"
    analysis_path = root / "docs/analysis-plan.md"
    instrument, instrument_paths, diagnostic, directories, selected_assignments, selected_validation = None, {}, None, {}, None, None
    pilot_proof, context_proof = None, None
    if config.benchmark_manifest:
        if mode not in {"preliminary", "diagnostic", "main", "engineering_smoke"}:
            raise RunError("Revision-02 remains exploratory; reviewed/legacy pilot routes cannot approve it")
        from ..instrument import read_manifest, validate_instrument
        instrument_path = config.resolve(config.benchmark_manifest)
        validate_instrument(root, instrument_path)
        instrument, instrument_paths = read_manifest(root, instrument_path)
        if instrument.status not in {"frozen_exploratory", "frozen_user_attested"}:
            raise RunError("A conditional draft proposal cannot enter generation; freeze the validated instrument first")
        questions_path, gold_path = instrument_paths["questions"], instrument_paths["gold"]
        if mode in {"main", "engineering_smoke"}:
            if instrument.status != "frozen_user_attested" or not instrument.main_experiment_allowed:
                raise RunError("Versioned main execution requires the researcher's hash-bound review statement")
            from .execution_review import validate_execution_review, load_smoke
            validate_execution_review(root, instrument, instrument_paths)
            if mode == "engineering_smoke":
                _, smoke_paths, _, _, pilot_proof = load_smoke(root, instrument, instrument_paths)
                questions_path, gold_path = smoke_paths["questions"], smoke_paths["gold"]
                pilot_proof = json.loads(smoke_paths["validation_lock"].read_bytes())
                if pilot_proof.get("database_config") != config.database.model_dump(mode="json"):
                    raise RunError("Smoke reference validation uses another database execution policy")
        specification_path, analysis_path = instrument_paths["annotation_specification"], instrument_paths["analysis_protocol"]
        proof = json.loads(instrument_paths["reference_validation_lock"].read_bytes())
        if proof.get("database_config") != config.database.model_dump(mode="json"):
            raise RunError("Reference validation and generation evaluation use different database policies")
        if config.resolve(config.prompt_template) != instrument_paths["prompt_template"]:
            raise RunError("Configured prompt differs from the versioned instrument")
        if mode == "diagnostic":
            if not config.diagnostic_manifest:
                raise RunError("A versioned 180-trial diagnostic manifest is required")
            from .diagnostics import load_diagnostic
            diagnostic, paths, _, _, selected_validation, directories, selected_assignments = load_diagnostic(root, config.resolve(config.diagnostic_manifest), config.experiment)
            if diagnostic.benchmark_manifest.sha256 != sha256_bytes(instrument_path.read_bytes()):
                raise RunError("Diagnostic refers to another frozen benchmark instrument")
            questions_path, gold_path = paths["questions"], paths["gold"]
            pilot_proof = json.loads(paths["semantic_validation_lock"].read_bytes())
            context_proof = json.loads(paths["context_preflight"].read_bytes())
            if pilot_proof.get("database_config") != config.database.model_dump(mode="json"):
                raise RunError("Pilot reference validation and evaluation database policies differ")
    elif mode == "diagnostic":
        raise RunError("Diagnostic mode requires the versioned exploratory instrument")
    elif mode == "engineering_smoke":
        raise RunError("Engineering smoke requires a versioned user-attested instrument")
    questions, references = load_questions(questions_path), load_gold(gold_path)
    expected_column_order = "permutation" if instrument and instrument.result_comparison == "ex-results-v3-column-permutation" else "fixed"
    if any(reference.column_order != expected_column_order for reference in references.values()):
        raise RunError("Loaded references differ from the selected column-order evaluation policy")
    if {q.question_id for q in questions} != references.keys():
        raise DatasetError("Pilot question and reference IDs differ")
    if smoke:
        questions = tuple(q for q in questions if q.question_id == "P001")
        references = {q.question_id: references[q.question_id] for q in questions}
    if mode == "pilot" and any(r.review_status != "approved" for r in references.values()):
        raise RunError("Pilot gold remains draft; human semantic review is required before new scored pilot requests. Backend/context verification can run without generation")
    from ..evaluation.gold import structural_complexity
    if instrument:
        from ..evaluation.structure import profile_sql
        classification = lambda sql: profile_sql(sql).complexity
    else:
        classification = structural_complexity
    if any(classification(references[q.question_id].sql) != q.complexity for q in questions):
        raise DatasetError("Reference SQL no longer matches the declared complexity rubric; revalidate the reviewed dataset")
    assignments = selected_assignments or build_schedule(questions, config.experiment, pilot=not benchmark)
    canonical_validation = validate_scenario_set(snapshots)
    if instrument and json.loads(instrument_paths["metadata_snapshots"].read_bytes())["snapshot_sha256"] != canonical_validation["snapshot_sha256"]:
        raise RunError("Snapshot set differs from the selected instrument")
    validation = selected_validation or canonical_validation
    evidence, backend = load_backend_evidence(backend_path)
    check_live_backend(config.inference, backend)
    if config.inference.model_id != evidence.model_id:
        raise RunError("Inference configuration differs from the verified model")
    if context_proof is not None:
        validate_context_backend(context_proof, evidence, backend, config.inference)
    expected_audit = json.loads((root / "runs/database/baseline.json").read_bytes())
    actual = inspect_database(config)
    verify_fingerprint(actual, expected_audit)
    if instrument:
        validate_reference_database(proof, actual)
    if pilot_proof is not None:
        validate_reference_database(pilot_proof, actual)
    manifest = {"manifest_version": 1, "mode": "pilot_smoke" if smoke else mode, "main_experiment_allowed": mode == "main",
                "evaluation_status": "provisional" if provisional else "reviewed" if mode == "main" else "engineering",
                "allow_unreviewed": provisional and allow_unreviewed, "public_results_embargo": True,
                "annotation_review_status": json.loads(specification_path.read_bytes()).get("status", "unknown"),
                "trial_count": len(assignments), "questions_sha256": sha256_bytes(questions_path.read_bytes()),
                "gold_sha256": sha256_bytes(gold_path.read_bytes()), "gold_review_status": sorted({r.review_status for r in references.values()}),
                "inference_config": config.inference.model_dump(mode="json"), "database_config": config.database.model_dump(mode="json"),
                "fixed_request_parameters": {"min_p": 0.0, "repeat_penalty": 1.0, "cache_prompt": False, "stream": False, "n": 1},
                "experiment_config": config.experiment.model_dump(mode="json"), "python_version": platform.python_version(),
                "package_versions": {name: importlib.metadata.version(name) for name in ("pydantic", "httpx", "pymysql", "sqlglot")},
                "database_schema_sha256": actual["schema_sha256"], "database_data_sha256": actual["data_sha256"],
                "mysql_version": actual["server"]["version"], "backend_evidence_sha256": evidence.verification_artifact_sha256,
                "backend_evidence": backend,
                "sakila_import_manifest_sha256": sha256_bytes((root / "runs/database/import-manifest.json").read_bytes()),
                "datahub_runtime_images_sha256": sha256_bytes((root / "runs/metadata/runtime-images.json").read_bytes()),
                "sampler_verification_sha256": sha256_bytes((backend_path.parent / "sampler-verification.json").read_bytes()) if benchmark and not (instrument and instrument.execution_amendment) else None,
                "sampler_verification_status": "verify_each_main_response_under_user_amendment" if instrument and instrument.execution_amendment else "verified_for_selected_backend" if benchmark else "deferred_until_pilot_completion",
                "model_id": evidence.model_id, "model_version_or_hash": evidence.model_sha256, "backend_revision": evidence.backend_revision,
                "snapshots": validation, "snapshot_manifest_sha256": {s: sha256_bytes(((root / directories[s]) if directories else (snapshots / s)).joinpath("manifest.json").read_bytes()) for s in validation["snapshot_sha256"]},
                "prompt_template_sha256": sha256_bytes(config.resolve(config.prompt_template).read_bytes()),
                "trial_plan_sha256": sha256_bytes(canonical_json([asdict(a) for a in assignments])), "comparator_version": COMPARATOR_VERSION,
                "source_version": source_version(root), "metadata_provenance": [json.loads((snapshots / s / "manifest.json").read_bytes()) for s in ("S0", "S1", "S2", "S3")],
                "analysis_protocol_sha256": sha256_bytes(analysis_path.read_bytes()),
                "note": "Provisional EX against draft references; external annotation pending; results embargoed" if provisional else "Reviewed main experiment" if mode == "main" else "Engineering checks only; draft pilot EX must not be reported as main research results"}
    if instrument:
        manifest.update(instrument_id=instrument.benchmark_id, benchmark_manifest_sha256=sha256_bytes(config.resolve(config.benchmark_manifest).read_bytes()),
                        instrument_paths={key: str(path.relative_to(root)) for key, path in instrument_paths.items()},
                        canonical_snapshots=canonical_validation, comparator_version=instrument.result_comparison,
                        analysis_protocol_id="paired-question-permutation-exact-v2", human_review_status=instrument.human_review_status)
        if instrument.status == "frozen_user_attested":
            from .execution_review import validate_execution_review
            review = validate_execution_review(root, instrument, instrument_paths)
            manifest.update(review_attestation_sha256=instrument.execution_review.sha256,
                            review_attestation=review, reviewer_identity_status=review["reviewer_identity_status"],
                            smoke_manifest_sha256=instrument.smoke_test.sha256 if instrument.smoke_test else None)
            if mode == "main":
                manifest.update(evaluation_status="user_attested_review", gold_file_review_labels=manifest["gold_review_status"],
                                gold_review_status=["user_attested_complete"], annotation_review_status="user_attested_complete",
                                note="Review completion reported by researcher; reviewer names/date not independently documented yet.")
        if benchmark:
            contracts = {row["question_id"]: row for row in map(json.loads, instrument_paths["contracts"].read_bytes().splitlines())}
            manifest["question_attributes"] = _question_attributes(questions, references, contracts)
    if diagnostic:
        manifest.update(diagnostic_manifest_sha256=sha256_bytes(config.resolve(config.diagnostic_manifest).read_bytes()),
                        diagnostic_rendering_directories=directories, diagnostic_repetitions=3,
                        diagnostic_rendering_provenance=[json.loads((root / directory / "manifest.json").read_bytes()) for directory in directories.values()])
    return manifest, assignments, {q.question_id: q for q in questions}, references


def _question_attributes(questions, references, contracts):
    """The loader returns Question objects, while private maps use ID keys."""
    from ..evaluation.structure import profile_sql
    return {q.question_id: {"primary_need": contracts[q.question_id]["primary_need"],
                           "semantic_family": contracts[q.question_id]["semantic_family"],
                           "spider_level": profile_sql(references[q.question_id].sql).spider_level}
            for q in questions}


def validate_reference_database(proof, actual):
    if (any(proof.get("database_" + field) != actual[field] for field in ("schema_sha256", "data_sha256"))
            or proof.get("mysql_version") != actual["server"]["version"]):
        raise RunError("Reference validation and generation evaluation use different frozen database content or server version")


def validate_context_backend(proof, evidence, backend, settings):
    expected = {"model_id": evidence.model_id, "model_sha256": evidence.model_sha256,
                "backend_revision": evidence.backend_revision, "backend_build_info": backend["build_info"],
                "chat_template_sha256": backend["chat_template_sha256"], "context_tokens": settings.context_tokens}
    if any(proof.get(key) != value for key, value in expected.items()):
        raise RunError("Diagnostic tokenizer/context evidence differs from the selected model, backend or template")


def pilot_inputs(config: AppConfig, snapshots: Path, backend_path: Path, *, smoke: bool = False):
    return _build_inputs(config, snapshots, backend_path, smoke=smoke)


def main_inputs(config: AppConfig, snapshots: Path, backend_path: Path, pilot_directory: Path | None):
    if config.benchmark_manifest:
        from ..instrument import read_manifest
        instrument, _ = read_manifest(config.project_root, config.resolve(config.benchmark_manifest))
        if instrument.execution_amendment is not None:
            if pilot_directory is not None:
                raise RunError("Direct main execution cannot claim a matching generation pilot")
            from .direct_main import direct_main_inputs
            inputs = _build_inputs(config, snapshots, backend_path, mode="main")
            direct_main_inputs(config, inputs[0], inputs[2], backend_path)
            return inputs
        return _attested_main_inputs(config, snapshots, backend_path, pilot_directory)
    from .readiness import main_readiness
    readiness = main_readiness(config, snapshots, backend_path, pilot_directory)
    if readiness["status"] != "review_gates_passed":
        raise RunError("Main experiment remains blocked: " + "; ".join(readiness["blockers"]))
    manifest, assignments, questions, references = _build_inputs(config, snapshots, backend_path, mode="main")
    if any(reference.review_status != "approved" for reference in references.values()):
        raise RunError("Every main reference must be semantically approved")
    # Verify all 120 complete main prompts before a frozen main manifest can exist.
    evidence, _ = load_backend_evidence(backend_path)
    budgets = []
    with LlamaClient(config.inference, evidence) as client:
        for question in questions.values():
            for scenario in ("S0", "S1", "S2", "S3"):
                folder = snapshots / scenario
                snapshot = json.loads((folder / "manifest.json").read_bytes())
                prompt = build_prompt(question.generation_input(), json.loads((folder / snapshot["payload_file"]).read_bytes()),
                                      snapshot["snapshot_sha256"], config.project_root / "prompts/generation.txt")
                checked = client.prepare(prompt)
                budgets.append({"question_id": question.question_id, "scenario_id": scenario, "input_tokens": checked.input_tokens,
                                "prompt_sha256": prompt.prompt_sha256})
    manifest.update(review_decisions_sha256=sha256_bytes((config.project_root / "data/reviews/decisions.json").read_bytes()),
                    required_reviews=readiness["required_reviews"], complete_main_prompt_budgets=budgets,
                    verified_pilot_manifest_sha256=sha256_bytes((pilot_directory / "manifest.json").read_bytes()))
    return manifest, assignments, questions, references


def _attested_main_inputs(config, snapshots, backend_path, pilot_directory):
    from ..analysis.report import audit_run
    manifest, assignments, questions, references = _build_inputs(config, snapshots, backend_path, mode="main")
    pilot, records = audit_run(pilot_directory)
    if pilot.get("mode") != "engineering_smoke" or len(records) != 12:
        raise RunError("A complete matching12-request engineering smoke is required")
    from ..instrument import read_manifest
    from .execution_review import load_smoke
    instrument, paths = read_manifest(config.project_root, config.resolve(config.benchmark_manifest))
    _, smoke_paths, smoke_questions, _, _ = load_smoke(config.project_root, instrument, paths)
    expected = {(q.question_id, s, 1) for q in smoke_questions for s in config.experiment.scenario_ids}
    if (pilot.get("questions_sha256") != sha256_bytes(smoke_paths["questions"].read_bytes())
            or pilot.get("gold_sha256") != sha256_bytes(smoke_paths["gold"].read_bytes())
            or {(r["question_id"], r["scenario_id"], r["repetition_id"]) for r in records} != expected):
        raise RunError("Completed smoke differs from the declared separate question/reference plan")
    for key in ("model_version_or_hash", "backend_evidence_sha256", "inference_config", "prompt_template_sha256",
                "database_schema_sha256", "database_data_sha256", "source_version", "benchmark_manifest_sha256",
                "canonical_snapshots", "smoke_manifest_sha256", "comparator_version", "review_attestation_sha256",
                "database_config", "fixed_request_parameters", "snapshot_manifest_sha256"):
        if pilot.get(key) != manifest.get(key):
            raise RunError("Smoke/main input or source mismatch: " + key)
    sampler_path = backend_path.parent / "sampler-verification.json"
    sampler = json.loads(sampler_path.read_bytes())
    if (sampler.get("status") != "sampler_seed_cache_verified" or sampler.get("model_sha256") != manifest["model_version_or_hash"]
            or sampler.get("backend_evidence_sha256") != manifest["backend_evidence_sha256"]
            or sampler.get("pilot_manifest_sha256") != sha256_bytes((pilot_directory / "manifest.json").read_bytes())):
        raise RunError("Sampler evidence does not match this smoke and backend")
    manifest.update(complete_main_prompt_budgets=_prompt_budgets(config, backend_path, questions, snapshots),
                    verified_pilot_manifest_sha256=sha256_bytes((pilot_directory / "manifest.json").read_bytes()))
    return manifest, assignments, questions, references


def preliminary_inputs(config, snapshots, backend_path, pilot_directory, *, allow_unreviewed):
    from ..analysis.report import audit_run
    manifest, assignments, questions, references = _build_inputs(config, snapshots, backend_path, mode="preliminary", allow_unreviewed=allow_unreviewed)
    pilot, records = audit_run(pilot_directory)
    if config.benchmark_manifest:
        if pilot.get("mode") != "diagnostic" or len(records) != 180:
            raise RunError("Revision-02 requires its complete audited 180-trial diagnostic")
        for key in ("model_version_or_hash", "backend_evidence_sha256", "inference_config", "prompt_template_sha256", "database_schema_sha256", "database_data_sha256", "source_version", "benchmark_manifest_sha256", "canonical_snapshots"):
            if pilot.get(key) != manifest.get(key):
                raise RunError("Diagnostic/benchmark input or source mismatch: " + key)
        if pilot.get("diagnostic_manifest_sha256") != sha256_bytes(config.resolve(config.diagnostic_manifest).read_bytes()):
            raise RunError("Diagnostic inputs changed after the diagnostic run")
    else:
        _check_legacy_preliminary_pilot(config, manifest, pilot, records)
    sampler = json.loads((backend_path.parent / "sampler-verification.json").read_bytes())
    if (sampler.get("status") != "sampler_seed_cache_verified" or sampler.get("model_sha256") != manifest["model_version_or_hash"]
            or sampler.get("backend_evidence_sha256") != manifest["backend_evidence_sha256"]
            or sampler.get("pilot_manifest_sha256") != sha256_bytes((pilot_directory / "manifest.json").read_bytes())):
        raise RunError("Sampler proof does not match the preliminary pilot and backend")
    manifest.update(complete_main_prompt_budgets=_prompt_budgets(config, backend_path, questions, snapshots),
                    verified_pilot_manifest_sha256=sha256_bytes((pilot_directory / "manifest.json").read_bytes()))
    return manifest, assignments, questions, references


def _check_legacy_preliminary_pilot(config, manifest, pilot, records):
    if pilot.get("mode") != "preliminary_pilot" or len(records) != 36:
        raise RunError("A complete audited preliminary pilot is required")
    expected = {(q.question_id, s, 1) for q in load_questions(config.project_root / "data/pilot/questions.jsonl") for s in config.experiment.scenario_ids}
    if {(r["question_id"], r["scenario_id"], r["repetition_id"]) for r in records} != expected:
        raise RunError("Pilot assignments differ from the fixed pilot dataset")
    for key in ("model_version_or_hash", "backend_evidence_sha256", "inference_config", "prompt_template_sha256", "snapshot_manifest_sha256", "database_schema_sha256", "database_data_sha256", "source_version"):
        if pilot[key] != manifest[key]:
            raise RunError("Pilot/main input or source mismatch: " + key)
    if pilot["gold_sha256"] != sha256_bytes((config.project_root / "data/pilot/gold.jsonl").read_bytes()):
        raise RunError("Pilot reference version changed")
    if pilot["questions_sha256"] != sha256_bytes((config.project_root / "data/pilot/questions.jsonl").read_bytes()):
        raise RunError("Pilot questions changed")


def _prompt_budgets(config, backend_path, questions, snapshots, directories=None):
    evidence, _ = load_backend_evidence(backend_path)
    budgets = []
    with LlamaClient(config.inference, evidence) as client:
        for q in questions.values():
            for s in (directories or config.experiment.scenario_ids):
                folder = config.project_root / directories[s] if directories else snapshots / s
                snapshot = json.loads((folder / "manifest.json").read_bytes())
                prompt = build_prompt(q.generation_input(), json.loads((folder / snapshot["payload_file"]).read_bytes()), snapshot["snapshot_sha256"], config.resolve(config.prompt_template))
                checked = client.prepare(prompt)
                budgets.append({"question_id": q.question_id, "scenario_id": s, "input_tokens": checked.input_tokens, "prompt_sha256": prompt.prompt_sha256})
    return budgets


def evaluate_response(config, tables, response: GenerationResponse, reference, gold_execution):
    if response.infrastructure_error:
        raise RunError(response.infrastructure_error)
    common = {"raw_llm_response": response.raw_response, "raw_model_text": response.text,
              "column_order_policy": reference.column_order, "column_permutation": None,
              "inference_latency_ms": response.inference_latency_ms, "input_tokens": response.input_tokens,
              "output_tokens": response.output_tokens, "token_usage_source": response.token_usage_source,
              "model_response_valid": response.response_valid, "finish_reason": response.finish_reason,
              "resolved_request_parameters": response.request_parameters,
              "gold_result_hash": gold_execution.result_sha256, "extracted_sql": None, "execution_result_hash": None,
              "sql_execution_latency_ms": None, "error_type": None, "error_message": None}
    common["execution_error_code"] = None
    # Formatting cleanup has no semantic rewrite. Rejected raw outputs stay durable.
    extracted = extract_sql(response.text or "")
    if not response.response_valid or not extracted:
        return {**common, "validation_status": "invalid_model_output", "execution_status": "not_executed",
                "error_type": "model_output", "execution_accuracy": 0}, None
    common["extracted_sql"] = extracted
    execution = execute_sql(config, extracted, tables)
    if execution.status == "infrastructure_error":
        raise RunError("sql_execution_infrastructure_error")
    common.update(validation_status=execution.validation_code, execution_status=execution.status,
                  sql_execution_latency_ms=execution.latency_ms, execution_result_hash=execution.result_sha256,
                  error_type="sql_model_error" if execution.status != "success" else None,
                  error_message=execution.error_message, execution_error_code=execution.error_code)
    if execution.status != "success":
        return {**common, "execution_accuracy": 0}, None
    comparison = compare_results(execution.result, gold_execution.result,
                                 comparison_spec(reference))
    return {**common, "execution_accuracy": comparison.execution_accuracy, "comparison_reason": comparison.reason,
            "column_order_policy": reference.column_order, "column_permutation": comparison.column_permutation}, execution.result


def _run(config: AppConfig, snapshots: Path, backend_path: Path, directory: Path, experiment_id: str,
         *, smoke: bool = False, dry_run: bool = False, mode: str = "pilot", pilot_directory: Path | None = None,
         freeze_only: bool = False, allow_unreviewed: bool = False, progress=print,
         candidate_manifest: Path | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", experiment_id):
        raise RunError("Experiment ID is not a safe identifier")
    if mode == "candidate_pilot":
        from .candidate_pilot import candidate_inputs
        if candidate_manifest is None or smoke or config.benchmark_manifest or config.diagnostic_manifest:
            raise RunError("Candidate pilot requires its separate manifest, never a main instrument")
        manifest, assignments, questions, references = candidate_inputs(config, snapshots, backend_path, candidate_manifest)
        if not freeze_only and not (directory / "freeze.json").is_file():
            raise RunError("Freeze the separate capability pilot before generation")
    elif mode == "main":
        if pilot_directory is None:
            from ..instrument import read_manifest
            if not config.benchmark_manifest or read_manifest(config.project_root, config.resolve(config.benchmark_manifest))[0].execution_amendment is None:
                raise RunError("A verified complete pilot or explicit user-authorized execution amendment is required")
        manifest, assignments, questions, references = main_inputs(config, snapshots, backend_path, pilot_directory)
        if not freeze_only and not (directory / "freeze.json").is_file():
            raise RunError("Freeze and review the concrete main manifest before running main trials")
    elif mode == "preliminary":
        if pilot_directory is None:
            raise RunError("Preliminary pilot evidence is required")
        manifest, assignments, questions, references = preliminary_inputs(config, snapshots, backend_path, pilot_directory, allow_unreviewed=allow_unreviewed)
        if not freeze_only and not (directory / "freeze.json").is_file():
            raise RunError("Freeze preliminary inputs before generation")
    elif mode == "diagnostic":
        manifest, assignments, questions, references = _build_inputs(config, snapshots, backend_path, mode=mode, allow_unreviewed=allow_unreviewed)
        manifest["complete_diagnostic_prompt_budgets"] = _prompt_budgets(config, backend_path, questions, snapshots, manifest["diagnostic_rendering_directories"])
        if not freeze_only and not (directory / "freeze.json").is_file():
            raise RunError("Freeze all 60 diagnostic prompts and references before generation")
    elif mode == "engineering_smoke":
        manifest, assignments, questions, references = _build_inputs(config, snapshots, backend_path, mode=mode)
        manifest["complete_smoke_prompt_budgets"] = _prompt_budgets(config, backend_path, questions, snapshots)
        if not freeze_only and not (directory / "freeze.json").is_file():
            raise RunError("Freeze the separate smoke inputs before generation")
    elif mode == "preliminary_pilot":
        manifest, assignments, questions, references = _build_inputs(config, snapshots, backend_path, mode=mode, allow_unreviewed=allow_unreviewed)
    else:
        manifest, assignments, questions, references = pilot_inputs(config, snapshots, backend_path, smoke=smoke)
    manifest["experiment_id"] = experiment_id
    publish_artifact(directory / "manifest.json", canonical_json(manifest))
    publish_artifact(directory / "plan.json", canonical_json([asdict(a) for a in assignments]))
    if mode in {"main", "preliminary", "diagnostic", "engineering_smoke", "candidate_pilot"} and not freeze_only:
        freeze = json.loads((directory / "freeze.json").read_bytes())
        expected_status = mode + "_manifest_frozen"
        if freeze.get("status") != expected_status or freeze.get("manifest_sha256") != sha256_bytes(canonical_json(manifest)):
            raise RunError("Main freeze receipt differs from the current verified manifest")
    if dry_run:
        return {"status": "dry_run", "trial_count": len(assignments), "generation_requests": 0, "mode": manifest["mode"]}
    evidence, backend = load_backend_evidence(backend_path)
    tables = frozenset(t["name"] for t in json.loads((config.project_root / "runs/database/baseline.json").read_bytes())["technical_schema"]["tables"])
    gold_executions = {}
    # Gold is owned only by the evaluator. It never enters build_prompt or LlamaClient.
    for question_id, reference in references.items():
        execution = execute_sql(config, reference.sql, tables)
        if execution.status != "success":
            raise RunError("Reference SQL preflight failed: " + question_id)
        spec = comparison_spec(reference)
        if compare_results(execution.result, execution.result, spec).execution_accuracy != 1:
            raise RunError("Reference SQL column/result contract failed")
        publish_artifact(directory / "gold-results" / f"{question_id}.json", canonical_json(execution.result.encoded()))
        gold_executions[question_id] = execution
    if freeze_only:
        receipt = {"status": mode + "_manifest_frozen", "trial_count": len(assignments), "generation_requests": 0,
                   "manifest_sha256": sha256_bytes(canonical_json(manifest)),
                   "validated_gold_results": {q: e.result_sha256 for q, e in gold_executions.items()}}
        publish_artifact(directory / "freeze.json", canonical_json(receipt))
        return receipt
    with Ledger(directory / "ledger.sqlite3") as ledger, LlamaClient(config.inference, evidence) as client:
        ledger.register(experiment_id, manifest, assignments)
        completed = ledger.completed(experiment_id)
        for assignment in assignments:
            if assignment.trial_id in completed:
                continue
            directories = manifest.get("diagnostic_rendering_directories")
            folder = config.project_root / directories[assignment.scenario_id] if directories else snapshots / assignment.scenario_id
            snapshot_bytes = (folder / "manifest.json").read_bytes()
            if sha256_bytes(snapshot_bytes) != manifest["snapshot_manifest_sha256"][assignment.scenario_id]:
                raise RunError("Snapshot manifest changed during the run")
            snapshot = json.loads(snapshot_bytes)
            payload = json.loads((folder / snapshot["payload_file"]).read_bytes())
            prompt = build_prompt(questions[assignment.question_id].generation_input(), payload, snapshot["snapshot_sha256"], config.resolve(config.prompt_template))
            if prompt.template_sha256 != manifest["prompt_template_sha256"]:
                raise RunError("Prompt template changed during the run")
            prompt_path = directory / "prompts" / f"{prompt.prompt_sha256}.json"
            publish_artifact(prompt_path, canonical_json(prompt.chat_messages()))
            stored = ledger.latest_response(experiment_id, assignment.trial_id)
            attempt = None
            try:
                if stored:
                    attempt, stored_payload = stored
                    if stored_payload["prompt_hash"] != prompt.prompt_sha256:
                        raise RunError("Stored response prompt does not match frozen inputs")
                    response = GenerationResponse(**stored_payload["generation_response"])
                else:
                    attempt = ledger.start_attempt(experiment_id, assignment.trial_id)
                    checked = client.prepare(prompt)  # Overflow never dispatches generation.
                    response = client.generate(checked, assignment.inference_seed)
                    ledger.record_response(experiment_id, assignment.trial_id, attempt,
                                           {"prompt_hash": prompt.prompt_sha256, "generation_response": asdict(response), "checked_input_tokens": checked.input_tokens})
                outcome, result = evaluate_response(config, tables, response, references[assignment.question_id], gold_executions[assignment.question_id])
                if result is not None:
                    publish_artifact(directory / "results" / f"{assignment.trial_id}.json", canonical_json(result.encoded()))
                outcome.update(asdict(assignment))
                outcome.update(timestamp=datetime.now(timezone.utc).isoformat(), model_id=evidence.model_id,
                               evaluation_status=manifest.get("evaluation_status", "engineering"), reference_review_status=references[assignment.question_id].review_status,
                               model_version_or_hash=evidence.model_sha256, inference_config=config.inference.model_dump(mode="json"),
                               snapshot_id=snapshot["snapshot_id"], snapshot_sha256=snapshot["snapshot_sha256"],
                               prompt_hash=prompt.prompt_sha256, raw_prompt_or_reproducible_prompt_reference=str(prompt_path.resolve()))
                if manifest.get("evaluation_status") == "user_attested_review":
                    outcome.update(reference_file_label=outcome["reference_review_status"], reference_review_status="user_attested_complete")
                ledger.finish_trial(experiment_id, assignment.trial_id, attempt, outcome)
            except (LLMServiceError, RunError, EvaluationError) as error:
                if attempt is not None:
                    ledger.record_infrastructure_failure(experiment_id, assignment.trial_id, attempt,
                                                         {"error_type": type(error).__name__, "error_message": str(error), "raw_backend_response": getattr(error, "raw_response", None),
                                                          "stored_response_preserved": ledger.latest_response(experiment_id, assignment.trial_id) is not None})
                # Stop, never silently generate again. Resume requires an explicit rerun.
                raise RunError("Pilot interrupted by infrastructure/evaluation issue: " + str(error)) from None
            # A post-completion observer must not relabel a durable model outcome
            # as an infrastructure failure or cause that response to regenerate.
            progress(canonical_json({"trial_id": assignment.trial_id, "status": "completed", "execution_accuracy": outcome["execution_accuracy"]}).decode().strip())
        final_audit = inspect_database(config)
        baseline = json.loads((config.project_root / "runs/database/baseline.json").read_bytes())
        verify_fingerprint(final_audit, baseline)
        results = ledger.completed(experiment_id)
        if set(results) != {a.trial_id for a in assignments}:
            raise RunError("Completed trials do not match the fixed assignment plan")
        ledger.export_jsonl(experiment_id, directory / "events.jsonl")
        publish_artifact(directory / "trials.jsonl", b"".join(canonical_json(results[a.trial_id]) for a in assignments))
        report = {"status": "preliminary_complete" if mode.startswith("preliminary") else mode + "_complete" if mode in {"main", "diagnostic"} else "pilot_complete", "experiment_id": experiment_id, "mode": manifest["mode"],
                  "completed_trials": len(results), "main_experiment_allowed": mode == "main",
                  "database_unchanged": True, "manifest_sha256": sha256_bytes(canonical_json(manifest))}
        publish_artifact(directory / "completion.json", canonical_json(report))
        return report


def run_pilot(config: AppConfig, snapshots: Path, backend_path: Path, directory: Path, experiment_id: str,
              *, smoke: bool = False, dry_run: bool = False, progress=print) -> dict:
    return _run(config, snapshots, backend_path, directory, experiment_id, smoke=smoke, dry_run=dry_run, progress=progress)


def run_main(config: AppConfig, snapshots: Path, backend_path: Path, directory: Path, experiment_id: str,
             pilot_directory: Path | None, *, freeze_only: bool = False, progress=print) -> dict:
    return _run(config, snapshots, backend_path, directory, experiment_id, mode="main", pilot_directory=pilot_directory,
                freeze_only=freeze_only, progress=progress)


def run_preliminary(config, snapshots, backend_path, directory, experiment_id, *, pilot_directory=None, pilot=False, freeze_only=False, allow_unreviewed=False, progress=print):
    return _run(config, snapshots, backend_path, directory, experiment_id, mode="preliminary_pilot" if pilot else "preliminary",
                pilot_directory=pilot_directory, freeze_only=freeze_only, allow_unreviewed=allow_unreviewed, progress=progress)


def run_diagnostic(config, snapshots, backend_path, directory, experiment_id, *, freeze_only=False, allow_unreviewed=False, progress=print):
    return _run(config, snapshots, backend_path, directory, experiment_id, mode="diagnostic",
                freeze_only=freeze_only, allow_unreviewed=allow_unreviewed, progress=progress)


def run_engineering_smoke(config, snapshots, backend_path, directory, experiment_id, *, freeze_only=False, progress=print):
    return _run(config, snapshots, backend_path, directory, experiment_id, mode="engineering_smoke",
                freeze_only=freeze_only, progress=progress)


def run_candidate_pilot(config, snapshots, backend_path, directory, experiment_id, candidate_manifest,
                        *, freeze_only=False, progress=print):
    """Separate, explicitly draft-reference model feasibility evidence; never main approval."""
    return _run(config, snapshots, backend_path, directory, experiment_id, mode="candidate_pilot",
                candidate_manifest=candidate_manifest, freeze_only=freeze_only, progress=progress)
