"""Bind the actual researcher statement; preserve anonymous/unknown fields."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.experiment.execution_review import stimulus_identity, stimulus_scope
from sakila_experiment.instrument import ArtifactReference, BenchmarkManifest, validate_instrument

ROOT = Path(__file__).resolve().parents[2]


def ref(path):
    return ArtifactReference(path=str(path.relative_to(ROOT)), sha256=sha256_bytes(path.read_bytes()))


def main():
    source = ROOT / "data/benchmarks/revision-03/final-02/manifest.json"
    original = BenchmarkManifest.model_validate_json(source.read_bytes())
    review_path = ROOT / "data/reviews/revision03-user-attestation.json"
    if not review_path.exists():
        review = {"status": "user_attested_complete", "source": "direct_user_statement",
                  "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                  "statement": "semua ini sudah di review! nanti saya sendiri yang nyantumin reviewernya siapa!",
                  "scope": stimulus_scope(original),
                  "snapshot_sha256": json.loads((ROOT / original.metadata_snapshots.path).read_bytes())["snapshot_sha256"],
                  "reviewer_names": [], "reviewer_identity_status": "pending_user_entry", "review_date_utc": None,
                  "basis": "Review completion declared by the researcher in the current conversation; no independent signatures or item-level submission files are asserted."}
        publish_artifact(review_path, canonical_json(review))
    smoke_directory = ROOT / "data/benchmarks/revision-03/smoke-01"
    proof = ROOT / "runs/revision-03/smoke-reference-checks-01"
    smoke_path = smoke_directory / "manifest.json"
    smoke = {"purpose": "engineering_only_no_score_threshold", "trial_count": 12,
             "stimulus_identity": stimulus_identity(original),
             "questions": ref(smoke_directory / "candidates.questions.jsonl").model_dump(mode="json"),
             "gold": ref(smoke_directory / "candidates.gold-a.jsonl").model_dump(mode="json"),
             "mutations": ref(smoke_directory / "mutations.json").model_dump(mode="json"),
             "independent_review": ref(ROOT / "runs/revision-03/smoke-independent-01/receipt.json").model_dump(mode="json"),
             "validation": ref(proof / "summary.json").model_dump(mode="json"),
             "validation_lock": ref(proof / "input-lock.json").model_dump(mode="json")}
    publish_artifact(smoke_path, canonical_json(smoke))
    main_manifest = original.model_copy(update={"status": "frozen_user_attested", "main_experiment_allowed": True,
        "human_review_status": "user_attested_complete", "execution_review": ref(review_path), "smoke_test": ref(smoke_path)})
    path = ROOT / "data/benchmarks/revision-03/execution-01/manifest.json"
    publish_artifact(path, canonical_json(main_manifest.model_dump(mode="json")))
    validate_instrument(ROOT, path, path.parent / "validation.json")
    print(json.dumps({"status": "user_attested_inputs_bound", "reviewer_names_supplied": False,
                      "generation_requests": 0, "manifest": str(path.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
