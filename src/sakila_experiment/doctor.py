"""Read-only environment inspection; missing research services are explicit."""

from __future__ import annotations

import importlib.metadata
import json
import platform
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .config import AppConfig


def command_probe(arguments: list[str]) -> dict[str, Any]:
    if not shutil.which(arguments[0]):
        return {"status": "unavailable", "reason": "executable_not_found"}
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "unavailable", "reason": "command_failed_or_timed_out"}
    if result.returncode:
        return {"status": "unavailable", "reason": "nonzero_exit", "exit_code": result.returncode}
    return {"status": "ok", "output": result.stdout.strip()}


def tcp_probe(host: str, port: int) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=1):
            pass
    except OSError:
        return {"status": "unavailable", "reason": "connection_failed"}
    return {"status": "reachable", "note": "TCP reachability is not authentication or schema validation"}


def http_probe(url: str) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=2, trust_env=False, follow_redirects=False) as client:
            response = client.get(url)
    except httpx.HTTPError:
        return {"status": "unavailable", "reason": "request_failed"}
    return {"status": "ok" if response.status_code == 200 else "unavailable", "http_status": response.status_code}


def inspect_environment(config: AppConfig, *, services: bool = True) -> dict[str, Any]:
    packages = {}
    for name in ("sakila-metadata-experiment", "pydantic", "httpx", "pymysql", "sqlglot", "pytest"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    memory = {}
    if Path("/proc/meminfo").exists():
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                memory[key + "_bytes"] = int(value.split()[0]) * 1024
    disk = shutil.disk_usage(config.project_root)
    commands = {
        "docker": ["docker", "--version"],
        "compose": ["docker", "compose", "version"],
        "uv": ["uv", "--version"],
        "gpu": ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
        "nvidia_toolkit": ["nvidia-ctk", "--version"],
    }
    report: dict[str, Any] = {
        "report_schema_version": 1,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "memory": memory,
        "disk": {"total_bytes": disk.total, "free_bytes": disk.free},
        "packages": packages,
        "commands": {name: command_probe(args) for name, args in commands.items()},
        "design": config.experiment.model_dump(mode="json"),
        "readiness": {"main_experiment_ready": False, "reason": "requires independently validated frozen artifacts and runtime acceptance gates"},
    }
    if services:
        report["services"] = {
            "research_mysql": tcp_probe(config.database.host, config.database.port),
            "datahub_gms": http_probe(config.datahub.gms_url + "/health"),
            "llama_server": http_probe(config.inference.base_url + "/health"),
        }
    return report

