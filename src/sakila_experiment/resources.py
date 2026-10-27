"""Pause only the explicitly authorized Airflow project and always restore it."""

from __future__ import annotations

import json
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .artifacts import canonical_json, publish_artifact


def memory_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("Memory availability could not be measured")


@contextmanager
def pause_authorized_airflow(artifact_directory: Path):
    listing = subprocess.run([
        "docker", "ps", "--filter", "label=com.docker.compose.project=airflow-workshop",
        "--format", "{{json .}}",
    ], capture_output=True, text=True, check=True)
    containers = [json.loads(line) for line in listing.stdout.splitlines() if line]
    identities = [container["ID"] for container in containers]
    before = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "containers": [{"id": item["ID"], "name": item["Names"]} for item in containers], "available_bytes": memory_available_bytes()}
    publish_artifact(artifact_directory / "before.json", canonical_json(before))
    try:
        if identities:
            subprocess.run(["docker", "stop", "--time", "30", *identities], capture_output=True, check=True, timeout=90)
        yield {"paused_containers": before["containers"], "available_bytes": memory_available_bytes()}
    finally:
        # Start only containers that were running before this operation.
        if identities:
            subprocess.run(["docker", "start", *identities], capture_output=True, check=True, timeout=90)
        after = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "restored_containers": before["containers"], "available_bytes": memory_available_bytes()}
        publish_artifact(artifact_directory / "restored.json", canonical_json(after))

