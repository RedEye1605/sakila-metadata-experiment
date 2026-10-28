"""Hash-bound, versioned research inputs; private contracts never enter inference."""

from __future__ import annotations

import json
import importlib.metadata
import platform
import re
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .artifacts import canonical_json, publish_artifact, sha256_bytes
from .config import StrictModel
from .contracts import DatasetError, load_gold, load_questions
from .evaluation.structure import RUBRIC_VERSION, profile_sql

SCENARIOS = ("S0", "S1", "S2", "S3")
NEEDS = ("schema_mapping", "local_semantics", "domain_integration")
STRUCTURAL_LEVELS = ("simple", "medium", "complex")
# A01: source feasibility, approved before generation. Never force domain
# knowledge into trivial tasks to fill the original crossed-cell proposal.
DOMAIN_ALLOCATION = {"simple": 0, "medium": 2, "complex": 4}
REFERENCE_VALIDATION_SOURCES = (
    "research/revision-02/validate_references.py", "research/revision-02/mutations.py",
    "src/sakila_experiment/evaluation/compare.py", "src/sakila_experiment/evaluation/safety.py",
    "src/sakila_experiment/evaluation/fixtures.py", "src/sakila_experiment/db/execute.py",
    "src/sakila_experiment/db/values.py", "src/sakila_experiment/db/connection.py", "src/sakila_experiment/config.py",
    "src/sakila_experiment/bootstrap.py", "src/sakila_experiment/db/inspect.py",
    "src/sakila_experiment/artifacts.py", "src/sakila_experiment/contracts.py",
)
REFERENCE_VALIDATION_PACKAGES = ("pydantic", "pymysql", "sqlglot")


def validate_reference_code(root: Path, proof: dict) -> None:
    hashes = proof.get("implementation_sha256", {})
    if set(hashes) != set(REFERENCE_VALIDATION_SOURCES) or any(sha256_bytes((root / relative).read_bytes()) != digest for relative, digest in hashes.items()):
        raise DatasetError("Reference validation implementation changed or lacks its complete source lock")
    expected = {name: importlib.metadata.version(name) for name in REFERENCE_VALIDATION_PACKAGES}
    if proof.get("package_versions") != expected or proof.get("python_version") != platform.python_version():
        raise DatasetError("Reference validation runtime versions differ from the current evaluator")


class ArtifactReference(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    def verified_path(self, root: Path) -> Path:
        path = (root / self.path).resolve()
        if Path(self.path).is_absolute() or not path.is_relative_to(root.resolve()):
            raise DatasetError("Instrument artifact path escapes the project")
        try:
            content = path.read_bytes()
        except OSError:
            raise DatasetError("An instrument artifact is unavailable") from None
        if sha256_bytes(content) != self.sha256:
            raise DatasetError("An instrument artifact changed after manifest creation")
        return path


class SemanticContract(StrictModel):
    question_id: str = Field(pattern=r"^[QP][0-9]{3}$")
    analytic_purpose: str = Field(min_length=20)
    primary_need: Literal["schema_mapping", "local_semantics", "domain_integration"]
    semantic_family: str = Field(min_length=5)
    capabilities: tuple[str, ...] = Field(min_length=1)
    grain: str = Field(min_length=5)
    population: str = Field(min_length=5)
    measure: str = Field(min_length=5)
    role_attribution: str = Field(min_length=3)
    units: str = Field(min_length=3)
    time_scope: str = Field(min_length=3)
    zero_and_null_policy: str = Field(min_length=5)
    duplicate_policy: str = Field(min_length=5)
    ordering_and_ties: str = Field(min_length=5)
    output_columns: tuple[str, ...] = Field(min_length=1)
    numeric_policy: str = Field(min_length=5)
    required_fact_ids: tuple[str, ...] = Field(min_length=1)
    fact_availability: dict[str, dict[str, Literal["explicit", "derivable", "absent"]]]
    source_urls: tuple[str, ...] = Field(min_length=1)
    plausible_wrong_variants: tuple[str, ...] = Field(min_length=1)
    review_notes: tuple[str, ...] = ()
    independent_review_artifacts: tuple[ArtifactReference, ...] = ()
    construction_status: Literal["draft", "ai_checked"] = "draft"
    human_review_status: Literal["pending"] = "pending"

    @model_validator(mode="after")
    def complete_information_contract(self):
        if len(set(self.required_fact_ids)) != len(self.required_fact_ids):
            raise ValueError("Required facts must be unique")
        if set(self.fact_availability) != set(self.required_fact_ids):
            raise ValueError("Every required fact needs an availability assessment")
        if any(set(arms) != set(SCENARIOS) for arms in self.fact_availability.values()):
            raise ValueError("Availability must cover exactly S0-S3")
        if not all(url.startswith("https://dev.mysql.com/doc/") for url in self.source_urls):
            raise ValueError("Core Sakila contracts require official MySQL sources")
        return self


class BenchmarkManifest(StrictModel):
    manifest_version: Literal[2] = 2
    benchmark_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    estimand: Literal["metadata-package-domain-information-availability"]
    status: Literal["draft", "frozen_exploratory", "frozen_user_attested"] = "draft"
    main_experiment_allowed: bool = False
    rubric_version: Literal["spider-components-mysql-v2"] = RUBRIC_VERSION
    result_comparison: Literal["ex-results-v2-column-contracts", "ex-results-v3-column-permutation"] = "ex-results-v2-column-contracts"
    questions: ArtifactReference
    gold: ArtifactReference
    contracts: ArtifactReference
    annotation_specification: ArtifactReference
    fact_inventory: ArtifactReference
    analysis_protocol: ArtifactReference
    evaluation_protocol: ArtifactReference
    source_lock: ArtifactReference
    selection_receipt: ArtifactReference
    prompt_template: ArtifactReference
    information_audit: ArtifactReference
    metadata_snapshots: ArtifactReference
    reference_validation: ArtifactReference
    reference_validation_lock: ArtifactReference
    fixture_specification: ArtifactReference
    human_review_status: Literal["pending", "user_attested_complete"] = "pending"
    execution_review: ArtifactReference | None = None
    smoke_test: ArtifactReference | None = None

    @model_validator(mode="after")
    def review_state(self):
        if self.status == "frozen_user_attested":
            if (not self.main_experiment_allowed or self.human_review_status != "user_attested_complete"
                    or self.execution_review is None or self.smoke_test is None):
                raise ValueError("User-attested execution needs its review and separate smoke evidence")
        elif self.main_experiment_allowed or self.human_review_status != "pending" or self.execution_review is not None:
            raise ValueError("main_experiment_allowed requires a hash-bound user review statement")
        return self

    def paths(self, root: Path) -> dict[str, Path]:
        paths = {name: getattr(self, name).verified_path(root) for name in (
            "questions", "gold", "contracts", "annotation_specification", "fact_inventory",
            "analysis_protocol", "evaluation_protocol", "source_lock", "selection_receipt", "prompt_template", "information_audit", "metadata_snapshots", "reference_validation", "reference_validation_lock", "fixture_specification")}
        for name in ("execution_review", "smoke_test"):
            if getattr(self, name) is not None:
                paths[name] = getattr(self, name).verified_path(root)
        return paths


def read_manifest(root: Path, path: Path) -> tuple[BenchmarkManifest, dict[str, Path]]:
    manifest = BenchmarkManifest.model_validate_json(path.read_bytes())
    return manifest, manifest.paths(root)


def validate_permutation_witnesses(summary_path: Path, lock_path: Path, checks: dict, mutants: dict, identifiers: set[str]):
    """Reconstruct declared witnesses from hash-bound per-case evidence."""
    lock_sha = sha256_bytes(lock_path.read_bytes())
    if checks.get("input_lock_sha256") != lock_sha:
        raise DatasetError("Reference summary belongs to another input lock")
    cases = checks["cases"]
    digests = checks.get("case_evidence_sha256", {})
    if set(digests) != set(cases) or set(mutants) != identifiers:
        raise DatasetError("Reference case or declared-mutant coverage differs")
    declared = {qid: [m["mutation_id"] for m in values] for qid, values in mutants.items()}
    if any(not values or len(set(values)) != len(values) for values in declared.values()):
        raise DatasetError("Declared mutant IDs must be present and unique")
    records = {r["question_id"]: r for r in checks["records"]}
    if len(records) != len(checks["records"]) or set(records) != identifiers:
        raise DatasetError("Reference summary IDs are duplicated or incomplete")
    observed = {qid: {mid: [] for mid in mids} for qid, mids in declared.items()}
    for case in cases:
        path = summary_path.parent / case / "comparisons.json"
        if not path.is_file() or sha256_bytes(path.read_bytes()) != digests[case]:
            raise DatasetError("Reference per-case evidence hash differs")
        rows = json.loads(path.read_bytes())
        by_id = {r["question_id"]: r for r in rows}
        if len(by_id) != len(rows) or set(by_id) != identifiers:
            raise DatasetError("Reference per-case IDs are duplicated or incomplete")
        for qid, row in by_id.items():
            if (row.get("input_lock_sha256") != lock_sha or row.get("fixture_id") != case
                    or row.get("reference_agreement") is not True
                    or row.get("author_a_status") != "success" or row.get("author_b_status") != "success"):
                raise DatasetError("Reference per-case execution does not match the locked proof")
            results = {r["mutation_id"]: r for r in row["mutations"]}
            if len(results) != len(row["mutations"]) or set(results) != set(declared[qid]):
                raise DatasetError("Reference per-case mutant IDs differ from the declared set")
            for mid, result in results.items():
                if result.get("semantic_difference_observed") is True:
                    if result.get("execution_status") != "success":
                        raise DatasetError("A failed mutant cannot establish a semantic witness")
                    observed[qid][mid].append(case)
    for qid, record in records.items():
        witnesses = record.get("witnesses", {})
        if set(witnesses) != set(declared[qid]):
            raise DatasetError("Reference witness IDs differ from the predeclared mutants")
        for mid, values in witnesses.items():
            if (not isinstance(values, list) or not values or any(not isinstance(v, str) for v in values)
                    or len(values) != len(set(values)) or set(values) != set(observed[qid][mid])):
                raise DatasetError("Reference witnesses do not match actual declared case evidence")


def validate_instrument(root: Path, manifest_path: Path, output: Path | None = None) -> dict:
    manifest, paths = read_manifest(root, manifest_path)
    questions, gold = load_questions(paths["questions"]), load_gold(paths["gold"])
    contracts = [SemanticContract.model_validate_json(line) for line in paths["contracts"].read_bytes().splitlines() if line.strip()]
    ids = {q.question_id for q in questions}
    if ids != gold.keys() or ids != {c.question_id for c in contracts} or len(contracts) != len(ids):
        raise DatasetError("Question, gold and semantic-contract IDs must agree without duplicates")
    expected_column_order = "permutation" if manifest.result_comparison == "ex-results-v3-column-permutation" else "fixed"
    if any(reference.column_order != expected_column_order for reference in gold.values()):
        raise DatasetError("Gold column-order policy differs from the versioned evaluator")
    if len(ids) != 30 or Counter(q.complexity for q in questions) != {label: 10 for label in STRUCTURAL_LEVELS}:
        raise DatasetError("Revised benchmark requires 30 questions, ten per complexity")
    if any(not q.question_id.startswith("Q") for q in questions):
        raise DatasetError("Benchmark questions must have Q-prefixed IDs")
    selection = json.loads(paths["selection_receipt"].read_bytes())
    if set(selection.get("selected_question_ids", [])) != ids or selection.get("generation_requests") != 0:
        raise DatasetError("Selection receipt does not bind the prospective selected questions")
    if expected_column_order == "permutation":
        for question in questions:
            if re.search(r"\b(?:keluaran|select|join|having|limit)\b|\b(?:group|order)\s+by\b|[a-z]+_[a-z]+", question.question, re.IGNORECASE):
                raise DatasetError("Natural question contains an output footer or technical SQL/schema hint")
        profiles = [profile_sql(gold[q.question_id].sql) for q in questions]
        if (sum(bool(p.features["order"]) for p in profiles) < 3
                or sum(bool(p.features["limit"]) for p in profiles) < 2):
            raise DatasetError("Revised coverage requires three ordered tasks including two top-k tasks")
        if any(bool(p.features["order"]) != gold[q.question_id].ordered for q, p in zip(questions, profiles, strict=True)):
            raise DatasetError("Ordered-result contracts disagree with the declared ranking tasks")
    candidates = {name: ArtifactReference.model_validate(reference).verified_path(root) for name, reference in selection["candidates"].items()}
    candidate_questions, candidate_gold = {q.question_id: q for q in load_questions(candidates["questions"])}, load_gold(candidates["gold"])
    if any(q != candidate_questions.get(q.question_id) or gold[q.question_id] != candidate_gold.get(q.question_id) for q in questions):
        raise DatasetError("Selected question/reference differs from its validated candidate version")
    reference_lock = json.loads(paths["reference_validation_lock"].read_bytes())
    if expected_column_order == "permutation":
        mutant = ArtifactReference.model_validate(selection.get("mutations", {}))
        mutant.verified_path(root)
        if reference_lock.get("mutations_artifact") != mutant.model_dump(mode="json"):
            raise DatasetError("Reference witnesses differ from the predeclared semantic mutants")
    if reference_lock["gold_a_sha256"] != sha256_bytes(candidates["gold"].read_bytes()) or reference_lock["questions_sha256"] != sha256_bytes(candidates["questions"].read_bytes()):
        raise DatasetError("Reference execution evidence belongs to another candidate version")
    if reference_lock["fixture_definition_sha256"] != sha256_bytes(paths["fixture_specification"].read_bytes()):
        raise DatasetError("Reference fixture validation belongs to another fixture definition")
    for reference in reference_lock["gold_b_files"]:
        ArtifactReference.model_validate(reference).verified_path(root)
    reference_checks = json.loads(paths["reference_validation"].read_bytes())
    checked = {r["question_id"]: r for r in reference_checks["records"]}
    fixture_ids = [case["fixture_id"] for case in json.loads(paths["fixture_specification"].read_bytes())["cases"]]
    if (len(reference_checks["cases"]) != 9 or set(reference_checks["cases"]) != {"baseline", *fixture_ids}
            or reference_checks.get("primary_database_unchanged") is not True):
        raise DatasetError("Complete baseline plus8fixture reference evidence is required")
    if expected_column_order == "permutation":
        validate_permutation_witnesses(paths["reference_validation"], paths["reference_validation_lock"],
                                       reference_checks, json.loads(mutant.verified_path(root).read_bytes()), set(candidate_questions))
    for qid in ids:
        record = checked.get(qid, {})
        if not all(record.get(key) is True for key in ("reference_agreement_all_checked", "reference_execution_valid", "all_predeclared_mutants_distinguished")):
            raise DatasetError("Selected reference or distinguishing witnesses did not pass: " + qid)
        if not record.get("witnesses") or any(not cases for cases in record["witnesses"].values()):
            raise DatasetError("Selected question has an unobserved critical semantic witness")
    information = json.loads(paths["information_audit"].read_bytes())
    snapshot_checks = json.loads(paths["metadata_snapshots"].read_bytes())
    if information.get("status") != "complete_independent_AI_review" or information.get("human_review_complete") is not False:
        raise DatasetError("An incomplete AI audit cannot satisfy the independent information gate")
    if information.get("prompt_template_sha256") != sha256_bytes(paths["prompt_template"].read_bytes()) or information.get("snapshot_sha256") != snapshot_checks["snapshot_sha256"]:
        raise DatasetError("Independent information audit belongs to another model input")
    question_packet = b"".join(canonical_json({"question_id": q.question_id, "question": q.question}) for q in candidate_questions.values())
    if information.get("question_packet_sha256") != sha256_bytes(question_packet):
        raise DatasetError("Independent information audit belongs to another natural-question packet")
    assessed = {r["question_id"]: r for r in information["question_assessments"]}
    if len(assessed) != len(information["question_assessments"]) or set(assessed) != candidate_questions.keys():
        raise DatasetError("Independent information assessment coverage is duplicated or incomplete")
    if any(assessed.get(qid, {}).get("material_residual_ambiguity") is not False for qid in ids):
        raise DatasetError("A selected question still lacks independently checked S3 disambiguation")
    validate_reference_code(root, reference_lock)
    by_id = {contract.question_id: contract for contract in contracts}
    cells = Counter((q.complexity, by_id[q.question_id].primary_need) for q in questions)
    if any(cells[(level, "domain_integration")] != DOMAIN_ALLOCATION[level] for level in STRUCTURAL_LEVELS):
        raise DatasetError("Domain allocation must match the source-feasible prospective amendment")
    inventory = json.loads(paths["fact_inventory"].read_bytes())
    facts = {fact["fact_id"]: fact for fact in inventory["facts"]}
    if len(facts) != len(inventory["facts"]):
        raise DatasetError("Duplicate fact identity")
    profiles = []
    for question in questions:
        reference, contract = gold[question.question_id], by_id[question.question_id]
        if manifest.status in {"frozen_exploratory", "frozen_user_attested"} and not contract.independent_review_artifacts:
            raise DatasetError("Frozen private contracts require their independent interpretation source")
        for artifact in contract.independent_review_artifacts:
            records = [json.loads(line) for line in artifact.verified_path(root).read_bytes().splitlines() if line.strip()]
            rows = [row for row in records if row["question_id"] == question.question_id]
            if (len(rows) != 1 or rows[0]["question"] != question.question
                    or (contract.grain, contract.population, contract.measure) != (rows[0]["grain"], rows[0]["population"], rows[0]["intent"])):
                raise DatasetError("Private contract no longer matches the independent interpretation")
        profile = profile_sql(reference.sql)
        if profile.complexity != question.complexity:
            raise DatasetError(f"{question.question_id}: canonical SQL differs from its frozen complexity")
        if reference.review_status != "draft" or len(contract.output_columns) != reference.column_count:
            raise DatasetError("Exploratory gold must remain draft and match its output contract")
        if not set(contract.required_fact_ids) <= facts.keys():
            raise DatasetError("A required domain fact is absent from the source inventory")
        if contract.primary_need == "domain_integration" and not any(
            fact["S3"] == "explicit" and fact["S2"] != "explicit" for fact in contract.fact_availability.values()
        ):
            raise DatasetError("Domain integration needs an explicitly assessed incremental S3 fact")
        profiles.append({"question_id": question.question_id, **profile.document()})
    counts = Counter(profile["spider_level"] for profile in profiles)
    if counts != {"easy": 10, "medium": 10, "hard": 5, "extra": 5}:
        raise DatasetError("Original four-level allocation must be 10/10/5/5")
    spec = json.loads(paths["annotation_specification"].read_bytes())
    if spec.get("status") != "draft":
        raise DatasetError("Revised annotation review remains draft")
    from .metadata.snapshots import validate_mcp_provenance, validate_scenario_set
    snapshot_root = paths["metadata_snapshots"].parent / "snapshots"
    if validate_scenario_set(snapshot_root) != snapshot_checks:
        raise DatasetError("Snapshot set differs from its validated receipt")
    baseline = json.loads((root / "runs/database/baseline.json").read_bytes())
    for scenario in SCENARIOS:
        validate_mcp_provenance(root, snapshot_root / scenario, spec, baseline)
    if manifest.status == "frozen_user_attested":
        from .experiment.execution_review import validate_execution_review, load_smoke
        validate_execution_review(root, manifest, paths)
        load_smoke(root, manifest, paths)
    report = {"status": "offline_instrument_validated", "benchmark_id": manifest.benchmark_id,
              "manifest_sha256": sha256_bytes(manifest_path.read_bytes()), "rubric_version": RUBRIC_VERSION,
              "profiles": profiles, "question_count": 30,
              "human_review_complete": manifest.human_review_status == "user_attested_complete",
              "review_basis": "user_attestation" if manifest.human_review_status == "user_attested_complete" else "not_provided",
              "main_experiment_allowed": False, "generation_requests": 0,
              "limits": "Structure and artifact checks do not establish semantic correctness; gold, metadata and fixtures require separate validation."}
    if output:
        publish_artifact(output, canonical_json(report))
    return report
