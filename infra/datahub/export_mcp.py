from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ["DATAHUB_TELEMETRY_ENABLED"] = "false"

from sakila_experiment.metadata.mcp_client import export_metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=("S0", "S1", "S2", "S3"), required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--spec", type=Path, help="Versioned authoring specification whose glossary scope is retrieved")
    args = parser.parse_args()
    bundle = asyncio.run(export_metadata(ROOT, args.scenario, args.output_directory.resolve(), page_size=args.page_size, specification_path=args.spec))
    print(json.dumps({"status": "mcp_export_complete", "scenario": args.scenario, "datasets": len(bundle["dataset_urns"]), "tool_calls": len(bundle["calls"])}))

