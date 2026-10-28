"""Prospective constrained selection, never based on model outcomes or EX."""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.contracts import load_gold, load_questions
from sakila_experiment.instrument import ArtifactReference, BenchmarkManifest, SemanticContract, validate_instrument

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/benchmarks/revision-02"
SEED = 2026102801
EXCLUSIONS = {
    "Q101": "Independent natural-language/complete-input ambiguity and fixture disagreement: missing postal text.",
    "Q103": "Independent references disagree on NULL rating inclusion in fixed data variations.",
    "Q104": "Low discrimination on primary Sakila: release-year MIN/MAX collapse; keep broader value/filter coverage.",
    "Q106": "Unresolved whitespace convention for filled district text.",
    "Q115": "All original-language references NULL on primary Sakila; avoid a zero-only primary scalar item.",
    "Q123": "Date/staff observed groups versus zero-event grid not fully specified.",
    "Q126": "Independent source-based follow-up finds material all-master-stores versus observed-home-assignments ambiguity.",
    "Q127": "Withhold recorded staff-home-store population pending the same independent master/assignment boundary clarification.",
    "Q129": "Independent natural-language ambiguity: all languages versus observed dubbing languages.",
    "Q132": "Initial empty result and less direct canonical EXISTS structure; avoid structure inflation through reference choice.",
    "Q135": "Fifth-place tie policy unspecified by the natural question.",
    "Q136": "First canonical reference exceeded fixed10s deadline; preserve this exclusion rather than tuning the timeout.",
    "Q137": "Independent material ambiguity: elapsed versus calendar days and unfinished rentals.",
    "Q138": "Same date/staff group population convention asQ123.",
    "Q139": "Independent reference disagreement: observed store/rating groups versus complete grid.",
    "Q144": "Withhold recorded staff-home-store population pending the same independent master/assignment boundary clarification.",
}
DOMAIN_IDS = {f"Q{i}" for i in range(146, 152)}


def ref(path):
    path = path.resolve()
    return ArtifactReference(path=str(path.relative_to(ROOT)), sha256=sha256_bytes(path.read_bytes()))


def select(profiles):
    generator = random.Random(SEED)
    selected, draws = [], []
    for name, level, count, filtered in (("simple-filter", "easy", 5, True), ("simple-aggregate", "easy", 5, False),
                                          ("medium", "medium", 10, None), ("hard", "hard", 5, None), ("extra", "extra", 5, None)):
        pool = sorted(row["question_id"] for row in profiles if row["question_id"] not in EXCLUSIONS
                      and row["spider_level"] == level and (filtered is None or row["features"]["where"] == filtered))
        mandatory = sorted(set(pool) & DOMAIN_IDS)
        remaining = [qid for qid in pool if qid not in mandatory]
        sampled = generator.sample(remaining, count - len(mandatory))
        chosen = sorted(mandatory + sampled)
        if len(chosen) != count:
            raise ValueError("Insufficient eligible supply in prospective stratum: " + name)
        selected.extend(chosen)
        draws.append({"stratum": name, "pool": pool, "mandatory_source_rule_ids": mandatory, "selected": chosen})
    if len(set(selected)) != 30 or not DOMAIN_IDS <= set(selected):
        raise ValueError("Selected draft does not satisfy prospective30-question/source-family design")
    return sorted(selected), draws


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--draft", action="store_true", help="Publish a conditional proposal only; cannot create a frozen instrument")
    parser.add_argument("--information-audit", type=Path)
    parser.add_argument("--reference-validation", type=Path)
    parser.add_argument("--metadata-validation", type=Path, default=ROOT / "runs/revision-02/metadata/preparation-03/validation.json")
    parser.add_argument("--semantic-review", type=Path, action="append", help="Locked independent interpretation JSONL files; required for final private contracts")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("Choose a new selection directory")
    questions = {q.question_id: q for q in load_questions(DATA / "candidates.questions.jsonl")}
    gold = load_gold(DATA / "candidates.gold-a.jsonl")
    contracts = {c.question_id: c for c in (SemanticContract.model_validate_json(line) for line in (DATA / "candidates.contracts.jsonl").read_bytes().splitlines())}
    profile_rows = json.loads((DATA / "candidate-profiles.json").read_bytes())["profiles"]
    selected, draws = select(profile_rows)
    interpretation_rows = {}
    for path in args.semantic_review or []:
        for row in map(json.loads, path.read_bytes().splitlines()):
            if row["question_id"] in interpretation_rows:
                raise ValueError("Duplicate independent interpretation ID")
            interpretation_rows[row["question_id"]] = (row, ref(path))
    if not args.draft:
        if args.information_audit is None or args.reference_validation is None:
            raise ValueError("Freeze requires completed independent information review and full reference/witness evidence")
        if not set(selected) <= interpretation_rows.keys():
            raise ValueError("Every selected question requires its locked independent interpretation")
        # Check before publication. An incomplete review is not promoted by
        # filling out a manifest or by merely requesting exploratory scoring.
        information = json.loads(args.information_audit.read_bytes())
        if information.get("status") != "complete_independent_AI_review":
            raise ValueError("Independent information audit is incomplete")
        assessed = {row["question_id"]: row for row in information["question_assessments"]}
        if any(assessed.get(qid, {}).get("material_residual_ambiguity") is not False for qid in selected):
            raise ValueError("A proposed selected question still has unresolved independent information findings")
        checks = {row["question_id"]: row for row in json.loads(args.reference_validation.read_bytes())["records"]}
        if any(not all(checks.get(qid, {}).get(key) is True for key in ("reference_agreement_all_checked", "reference_execution_valid", "all_predeclared_mutants_distinguished")) for qid in selected):
            raise ValueError("A proposed selected question failed reference or witness gates")
    publish_artifact(output / "questions.jsonl", b"".join(canonical_json(questions[qid].model_dump(mode="json")) for qid in selected))
    publish_artifact(output / "gold.jsonl", b"".join(canonical_json(gold[qid].model_dump(mode="json")) for qid in selected))
    final_contracts = []
    for qid in selected:
        contract = contracts[qid]
        if qid in interpretation_rows:
            row, source = interpretation_rows[qid]
            if row["question"] != questions[qid].question:
                raise ValueError("Independent interpretation refers to different wording")
            contract = contract.model_copy(update={"grain": row["grain"], "population": row["population"], "measure": row["intent"],
                                                  "review_notes": tuple(row.get("assumptions", [])), "independent_review_artifacts": (source,)})
        final_contracts.append(contract)
    publish_artifact(output / "contracts.jsonl", b"".join(canonical_json(c.model_dump(mode="json")) for c in final_contracts))
    receipt = {"status": "conditional_draft_not_eligible" if args.draft else "selected_before_inference",
               "generation_requests": 0, "human_review_complete": False, "main_experiment_allowed": False,
               "seed": SEED, "rng": "Python random.Random; sorted pools; stratum order explicit",
               "selected_question_ids": selected, "stratum_draws": draws, "exclusions": EXCLUSIONS,
               "candidates": {"questions": ref(DATA / "candidates.questions.jsonl").model_dump(), "gold": ref(DATA / "candidates.gold-a.jsonl").model_dump()},
               "source_feasible_domain_allocation": {"simple": 0, "medium": 2, "complex": 4},
               "simple_coverage": "five single-predicate filters and five unfiltered aggregates",
               "semantic_contract_sources": [ref(path).model_dump() for path in args.semantic_review or []],
               "limits": "Purposive constrained benchmark, not a probability sample or guaranteed treatment advantage. Draft selection does not establish eligibility. Never read model outputs, scores, latency or p-values for selection."}
    publish_artifact(output / "selection.json", canonical_json(receipt))
    publish_artifact(output / "profiles.json", canonical_json([row for row in profile_rows if row["question_id"] in selected]))
    if not args.draft:
        fields = {"questions": ref(output / "questions.jsonl"), "gold": ref(output / "gold.jsonl"), "contracts": ref(output / "contracts.jsonl"),
                  "annotation_specification": ref(DATA / "annotations.json"), "fact_inventory": ref(DATA / "facts.json"),
                  "analysis_protocol": ref(ROOT / "docs/revision-02/analysis-plan.md"), "evaluation_protocol": ref(ROOT / "docs/revision-02/evaluation-protocol.md"),
                  "source_lock": ref(ROOT / "research/revision-02/spider-source-lock.json"), "selection_receipt": ref(output / "selection.json"),
                  "prompt_template": ref(ROOT / "prompts/generation-v2.txt"), "information_audit": ref(args.information_audit),
                  "metadata_snapshots": ref(args.metadata_validation), "reference_validation": ref(args.reference_validation),
                  "reference_validation_lock": ref(args.reference_validation.parent / "input-lock.json"),
                  "fixture_specification": ref(ROOT / "research/revision-02/fixture_cases.json")}
        manifest = BenchmarkManifest(benchmark_id="sakila-revision-02", estimand="metadata-package-domain-information-availability", status="draft", **fields)
        publish_artifact(output / "manifest.candidate.json", canonical_json(manifest.model_dump(mode="json")))
        validate_instrument(ROOT, output / "manifest.candidate.json", output / "candidate-validation.json")
        frozen = manifest.model_copy(update={"status": "frozen_exploratory"})
        publish_artifact(output / "manifest.json", canonical_json(frozen.model_dump(mode="json")))
        validate_instrument(ROOT, output / "manifest.json", output / "validation.json")
    print(json.dumps({"status": receipt["status"], "selected_questions": len(selected), "complexity": dict(Counter(questions[q].complexity for q in selected)),
                      "main_experiment_allowed": False, "generation_requests": 0}), flush=True)


if __name__ == "__main__":
    main()
