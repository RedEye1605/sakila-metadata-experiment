"""Full candidate/diagnostic context verification; no completion requests."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.config import load_config
from sakila_experiment.contracts import load_questions
from sakila_experiment.experiment.diagnostics import VARIANTS
from sakila_experiment.generation.backend import check_live_backend, load_backend_evidence
from sakila_experiment.generation.llama import LlamaClient
from sakila_experiment.generation.prompt import build_prompt

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-evidence", type=Path, required=True)
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--diagnostics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/coder7b.toml")
    args = parser.parse_args()
    config = load_config(args.config)
    evidence, backend = load_backend_evidence(args.backend_evidence)
    check_live_backend(config.inference, backend)
    template = ROOT / "prompts/generation-v2.txt"
    records, annotation_tokens = [], {}
    with LlamaClient(config.inference, evidence) as client:
        for label, question_path, directory, variants in (
            ("candidate", ROOT / "data/benchmarks/revision-02/candidates.questions.jsonl", args.snapshots, ("S0", "S1", "S2", "S3")),
            ("diagnostic", ROOT / "data/benchmarks/revision-02/pilot.questions.jsonl", args.diagnostics, VARIANTS),
        ):
            for variant in variants:
                folder = directory / variant
                manifest_bytes = (folder / "manifest.json").read_bytes()
                manifest = json.loads(manifest_bytes)
                payload = json.loads((folder / manifest["payload_file"]).read_bytes())
                for question in load_questions(question_path):
                    prompt = build_prompt(question.generation_input(), payload, manifest["snapshot_sha256"], template)
                    checked = client.prepare(prompt)
                    records.append({"dataset": label, "question_id": question.question_id, "variant_id": variant,
                                    "prompt_sha256": prompt.prompt_sha256, "snapshot_manifest_sha256": sha256_bytes(manifest_bytes),
                                    "input_tokens": checked.input_tokens, "output_reserve": config.inference.max_output_tokens,
                                    "safety_margin": config.inference.safety_margin_tokens})
                if label == "diagnostic":
                    response = client.client.post(config.inference.base_url + "/tokenize", json={"content": canonical_json({k: payload[k] for k in ("descriptions", "business_context")}).decode(),
                                                                    "add_special": False, "parse_special": False, "with_pieces": False})
                    response.raise_for_status()
                    annotation_tokens[variant] = len(response.json()["tokens"])
    if abs(annotation_tokens["B"] - annotation_tokens["C"]) / annotation_tokens["B"] > .05:
        raise ValueError("Actual MCP diagnostic B/C no longer matches annotation-token criterion")
    report = {"status": "complete_contexts_verified_without_generation", "generation_requests": 0,
              "model_id": evidence.model_id, "backend_revision": evidence.backend_revision,
              "backend_build_info": backend["build_info"], "chat_template_sha256": backend["chat_template_sha256"],
              "backend_verification": {"path": str(args.backend_evidence.resolve().relative_to(ROOT)), "sha256": sha256_bytes(args.backend_evidence.read_bytes())},
              "model_sha256": evidence.model_sha256, "backend_evidence_sha256": evidence.verification_artifact_sha256,
              "prompt_template_sha256": sha256_bytes(template.read_bytes()), "context_tokens": config.inference.context_tokens,
              "annotation_tokens": annotation_tokens, "complete_prompt_checks": records,
              "questions_sha256": {p.name: sha256_bytes(p.read_bytes()) for p in (ROOT / "data/benchmarks/revision-02").glob("*.questions.jsonl")},
              "maximum_input_tokens": max(r["input_tokens"] for r in records), "truncation_allowed": False,
              "human_review_complete": False, "main_experiment_allowed": False}
    publish_artifact(args.output, canonical_json(report))
    print(json.dumps({k: report[k] for k in ("status", "generation_requests", "maximum_input_tokens", "annotation_tokens")}), flush=True)


if __name__ == "__main__":
    main()
