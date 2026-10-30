import json
from pathlib import Path

import pytest

from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.contracts import DatasetError, load_gold, load_questions
from sakila_experiment.instrument import BenchmarkManifest, validate_instrument

ROOT = Path(__file__).parents[2]


def test_structure_counts_cannot_substitute_for_independent_information_review(tmp_path):
    """Synthetic proof receipts exercise rejection, never endorse a real gold."""
    data = ROOT / "data/benchmarks/revision-02"
    ids = {"Q102", "Q105", "Q107", "Q112", "Q114", "Q116", "Q118", "Q119", "Q120", "Q121", "Q125", "Q126", "Q130", "Q131", "Q133", "Q134", "Q141", "Q142", "Q143", "Q146", "Q147", "Q148", "Q149", "Q150", "Q151", "Q155", "Q156", "Q157", "Q159", "Q160"}
    def write(name, value):
        path = tmp_path / name
        path.write_bytes(value if isinstance(value, bytes) else canonical_json(value))
        return {"path": name, "sha256": sha256_bytes(path.read_bytes())}
    candidates = load_questions(data / "candidates.questions.jsonl")
    references = load_gold(data / "candidates.gold-a.jsonl")
    questions = write("questions.jsonl", b"".join(canonical_json(q.model_dump(mode="json")) for q in candidates if q.question_id in ids))
    gold = write("gold.jsonl", b"".join(canonical_json(g.model_dump(mode="json")) for qid, g in references.items() if qid in ids))
    contract_bytes = b"".join(line + b"\n" for line in (data / "candidates.contracts.jsonl").read_bytes().splitlines() if json.loads(line)["question_id"] in ids)
    contracts = write("contracts.jsonl", contract_bytes)
    candidate_q = write("candidate-questions.jsonl", (data / "candidates.questions.jsonl").read_bytes())
    candidate_g = write("candidate-gold.jsonl", (data / "candidates.gold-a.jsonl").read_bytes())
    fixture_data = json.loads((ROOT / "research/revision-02/fixture_cases.json").read_bytes())
    fixture = write("fixtures.json", fixture_data)
    blank = write("unused.json", {})
    independent = write("independent-test-only.json", {"synthetic_fixture": True})
    selection = write("selection.json", {"selected_question_ids": sorted(ids), "generation_requests": 0,
                      "candidates": {"questions": candidate_q, "gold": candidate_g}})
    proof = write("reference-checks.json", {"synthetic_fixture": True, "primary_database_unchanged": True, "cases": ["baseline", *(case["fixture_id"] for case in fixture_data["cases"])],
                  "records": [{"question_id": qid, "reference_agreement_all_checked": True, "reference_execution_valid": True,
                               "all_predeclared_mutants_distinguished": True, "witnesses": {"wrong": ["synthetic"]}} for qid in ids]})
    proof_lock = write("proof-lock.json", {"questions_sha256": candidate_q["sha256"], "gold_a_sha256": candidate_g["sha256"],
                       "fixture_definition_sha256": fixture["sha256"], "gold_b_files": [independent]})
    info = write("information.json", {"status": "incomplete_due_to_quota", "human_review_complete": False})
    snapshots = write("snapshots.json", {"snapshot_sha256": {}})
    fields = {name: blank for name in ("annotation_specification", "fact_inventory", "analysis_protocol", "evaluation_protocol", "source_lock", "prompt_template")}
    fields.update(questions=questions, gold=gold, contracts=contracts, selection_receipt=selection,
                  information_audit=info, metadata_snapshots=snapshots, reference_validation=proof,
                  reference_validation_lock=proof_lock, fixture_specification=fixture)
    manifest = BenchmarkManifest(benchmark_id="synthetic-gate-test", estimand="metadata-package-domain-information-availability", **fields)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_bytes(canonical_json(manifest.model_dump(mode="json")))
    with pytest.raises(DatasetError, match="incomplete AI audit"):
        validate_instrument(tmp_path, manifest_path)
    # A failed reference must block even if someone changes an audit status.
    proof_value = json.loads((tmp_path / "reference-checks.json").read_bytes())
    proof_value["records"][0]["reference_agreement_all_checked"] = False
    fields["reference_validation"] = write("reference-checks.json", proof_value)
    manifest = BenchmarkManifest(benchmark_id="synthetic-gate-test", estimand="metadata-package-domain-information-availability", **fields)
    manifest_path.write_bytes(canonical_json(manifest.model_dump(mode="json")))
    with pytest.raises(DatasetError, match="did not pass"):
        validate_instrument(tmp_path, manifest_path)
