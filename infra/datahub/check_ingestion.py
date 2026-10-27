"""Run the real MySQL connector into a local file, without a DataHub service.

This is connector diagnostics, NOT an MCP export or experimental snapshot.
Never writes database records or sends benchmark queries to the catalog.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

os.environ["DATAHUB_TELEMETRY_ENABLED"] = "false"
from datahub.ingestion.run.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    destination = ROOT / "runs/metadata/connector-diagnostic.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        print("Connector diagnostic already exists; refusing to overwrite")
        return 2
    configuration = {
        "source": {"type": "mysql", "config": {
            "host_port": "127.0.0.1:13306", "database": "sakila", "username": "metadata_reader",
            "password": (ROOT / "secrets/metadata_password.txt").read_text().strip(),
            "platform_instance": "sakila-research", "env": "DEV",
            "include_tables": True, "include_views": False,
            "include_stored_procedures": False, "include_usage_statistics": False,
            "include_view_lineage": False, "include_view_column_lineage": False,
            "profiling": {"enabled": False},
        }},
        "sink": {"type": "file", "config": {"filename": str(destination)}},
    }
    logging.getLogger().setLevel(logging.ERROR)
    try:
        pipeline = Pipeline.create(configuration)
        pipeline.run()
        pipeline.raise_from_status()
    except Exception as error:
        # Never print configuration or errors that could contain the password.
        messages = []
        current = error
        while current is not None:
            messages.append(str(current).replace(configuration["source"]["config"]["password"], "[REDACTED]")[:2000])
            current = current.__cause__
        print(json.dumps({"status": "connector_failed", "error_class": type(error).__name__, "redacted_details": messages}))
        return 1
    print(json.dumps({"status": "connector_diagnostic_complete", "output": str(destination), "mcp_snapshot": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

