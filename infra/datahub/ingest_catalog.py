"""Persist validated, fidelity-correct metadata in the actual DataHub catalog."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

os.environ["DATAHUB_TELEMETRY_ENABLED"] = "false"
from datahub.ingestion.run.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    source = ROOT / "runs/metadata/validated-ingestion.json"
    receipt = json.loads((ROOT / "runs/metadata/fidelity-receipt.json").read_text())
    if receipt["validation"]["status"] != "passed" or hashlib.sha256(source.read_bytes()).hexdigest() != receipt["output_sha256"]:
        print(json.dumps({"status": "ingestion_fidelity_receipt_mismatch"}))
        return 1
    verification = subprocess.run([str(ROOT / ".venv/bin/sakila-experiment"), "database", "verify", "--config", str(ROOT / "configs/local.toml"), "--baseline", str(ROOT / "runs/database/baseline.json")], cwd=ROOT, capture_output=True)
    if verification.returncode:
        print(json.dumps({"status": "database_baseline_verification_failed"}))
        return 1
    token = (ROOT / "secrets/datahub_token.txt").read_text().strip()
    configuration = {"source": {"type": "file", "config": {"path": str(source)}},
                     "sink": {"type": "datahub-rest", "config": {"server": "http://127.0.0.1:18080", "token": token}}}
    try:
        pipeline = Pipeline.create(configuration)
        pipeline.run()
        pipeline.raise_from_status()
    except Exception as error:
        print(json.dumps({"status": "catalog_ingestion_failed", "error_class": type(error).__name__, "redacted_error": str(error).replace(token, "[REDACTED]")[:1500]}))
        return 1
    report = {"status": "catalog_ingested", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "server": "http://127.0.0.1:18080", "input_sha256": receipt["output_sha256"],
              "ingestion_sdk_version": importlib.metadata.version("acryl-datahub"),
              "table_count_expected": receipt["validation"]["base_tables"],
              "columns_expected": receipt["validation"]["columns"], "foreign_keys_expected": receipt["validation"]["foreign_keys"],
              "mcp_retrieval_verified": False}
    output = ROOT / "runs/metadata/catalog-ingestion.json"
    with output.open("x") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

