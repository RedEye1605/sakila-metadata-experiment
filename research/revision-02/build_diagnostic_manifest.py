"""Bind validated independent pilot evidence to actual MCP renderings."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.config import load_config
from sakila_experiment.experiment.diagnostics import DiagnosticManifest, VARIANTS, load_diagnostic
from sakila_experiment.instrument import ArtifactReference, validate_instrument

ROOT = Path(__file__).resolve().parents[2]


def ref(path):
    path = path.resolve()
    return ArtifactReference(path=str(path.relative_to(ROOT)), sha256=sha256_bytes(path.read_bytes()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-manifest", type=Path, required=True)
    parser.add_argument("--independent-review", type=Path, required=True)
    parser.add_argument("--reference-validation", type=Path, required=True)
    parser.add_argument("--renderings", type=Path, required=True)
    parser.add_argument("--token-matching", type=Path, required=True)
    parser.add_argument("--context-preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    validate_instrument(ROOT, args.benchmark_manifest)
    data = ROOT / "data/benchmarks/revision-02"
    manifest = DiagnosticManifest(diagnostic_id="revision-02-diagnostic-01",
        benchmark_manifest=ref(args.benchmark_manifest), questions=ref(data / "pilot.questions.jsonl"),
        gold=ref(data / "pilot.gold-a.jsonl"), cards=ref(data / "pilot.cards.jsonl"),
        independent_review=ref(args.independent_review), semantic_validation=ref(args.reference_validation),
        semantic_validation_lock=ref(args.reference_validation.parent / "input-lock.json"),
        token_matching=ref(args.token_matching), context_preflight=ref(args.context_preflight),
        renderings={variant: ref(args.renderings / variant / "manifest.json") for variant in VARIANTS})
    candidate = args.output.with_name("diagnostic-manifest.candidate.json")
    publish_artifact(candidate, canonical_json(manifest.model_dump(mode="json")))
    config = load_config(ROOT / "configs/revision02.toml")
    _, _, _, _, validation, _, schedule = load_diagnostic(ROOT, candidate, config.experiment)
    publish_artifact(args.output, canonical_json(manifest.model_dump(mode="json")))
    report = {"status": "offline_diagnostic_inputs_validated", "manifest_sha256": sha256_bytes(args.output.read_bytes()),
              "planned_trial_count": len(schedule), "generation_requests": 0, "rendering_sha256": validation["snapshot_sha256"],
              "human_review_complete": False, "main_experiment_allowed": False,
              "note": "Runtime/context/gold freeze remains a separate command; this receipt is not run completion."}
    publish_artifact(args.output.with_name("diagnostic-input-validation.json"), canonical_json(report))
    print(json.dumps({k: report[k] for k in ("status", "planned_trial_count", "generation_requests")}), flush=True)


if __name__ == "__main__":
    main()
