"""Bounded diagnostic manifest and schedule; variants are not S0-S3 trials."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import model_validator

from ..artifacts import canonical_json, sha256_bytes
from ..config import StrictModel
from ..contracts import DatasetError, load_gold, load_questions
from ..instrument import ArtifactReference
from .schedule import TrialAssignment, inference_seed

VARIANTS = ("A", "B", "C", "B-order1", "B-order2")


def expanded_description(text: str) -> str:
    return "Makna informasi pada elemen ini dijelaskan berikut. " + text + " Uraian tersebut menjelaskan informasi yang dicatat pada elemen ini."


class DiagnosticManifest(StrictModel):
    diagnostic_version: Literal[2] = 2
    diagnostic_id: str
    benchmark_manifest: ArtifactReference
    questions: ArtifactReference
    gold: ArtifactReference
    cards: ArtifactReference
    independent_review: ArtifactReference
    semantic_validation: ArtifactReference
    semantic_validation_lock: ArtifactReference
    token_matching: ArtifactReference
    context_preflight: ArtifactReference
    renderings: dict[str, ArtifactReference]
    repetitions: Literal[3] = 3
    trial_count: Literal[180] = 180
    main_experiment_allowed: Literal[False] = False
    human_review_status: Literal["pending"] = "pending"

    @model_validator(mode="after")
    def expected_renderings(self):
        if set(self.renderings) != set(VARIANTS):
            raise ValueError("Diagnostic manifest requires exactly A/B/C and two B rotations")
        return self


@dataclass(frozen=True)
class DiagnosticAssignment(TrialAssignment):
    variant_id: str


def diagnostic_schedule(questions, settings) -> tuple[DiagnosticAssignment, ...]:
    if len(questions) != 12 or len({q.question_id for q in questions}) != 12 or any(not q.question_id.startswith("P") for q in questions):
        raise DatasetError("Diagnostic schedule requires twelve unique separate P questions")
    generator = random.Random(settings.order_seed)
    assignments = []
    for repetition in range(1, 4):
        block = [(question, variant) for question in sorted(questions, key=lambda q: q.question_id) for variant in VARIANTS]
        generator.shuffle(block)
        for question, variant in block:
            assignments.append(DiagnosticAssignment(f"{question.question_id}-{variant}-r{repetition:02}", question.question_id,
                question.complexity, variant, repetition, inference_seed(settings.inference_seed_base, question.question_id, repetition), len(assignments) + 1, variant))
    return tuple(assignments)


def load_diagnostic(root: Path, path: Path, settings):
    manifest = DiagnosticManifest.model_validate_json(path.read_bytes())
    inputs = {name: getattr(manifest, name).verified_path(root) for name in (
        "benchmark_manifest", "questions", "gold", "cards", "independent_review", "semantic_validation", "semantic_validation_lock", "token_matching", "context_preflight")}
    questions, gold = load_questions(inputs["questions"]), load_gold(inputs["gold"])
    if {q.question_id for q in questions} != gold.keys() or any(g.review_status != "draft" for g in gold.values()):
        raise DatasetError("Diagnostic references must match the questions and remain honest drafts")
    cards = [json.loads(line) for line in inputs["cards"].read_bytes().splitlines() if line.strip()]
    from collections import Counter
    if ({row["question_id"] for row in cards} != gold.keys() or len(cards) != 12
            or sorted(Counter(row["semantic_family"] for row in cards).values()) != [3, 3, 3, 3]
            or any(row.get("primary_business_rule_family") is not None for row in cards)):
        raise DatasetError("Diagnostic family coverage differs from the separate four-family pilot design")
    proof = json.loads(inputs["semantic_validation_lock"].read_bytes())
    if proof["questions_sha256"] != sha256_bytes(inputs["questions"].read_bytes()) or proof["gold_a_sha256"] != sha256_bytes(inputs["gold"].read_bytes()):
        raise DatasetError("Pilot reference validation belongs to another question/gold version")
    for reference in proof["gold_b_files"]:
        ArtifactReference.model_validate(reference).verified_path(root)
    checked = json.loads(inputs["semantic_validation"].read_bytes())
    checks = {row["question_id"]: row for row in checked["records"]}
    if any(not all(checks.get(qid, {}).get(key) is True for key in ("reference_agreement_all_checked", "reference_execution_valid", "all_predeclared_mutants_distinguished")) for qid in gold):
        raise DatasetError("Pilot independent references or semantic witnesses are incomplete")
    review = json.loads(inputs["independent_review"].read_bytes())
    if (review.get("status") != "complete_independent_AI_pilot_review" or review.get("human_review_complete") is not False
            or review.get("questions_sha256") != sha256_bytes(inputs["questions"].read_bytes())
            or review.get("unresolved_question_ids") != []):
        raise DatasetError("The changed pilot still requires independent semantic follow-up")
    for reference in review["source_artifacts"]:
        ArtifactReference.model_validate(reference).verified_path(root)
    payloads, snapshots, directories, manifests = {}, {}, {}, {}
    for variant, reference in manifest.renderings.items():
        selected = reference.verified_path(root)
        document = json.loads(selected.read_bytes())
        digest = document["snapshot_sha256"]
        if document["payload_file"] != digest + ".json":
            raise DatasetError("Diagnostic payload path is not content addressed")
        content = (selected.parent / document["payload_file"]).read_bytes()
        if sha256_bytes(content) != digest:
            raise DatasetError("Diagnostic snapshot content changed")
        payloads[variant] = json.loads(content)
        manifests[variant] = document
        snapshots[variant] = digest
        directories[variant] = str(selected.parent.resolve().relative_to(root.resolve()))
    if any(payloads[v]["technical_schema"] != payloads["A"]["technical_schema"] for v in VARIANTS):
        raise DatasetError("Diagnostic technical schema changed")
    a, b, c = (payloads[v] for v in ("A", "B", "C"))
    if b["business_context"] != a["business_context"] or c["descriptions"] != a["descriptions"]:
        raise DatasetError("Diagnostic expansion changed an unplanned section")
    expected_b = [{"target": row["target"], "description": expanded_description(row["description"])} for row in a["descriptions"]]
    if b["descriptions"] != expected_b:
        raise DatasetError("Verbose control is not the preregistered proposition-preserving expansion")
    repeats = manifests["C"].get("business_card_repetitions")
    if not isinstance(repeats, list) or len(repeats) != len(a["business_context"]) or any(type(n) is not int or not 1 <= n <= 12 for n in repeats):
        raise DatasetError("Irrelevant-repetition counts are missing or invalid")
    expected_c = [{**row, "definition": "\n\n".join([row["definition"]] * count)} for row, count in zip(a["business_context"], repeats, strict=True)]
    if c["business_context"] != expected_c:
        raise DatasetError("Irrelevant-load control added or changed domain propositions")
    for payload in payloads.values():
        if set(payload) != {"technical_schema", "descriptions", "business_context"}:
            raise DatasetError("Diagnostic model context contains an unapproved section")
        targets = [row["target"] for row in payload["descriptions"]]
        if len(targets) != 106 or len(set(targets)) != 106 or set(targets) != {row["target"] for row in a["descriptions"]}:
            raise DatasetError("Diagnostic annotation coverage changed")
    for variant in ("B-order1", "B-order2"):
        rotated = payloads[variant]
        if rotated["business_context"] != b["business_context"] or sorted(rotated["descriptions"], key=lambda d: d["target"]) != sorted(b["descriptions"], key=lambda d: d["target"]):
            raise DatasetError("Position control changed the text multiset")
        if manifests[variant].get("source_snapshot_sha256") != snapshots["B"] or manifests[variant].get("transformation") != "fixed_description_block_rotation":
            raise DatasetError("Position-control provenance is missing")
        offset = len(b["descriptions"]) * (1 if variant == "B-order1" else 2) // 3
        if manifests[variant].get("rotation_offset") != offset or rotated["descriptions"] != b["descriptions"][offset:] + b["descriptions"][:offset]:
            raise DatasetError("Position control is not the preregistered fixed rotation")
    matching = json.loads(inputs["token_matching"].read_bytes())
    for variant in ("B", "C"):
        value = {name: payloads[variant][name] for name in ("descriptions", "business_context")}
        digest = sha256_bytes(canonical_json(value))
        count = matching[variant + "_annotation_tokens"]
        if not any(row["content_sha256"] == digest and row["tokens"] == count for row in matching["tokenizer_requests"]):
            raise DatasetError("Actual diagnostic annotation text lacks tokenizer matching evidence")
    if abs(matching["C_annotation_tokens"] - matching["B_annotation_tokens"]) / matching["B_annotation_tokens"] > .05:
        raise DatasetError("B/C annotation token counts differ by more than the frozen5percent limit")
    from ..metadata.snapshots import validate_mcp_provenance
    from ..instrument import read_manifest, validate_reference_code
    validate_reference_code(root, proof)
    benchmark, benchmark_paths = read_manifest(root, inputs["benchmark_manifest"])
    if proof["fixture_definition_sha256"] != benchmark.fixture_specification.sha256:
        raise DatasetError("Pilot and benchmark reference checks used different fixture definitions")
    fixture_ids = [row["fixture_id"] for row in json.loads(benchmark_paths["fixture_specification"].read_bytes())["cases"]]
    validate_pilot_cases(checked, gold.keys(), fixture_ids)
    context = json.loads(inputs["context_preflight"].read_bytes())
    backend_reference = ArtifactReference.model_validate(context["backend_verification"])
    backend_document = json.loads(backend_reference.verified_path(root).read_bytes())
    if backend_reference.sha256 != context["backend_evidence_sha256"]:
        raise DatasetError("Context evidence is not bound to its actual backend verification artifact")
    source_keys = {"model_id": "model_id", "model_sha256": "model_sha256", "backend_revision": "backend_revision",
                   "backend_build_info": "build_info", "chat_template_sha256": "chat_template_sha256", "context_tokens": "effective_context_tokens"}
    if any(context.get(key) != backend_document.get(source) for key, source in source_keys.items()):
        raise DatasetError("Context receipt misidentifies its source backend/model verification")
    if (context.get("status") != "complete_contexts_verified_without_generation" or context.get("generation_requests") != 0
            or context.get("questions_sha256", {}).get("pilot.questions.jsonl") != sha256_bytes(inputs["questions"].read_bytes())
            or context.get("prompt_template_sha256") != benchmark.prompt_template.sha256):
        raise DatasetError("Actual context/tokenization receipt belongs to another pilot or prompt")
    if matching.get("model_id") != context.get("model_id") or matching.get("build_info") != context.get("backend_build_info"):
        raise DatasetError("Diagnostic token matching and context checks used different backends")
    if any(context.get("annotation_tokens", {}).get(v) != matching[v + "_annotation_tokens"] for v in ("B", "C")):
        raise DatasetError("Fresh actual diagnostic annotation tokens differ from the matching plan")
    context_rows = [row for row in context["complete_prompt_checks"] if row["dataset"] == "diagnostic"]
    if (len(context_rows) != 60 or {(row["question_id"], row["variant_id"]) for row in context_rows} != {(qid, v) for qid in gold for v in VARIANTS}
            or any(row["snapshot_manifest_sha256"] != manifest.renderings[row["variant_id"]].sha256 for row in context_rows)):
        raise DatasetError("Actual diagnostic context checks do not cover all60frozen prompts")
    specification = json.loads(benchmark_paths["annotation_specification"].read_bytes())
    audit = json.loads((root / "runs/database/baseline.json").read_bytes())
    validate_mcp_provenance(root, root / directories["A"], specification, audit)
    planning_directory = inputs["token_matching"].parent
    for variant in ("B", "C"):
        validate_mcp_provenance(root, root / directories[variant], json.loads((planning_directory / (variant + ".annotations.json")).read_bytes()), audit)
    # Content matching is also checked against explicit construction receipts,
    # including wrapper/repetition rules; a SHA alone is not a semantics proof.
    for variant in VARIANTS:
        if manifests[variant].get("two_export_stability_verified") is not True:
            raise DatasetError("Diagnostic source lacks paired MCP stability evidence")
    assignments = diagnostic_schedule(questions, settings)
    return manifest, inputs, questions, gold, {"snapshot_sha256": snapshots, "main_experiment_allowed": False}, directories, assignments


def validate_pilot_cases(checked, ids, fixture_ids):
    if (len(checked.get("cases", [])) != 9 or set(checked["cases"]) != {"baseline", *fixture_ids}
            or checked.get("primary_database_unchanged") is not True):
        raise DatasetError("Pilot proof does not contain baseline plus the declared8cases on unchanged primary data")
    by_id = {row["question_id"]: row for row in checked["records"]}
    if len(by_id) != len(checked["records"]) or set(by_id) != set(ids):
        raise DatasetError("Pilot proof question coverage is duplicated or incomplete")
    for row in by_id.values():
        if not row.get("witnesses") or any(not cases or not set(cases) <= set(checked["cases"]) for cases in row["witnesses"].values()):
            raise DatasetError("A critical pilot mutant lacks a valid distinguishing fixture")
