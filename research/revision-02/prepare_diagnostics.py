"""Author and tokenize controlled diagnostic renderings; never generate SQL.

Planning payloads are not MCP exports. Final renderings may only be published
after separate, stable DataHub/MCP retrieval of both B and C specifications.
"""
from __future__ import annotations

import argparse
import copy
import itertools
import json
from pathlib import Path

import httpx

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.config import load_config
from sakila_experiment.experiment.diagnostics import expanded_description
from sakila_experiment.metadata.snapshots import validate_scenario_set

ROOT = Path(__file__).resolve().parents[2]


def payload(directory):
    document = json.loads((directory / "manifest.json").read_bytes())
    content = (directory / document["payload_file"]).read_bytes()
    if sha256_bytes(content) != document["snapshot_sha256"]:
        raise ValueError("Source snapshot bytes changed")
    return document, json.loads(content)


def plan(source, output, config_path):
    if output.exists():
        raise FileExistsError("Choose a new diagnostic planning directory")
    validate_scenario_set(source)
    _, a = payload(source / "S3")
    spec = json.loads((ROOT / "data/benchmarks/revision-02/annotations.json").read_bytes())
    b_spec, b = copy.deepcopy(spec), copy.deepcopy(a)
    b_spec["specification_version"] = "revision-02-diagnostic-verbose"
    for annotation in b_spec["annotations"]:
        annotation["detailed"] = expanded_description(annotation["detailed"])
    for row in b["descriptions"]:
        row["description"] = expanded_description(row["description"])
    settings = load_config(config_path).inference
    requests = []
    with httpx.Client(base_url=settings.base_url, timeout=30, trust_env=False) as client:
        def tokens(value):
            content = canonical_json(value).decode()
            response = client.post("/tokenize", json={"content": content, "add_special": False, "parse_special": False, "with_pieces": False})
            response.raise_for_status()
            result = response.json()
            if not isinstance(result.get("tokens"), list) or any(type(t) is not int for t in result["tokens"]):
                raise ValueError("Backend tokenizer returned invalid token IDs")
            requests.append({"content_sha256": sha256_bytes(content.encode()), "tokens": len(result["tokens"])})
            return len(result["tokens"])
        def annotations(value):
            return {name: value[name] for name in ("descriptions", "business_context")}
        target = tokens(annotations(b))
        a_count = tokens(annotations(a))
        # Rank bounded candidates using actual per-card token counts. Only
        # measured whole-annotation counts determine the acceptance decision.
        card_sizes = [tokens(row["definition"]) for row in a["business_context"]]
        choices = sorted(itertools.product(range(1, 13), repeat=len(card_sizes)),
                         key=lambda counts: (abs(a_count + sum((n - 1) * size for n, size in zip(counts, card_sizes)) - target), counts))
        checked = []
        for counts in choices:
            c = copy.deepcopy(a)
            for row, count in zip(c["business_context"], counts, strict=True):
                row["definition"] = "\n\n".join([row["definition"]] * count)
            measured = tokens(annotations(c))
            checked.append({"counts": counts, "annotation_tokens": measured, "relative_difference": abs(measured - target) / target})
            if abs(measured - target) / target <= 0.05:
                break
        else:
            raise ValueError("No allowed source-preserving C repetition matches B within5percent")
        props = client.get("/props")
        props.raise_for_status()
        properties = props.json()
        if properties.get("model_alias") != settings.model_id:
            raise ValueError("Tokenizer is not serving the fixed selected model")
    c_spec = copy.deepcopy(spec)
    c_spec["specification_version"] = "revision-02-diagnostic-irrelevant-repetition"
    # Normalization sorts glossary entities by URN. Bind counts to that same
    # stable order rather than relying on authoring-list insertion order.
    ordered = sorted(c_spec["business_terms"], key=lambda term: term["urn"])
    for term, count in zip(ordered, counts, strict=True):
        term["definition"] = "\n\n".join([term["definition"]] * count)
    publish_artifact(output / "B.annotations.json", canonical_json(b_spec))
    publish_artifact(output / "C.annotations.json", canonical_json(c_spec))
    publish_artifact(output / "token-matching.json", canonical_json({
        "status": "authoring_token_plan_not_mcp_evidence", "generation_requests": 0,
        "source_snapshot_sha256": sha256_bytes(canonical_json(a)),
        "source_specification_sha256": sha256_bytes(canonical_json(spec)),
        "model_id": properties["model_alias"], "build_info": properties["build_info"],
        "annotation_serialization": "canonical JSON of descriptions and business_context only",
        "A_annotation_tokens": a_count, "B_annotation_tokens": target, "C_annotation_tokens": measured,
        "C_business_card_repetitions": counts, "checked_candidates": checked, "tokenizer_requests": requests,
        "interpretation": "C repeats true, pilot-irrelevant domain rules already present in A; no novel facts. It tests irrelevant exposition/repetition and is not inert padding or pure length isolation."}))
    return {"status": "diagnostic_specs_authored", "B_annotation_tokens": target, "C_annotation_tokens": measured,
            "relative_difference": abs(measured-target)/target, "generation_requests": 0}


def assemble(source, plan_directory, b_directory, c_directory, output):
    if output.exists():
        raise FileExistsError("Choose a new diagnostic rendering directory")
    records = {"A": payload(source / "S3"), "B": payload(b_directory / "S3"), "C": payload(c_directory / "S3")}
    planning = json.loads((plan_directory / "token-matching.json").read_bytes())
    for variant, (document, value) in records.items():
        expected = document["snapshot_sha256"]
        if variant == "A" and expected != planning["source_snapshot_sha256"]:
            raise ValueError("Canonical A changed after token planning")
        if variant in {"B", "C"}:
            from sakila_experiment.metadata.snapshots import normalize_export
            spec = json.loads((plan_directory / f"{variant}.annotations.json").read_bytes())
            baseline = json.loads((ROOT / "runs/database/baseline.json").read_bytes())
            for export in document["source_exports"]:
                folder = Path(export["path"])
                if sha256_bytes((folder / "export.json").read_bytes()) != export["sha256"]:
                    raise ValueError("Diagnostic MCP export changed")
                if normalize_export(folder, baseline, spec) != value:
                    raise ValueError("Diagnostic payload differs from its actual MCP export")
        folder = output / variant
        publish_artifact(folder / f"{expected}.json", canonical_json(value))
        selected = {**document, "snapshot_id": f"diagnostic-{variant}-{expected[:16]}", "variant_id": variant}
        if variant == "C":
            selected["business_card_repetitions"] = planning["C_business_card_repetitions"]
        publish_artifact(folder / "manifest.json", canonical_json(selected))
    b_document, b_value = records["B"]
    for variant, numerator in (("B-order1", 1), ("B-order2", 2)):
        value = copy.deepcopy(b_value)
        offset = len(value["descriptions"]) * numerator // 3
        value["descriptions"] = value["descriptions"][offset:] + value["descriptions"][:offset]
        content, folder = canonical_json(value), output / variant
        digest = sha256_bytes(content)
        document = {**b_document, "snapshot_id": f"diagnostic-{variant}-{digest[:16]}", "variant_id": variant,
                    "snapshot_sha256": digest, "payload_file": digest + ".json", "source_snapshot_sha256": b_document["snapshot_sha256"],
                    "transformation": "fixed_description_block_rotation", "rotation_offset": offset,
                    "transformation_source_sha256": sha256_bytes(Path(__file__).read_bytes())}
        publish_artifact(folder / document["payload_file"], content)
        publish_artifact(folder / "manifest.json", canonical_json(document))
    return {"status": "diagnostic_renderings_assembled_from_mcp", "generation_requests": 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("plan", "assemble"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/coder7b.toml")
    parser.add_argument("--plan-directory", type=Path)
    parser.add_argument("--b-directory", type=Path)
    parser.add_argument("--c-directory", type=Path)
    args = parser.parse_args()
    result = plan(args.source, args.output, args.config) if args.stage == "plan" else assemble(args.source, args.plan_directory, args.b_directory, args.c_directory, args.output)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
