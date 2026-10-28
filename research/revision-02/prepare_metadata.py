"""Apply a versioned spec and audit two real MCP exports per condition."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.metadata.snapshots import build_candidate, validate_scenario_set

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scenarios", nargs="+", choices=("S0", "S1", "S2", "S3"), default=["S0", "S1", "S2", "S3"])
    args = parser.parse_args()
    spec, output = args.spec.resolve(), args.output.resolve()
    if output.exists():
        raise FileExistsError("Use a new metadata preparation directory")
    specification = json.loads(spec.read_bytes())
    audit = json.loads((ROOT / "runs/database/baseline.json").read_bytes())
    expected_targets = {table["name"] for table in audit["technical_schema"]["tables"]}
    expected_targets.update(table["name"] + "." + column["name"] for table in audit["technical_schema"]["tables"] for column in table["columns"])
    targets = [annotation["element_id"] for annotation in specification["annotations"]]
    if set(targets) != expected_targets or len(targets) != len(expected_targets):
        raise ValueError("Annotation target coverage differs from the installed schema")
    spec_hash = sha256_bytes(spec.read_bytes())
    py = ROOT / "environments/metadata/.venv/bin/python"
    for scenario in args.scenarios:
        if sha256_bytes(spec.read_bytes()) != spec_hash:
            raise ValueError("Authoring spec changed during metadata preparation")
        print(json.dumps({"stage": "write_catalog", "scenario": scenario}), flush=True)
        subprocess.run([str(py), "infra/datahub/apply_annotations.py", "--scenario", scenario, "--receipt", str(output / "writes" / (scenario + ".json")), "--spec", str(spec)], cwd=ROOT, check=True)
        for suffix in ("a", "b"):
            subprocess.run([str(py), "infra/datahub/export_mcp.py", "--scenario", scenario, "--spec", str(spec), "--output-directory", str(output / "exports" / (scenario + "-" + suffix))], cwd=ROOT, check=True)
        manifest = build_candidate(output / "exports" / (scenario + "-a"), output / "exports" / (scenario + "-b"), audit, specification, output / "snapshots")
        print(json.dumps({"stage": "snapshot_built", "scenario": scenario, "snapshot_sha256": manifest["snapshot_sha256"]}), flush=True)
    if args.scenarios == ["S0", "S1", "S2", "S3"]:
        report = validate_scenario_set(output / "snapshots")
        publish_artifact(output / "validation.json", canonical_json(report))
        print(json.dumps({"stage": "candidate_set_validated", "human_review_complete": False}), flush=True)


if __name__ == "__main__":
    main()
