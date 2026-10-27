"""Rebuild locked Python, official Sakila and snapshots in an isolated workspace.

Metadata is replayed from archived MCP evidence, not silently fetched through a
different API. A fresh DataHub catalog is explicitly outside this replay check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--port", type=int, default=13307)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.id) or not 1024 <= args.port <= 65535 or args.port in {3306, 13306}:
        raise ValueError("Use an isolated reproduction ID and a non-research loopback port")
    destination = args.output_directory.resolve()
    workspace = destination / "workspace"
    if destination.exists():
        raise FileExistsError("A reproduction directory already exists; choose a new ID/output")
    workspace.mkdir(parents=True)
    container = "sakila-repro-" + args.id + "-mysql"
    recorded = []
    names = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT, capture_output=True, check=True).stdout.split(b"\0")
    for raw in names:
        if not raw:
            continue
        relative = Path(raw.decode())
        source = ROOT / relative
        if source.is_file():
            (workspace / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, workspace / relative)
            recorded.append({"path": str(relative), "sha256": sha256_bytes(source.read_bytes())})
    for relative in ("downloads/sakila", "runs/metadata/exports"):
        shutil.copytree(ROOT / relative, workspace / relative)
    compose_path = workspace / "infra/compose.yaml"
    compose_path.write_text(compose_path.read_text().replace("name: sakila-research", "name: sakila-repro-" + args.id).replace("container_name: sakila-research-mysql", "container_name: " + container).replace("127.0.0.1:13306:3306", f"127.0.0.1:{args.port}:3306"))
    config = workspace / "configs/local.toml"
    config.write_text(config.read_text().replace("port = 13306", f"port = {args.port}"))
    publish_artifact(destination / "copied-source.json", canonical_json(recorded))
    commands = []
    repro_environment = dict(os.environ)
    for name in ("VIRTUAL_ENV", "PYTHONPATH", "UV_PROJECT", "SAKILA_READER_PASSWORD"):
        repro_environment.pop(name, None)
    repro_environment["UV_PROJECT_ENVIRONMENT"] = str(workspace / ".venv")
    def execute(arguments):
        result = subprocess.run(arguments, cwd=workspace, env=repro_environment, capture_output=True, text=True)
        index = len(commands)
        publish_artifact(destination / f"command-{index:02}.log", (result.stdout + result.stderr).encode())
        commands.append({"arguments": arguments, "exit_code": result.returncode, "log": f"command-{index:02}.log"})
        print(json.dumps({"stage": index, "exit_code": result.returncode, "command": arguments[:5]}), flush=True)
        if result.returncode:
            raise RuntimeError("Reproduction command failed; inspect the bounded stage log")
    try:
        execute(["uv", "sync", "--frozen", "--group", "analysis"])
        execute(["uv", "run", "--frozen", "sakila-experiment", "database", "bootstrap", "--container-name", container])
        execute(["uv", "run", "--frozen", "sakila-experiment", "database", "inspect", "--output", "runs/database/baseline.json"])
        actual = json.loads((workspace / "runs/database/baseline.json").read_bytes())
        expected = json.loads((ROOT / "runs/database/baseline.json").read_bytes())
        if any(actual[k] != expected[k] for k in ("schema_sha256", "ddl_sha256", "data_sha256", "server")):
            raise ValueError("Reproduced official Sakila differs from the frozen research database")
        for scenario in ("S0", "S1", "S2", "S3"):
            execute(["uv", "run", "--frozen", "sakila-experiment", "metadata", "snapshot-build", "--first-export", f"runs/metadata/exports/{scenario}-a",
                     "--second-export", f"runs/metadata/exports/{scenario}-b", "--audit", "runs/database/baseline.json", "--spec", "data/annotations/specification.json", "--output-directory", "snapshots/reproduced"])
            expected_snapshot = json.loads((ROOT / "snapshots/candidates-v2" / scenario / "manifest.json").read_bytes())
            actual_snapshot = json.loads((workspace / "snapshots/reproduced" / scenario / "manifest.json").read_bytes())
            if expected_snapshot["snapshot_sha256"] != actual_snapshot["snapshot_sha256"]:
                raise ValueError("Replayed MCP snapshot payload differs")
        execute(["uv", "run", "--frozen", "sakila-experiment", "metadata", "validate-set", "--snapshot-root", "snapshots/reproduced", "--output", "runs/metadata/replayed-validation.json"])
        execute(["uv", "run", "--frozen", "--group", "analysis", "pytest", "-q", "--run-integration"])
        report = {"status": "reproduction_verified", "python_environment": "new workspace with frozen lock", "database": "fresh isolated official import",
                  "database_port": args.port, "container": container, "database_schema_sha256": actual["schema_sha256"], "database_data_sha256": actual["data_sha256"],
                  "mcp_snapshot_payloads_identical": True, "fresh_datahub_catalog_tested": False, "model_generation_requests": 0, "commands": commands,
                  "topology_changes": ["separate Compose project/container/volume", "separate loopback port", "new private generated credentials"],
                  "limitation": "Replays archived actual MCP exports; does not claim a fresh DataHub ingestion or a new model pilot"}
        publish_artifact(destination / "report.json", canonical_json(report))
        print(json.dumps({k: report[k] for k in ("status", "mcp_snapshot_payloads_identical", "model_generation_requests")}))
    except BaseException:
        publish_artifact(destination / "failure.json", canonical_json({"status": "reproduction_failed", "commands": commands, "model_generation_requests": 0}))
        raise
    finally:
        result = subprocess.run(["docker", "compose", "-f", str(compose_path), "stop"], capture_output=True)
        publish_artifact(destination / "cleanup.json", canonical_json({"container_stopped": result.returncode == 0, "volumes_preserved": True}))


if __name__ == "__main__":
    main()
