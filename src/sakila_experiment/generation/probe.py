"""Bounded, reviewed-pilot-only repetition checks; never a model benchmark."""

from dataclasses import asdict
from pathlib import Path
import json

from ..artifacts import canonical_json, publish_artifact
from ..contracts import load_gold, load_questions
from ..experiment.schedule import inference_seed
from .backend import check_live_backend, load_backend_evidence
from .llama import LlamaClient, LLMServiceError
from .prompt import build_prompt


def repetition_probe(config, snapshots: Path, backend_path: Path, output: Path, *, question_id="P007", scenario="S3", allow_unreviewed=False):
    if output.exists():
        raise ValueError("Probe output exists; no request was made")
    if not question_id.startswith("P") or scenario not in config.experiment.scenario_ids:
        raise ValueError("Only separate pilot questions and fixed scenarios are allowed")
    questions = {q.question_id: q for q in load_questions(config.project_root / "data/pilot/questions.jsonl")}
    references = load_gold(config.project_root / "data/pilot/gold.jsonl")
    if question_id not in questions or question_id not in references:
        raise ValueError("Unknown pilot question")
    if references[question_id].review_status != "approved" and not allow_unreviewed:
        raise ValueError("Pilot reference remains draft; human review is required before repetition requests")
    evidence, record = load_backend_evidence(backend_path)
    check_live_backend(config.inference, record)
    folder = snapshots / scenario
    manifest = json.loads((folder / "manifest.json").read_bytes())
    prompt = build_prompt(questions[question_id].generation_input(), json.loads((folder / manifest["payload_file"]).read_bytes()),
                          manifest["snapshot_sha256"], config.project_root / "prompts/generation.txt")
    publish_artifact(output / "prompt.json", canonical_json(prompt.chat_messages()))
    responses = []
    with LlamaClient(config.inference, evidence) as client:
        checked = client.prepare(prompt)
        for repetition in range(1, 6):
            seed = inference_seed(config.experiment.inference_seed_base, question_id, repetition)
            publish_artifact(output / f"request-{repetition}.json", canonical_json({"repetition_id": repetition, "seed": seed, "prompt_sha256": prompt.prompt_sha256}))
            try:
                response = client.generate(checked, seed)
            except LLMServiceError as error:
                publish_artifact(output / "interruption.json", canonical_json({"repetition_id": repetition, "code": error.code, "automatic_retry": False}))
                raise
            publish_artifact(output / f"response-{repetition}.json", canonical_json(asdict(response)))
            if response.infrastructure_error:
                raise LLMServiceError(response.infrastructure_error)
            responses.append(response.text)
    report = {"status": "five_independent_pilot_requests_complete", "question_id": question_id, "scenario_id": scenario,
              "evaluation_status": "provisional" if allow_unreviewed else "engineering", "reference_review_status": references[question_id].review_status,
              "public_results_embargo": True,
              "requests": 5, "unique_raw_outputs": len(set(responses)), "model_sha256": evidence.model_sha256,
              "backend_evidence_sha256": evidence.verification_artifact_sha256, "inference_config": config.inference.model_dump(mode="json"),
              "snapshot_sha256": manifest["snapshot_sha256"], "execution_scoring": False, "main_experiment_allowed": False,
              "interpretation": "Stochastic requests may produce identical outputs; no semantic repair or feedback is performed"}
    publish_artifact(output / "report.json", canonical_json(report))
    return report
