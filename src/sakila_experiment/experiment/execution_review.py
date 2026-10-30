"""Researcher-declared review and a separate hash-bound engineering smoke.

Record the user's statement without inventing reviewer names, dates, independent
signatures or item-level submissions.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..artifacts import canonical_json, sha256_bytes
from ..contracts import DatasetError, load_gold, load_questions
from ..instrument import ArtifactReference, validate_permutation_witnesses, validate_reference_code

REVIEW_SCOPE = ("questions", "gold", "contracts", "annotation_specification", "fact_inventory",
                "analysis_protocol", "evaluation_protocol", "prompt_template", "metadata_snapshots")


def stimulus_scope(manifest):
    return {name: getattr(manifest, name).model_dump(mode="json") for name in REVIEW_SCOPE}


def stimulus_identity(manifest):
    return sha256_bytes(canonical_json(stimulus_scope(manifest)))


def validate_execution_review(root: Path, manifest, paths):
    if manifest.execution_review is None:
        raise DatasetError("A researcher review attestation is required for main execution")
    review = json.loads(paths["execution_review"].read_bytes())
    if (review.get("status") != "user_attested_complete" or review.get("source") != "direct_user_statement"
            or not review.get("statement", "").strip() or not review.get("recorded_at_utc")
            or review.get("scope") != stimulus_scope(manifest)
            or review.get("snapshot_sha256") != json.loads(paths["metadata_snapshots"].read_bytes())["snapshot_sha256"]):
        raise DatasetError("User review statement is absent or does not bind the selected inputs")
    if (review.get("reviewer_identity_status") not in {"pending_user_entry", "provided"}
            or review.get("reviewer_identity_status") == "provided" and not review.get("reviewer_names")):
        raise DatasetError("Review identity provenance is inconsistent")
    for value in review["scope"].values():
        ArtifactReference.model_validate(value).verified_path(root)
    return review


def load_smoke(root: Path, manifest, paths):
    if manifest.smoke_test is None:
        raise DatasetError("A versioned engineering smoke definition is required")
    document = json.loads(paths["smoke_test"].read_bytes())
    if (document.get("purpose") != "engineering_only_no_score_threshold" or document.get("trial_count") != 12
            or document.get("stimulus_identity") != stimulus_identity(manifest)):
        raise DatasetError("Smoke definition differs from the selected main inputs")
    selected = {name: ArtifactReference.model_validate(document[name]).verified_path(root)
                for name in ("questions", "gold", "mutations", "independent_review", "validation", "validation_lock")}
    questions, gold = load_questions(selected["questions"]), load_gold(selected["gold"])
    main_questions = load_questions(paths["questions"])
    normalize = lambda text: " ".join(text.casefold().split())
    if (len(questions) != 3 or {q.question_id for q in questions} != set(gold)
            or any(not q.question_id.startswith("P") for q in questions)
            or {normalize(q.question) for q in questions} & {normalize(q.question) for q in main_questions}
            or any(g.column_order != "permutation" for g in gold.values())):
        raise DatasetError("Smoke must contain three separate P questions under the selected result policy")
    proof = json.loads(selected["validation_lock"].read_bytes())
    if (proof.get("questions_sha256") != sha256_bytes(selected["questions"].read_bytes())
            or proof.get("gold_a_sha256") != sha256_bytes(selected["gold"].read_bytes())
            or proof.get("fixture_definition_sha256") != manifest.fixture_specification.sha256
            or proof.get("mutations_artifact") != document["mutations"]):
        raise DatasetError("Smoke reference proof belongs to other inputs")
    validate_reference_code(root, proof)
    for ref in proof["gold_b_files"]:
        ArtifactReference.model_validate(ref).verified_path(root)
    checks = json.loads(selected["validation"].read_bytes())
    fixture_ids = [case["fixture_id"] for case in json.loads(paths["fixture_specification"].read_bytes())["cases"]]
    if (set(checks.get("cases", [])) != {"baseline", *fixture_ids} or len(checks["cases"]) != 9
            or checks.get("primary_database_unchanged") is not True):
        raise DatasetError("Smoke reference proof requires baseline plus all eight unchanged-schema cases")
    validate_permutation_witnesses(selected["validation"], selected["validation_lock"], checks,
                                  json.loads(selected["mutations"].read_bytes()), set(gold))
    review = json.loads(selected["independent_review"].read_bytes())
    sources = {row["path"]: row["sha256"] for row in review.get("inputs", [])}
    if (review.get("review_kind") != "independent_engineering_reference_check"
            or review.get("engineering_review_complete") is not True
            or sources.get(str(selected["questions"].relative_to(root))) != sha256_bytes(selected["questions"].read_bytes())
            or review.get("engineering_findings", {}).get("unresolved_ambiguities") != []
            or review.get("human_review_complete") is not False
            or review.get("reference_artifact_sha256", {}).get("gold-b.jsonl") not in {r["sha256"] for r in proof["gold_b_files"]}):
        raise DatasetError("Smoke independent engineering interpretation is missing or unresolved")
    for row in review["inputs"]:
        ArtifactReference(path=row["path"], sha256=row["sha256"]).verified_path(root)
    return document, selected, questions, gold, proof
