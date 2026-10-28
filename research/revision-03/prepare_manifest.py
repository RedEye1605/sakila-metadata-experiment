"""Bind real independent review/reference evidence; never manufacture approval."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.contracts import load_gold, load_questions
from sakila_experiment.instrument import ArtifactReference, BenchmarkManifest, SemanticContract, validate_instrument

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/benchmarks/revision-03"


def ref(path):
    return ArtifactReference(path=str(path.resolve().relative_to(ROOT)), sha256=sha256_bytes(path.read_bytes()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-checks", type=Path, default=ROOT / "runs/revision-03/reference-checks-02")
    parser.add_argument("--independent-review", type=Path, default=ROOT / "runs/revision-03/independent-review-01")
    parser.add_argument("--output-directory", type=Path, default=DATA / "final-02")
    parser.add_argument("--information-audit", type=Path, default=ROOT / "runs/revision-03/independent-review-01/gate-receipt-v2.json")
    args = parser.parse_args()
    output = args.output_directory.resolve()
    if not output.is_relative_to(DATA):
        raise ValueError("A new versioned revision03 dataset directory is required")
    questions, gold = load_questions(DATA / "questions.jsonl"), load_gold(DATA / "gold.jsonl")
    interpretations = {r["question_id"]: r for r in map(json.loads, (args.independent_review / "question-intents.jsonl").read_bytes().splitlines())}
    # Authoring cards contain extra provenance notes. The runtime contract is
    # strict; preserve original cards separately rather than weakening schema.
    cards = [json.loads(line) for line in (DATA / "contracts.jsonl").read_bytes().splitlines() if line.strip()]
    contracts = [{key: value for key, value in card.items() if key in SemanticContract.model_fields} for card in cards]
    for contract in contracts:
        independent = interpretations[contract["question_id"]]
        contract.update(grain=independent["grain"], population=independent["population"], measure=independent["intent"],
                        human_review_status="pending", construction_status="draft",
                        ordering_and_ties=("Requested ranking/order is compared after one global column bijection; remaining ties use ascending entity numeric ID, top-k exact." if gold[contract["question_id"]].ordered
                                           else "Unordered multiset of whole rows after one global column bijection; duplicate multiplicities preserved."),
                        independent_review_artifacts=[ref(args.independent_review / "question-intents.jsonl").model_dump(mode="json")],
                        review_notes=(*contract.get("review_notes", []), "Independent complete-input interpretation locked before execution; AI-assisted, human review pending."))
    for contract in contracts:
        SemanticContract.model_validate(contract)
    for name, records in (("questions", [q.model_dump(mode="json") for q in questions]),
                          ("gold", [g.model_dump(mode="json") for g in gold.values()]), ("contracts", contracts)):
        publish_artifact(output / (name + ".jsonl"), b"".join(canonical_json(row) for row in records))
    publish_artifact(output / "profiles.json", (DATA / "profiles.json").read_bytes())
    selection = {"status": "coverage_revised_before_revision03_inference", "selected_question_ids": [q.question_id for q in questions],
                 "generation_requests": 0, "human_review_complete": False,
                 "candidates": {"questions": ref(DATA / "candidates.questions.jsonl").model_dump(mode="json"),
                                "gold": ref(DATA / "candidates.gold-a.jsonl").model_dump(mode="json")},
                 "mutations": ref(DATA / "mutations.json").model_dump(mode="json"),
                 "reason": "Preserve30 IDs/10-10-10 and six domain tasks; add genuine ordered/top-k coverage, natural wording and column-permutation EX by explicit user instruction.",
                 "source_based_scope_changes": ["Q128", "Q141", "Q152"],
                 "wording_ambiguity_correction": "Q154 observed film-linked actor/category pairs, independently flagged before execution.",
                 "not_selected_by": ["model correctness", "S3 advantage", "significance"],
                 "prior_instrument": "data/benchmarks/revision-02/final-02/manifest.json"}
    publish_artifact(output / "selection.json", canonical_json(selection))
    fields = {"questions": ref(output / "questions.jsonl"), "gold": ref(output / "gold.jsonl"), "contracts": ref(output / "contracts.jsonl"),
              "annotation_specification": ref(ROOT / "data/benchmarks/revision-02/annotations.json"),
              "fact_inventory": ref(ROOT / "data/benchmarks/revision-02/facts.json"),
              "analysis_protocol": ref(ROOT / "docs/revision-03/analysis-plan.md"),
              "evaluation_protocol": ref(ROOT / "docs/revision-03/evaluation-protocol.md"),
              "source_lock": ref(ROOT / "research/revision-02/spider-source-lock.json"),
              "selection_receipt": ref(output / "selection.json"), "prompt_template": ref(ROOT / "prompts/generation-v3.txt"),
              "information_audit": ref(args.information_audit),
              "metadata_snapshots": ref(ROOT / "runs/revision-02/metadata/preparation-03/validation.json"),
              "reference_validation": ref(args.reference_checks / "summary.json"),
              "reference_validation_lock": ref(args.reference_checks / "input-lock.json"),
              "fixture_specification": ref(ROOT / "research/revision-03/fixture_cases.json")}
    manifest = BenchmarkManifest(benchmark_id="sakila-revision-03", estimand="metadata-package-domain-information-availability",
                                 result_comparison="ex-results-v3-column-permutation", status="draft", **fields)
    candidate_path = output / "manifest.candidate.json"
    publish_artifact(candidate_path, canonical_json(manifest.model_dump(mode="json")))
    validate_instrument(ROOT, candidate_path, output / "candidate-validation.json")
    manifest = manifest.model_copy(update={"status": "frozen_exploratory"})
    path = output / "manifest.json"
    publish_artifact(path, canonical_json(manifest.model_dump(mode="json")))
    report = validate_instrument(ROOT, path, output / "validation.json")
    print(json.dumps({"status": report["status"], "questions": report["question_count"],
                      "manifest": str(path.relative_to(ROOT)), "generation_requests": 0, "human_review_complete": False}))


if __name__ == "__main__":
    main()
