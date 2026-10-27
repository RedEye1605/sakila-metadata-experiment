"""Vendor a release-pinned DataHub Compose file and derive a local-only topology.

Run with the isolated metadata tooling environment. This prepares files only;
it does not start DataHub or stop existing services.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
VERSION = "v1.8.0"
SOURCE = f"https://raw.githubusercontent.com/datahub-project/datahub/{VERSION}/docker/quickstart/docker-compose.quickstart-profile.yml"


def main() -> int:
    vendor = ROOT / "infra/datahub/vendor"
    vendor.mkdir(parents=True, exist_ok=True)
    source_path = vendor / "compose-v1.8.0.yaml"
    if source_path.exists():
        content = source_path.read_bytes()
    else:
        with urllib.request.urlopen(SOURCE, timeout=30) as response:
            content = response.read()
        source_path.write_bytes(content)
    document = yaml.safe_load(content)
    document["name"] = "sakila-metadata"
    document["services"].pop("datahub-actions-quickstart", None)
    limits = {"datahub-gms-quickstart": "2g", "frontend-quickstart": "1g", "kafka-broker": "1g", "mysql": "512m", "opensearch": "2g", "system-update-quickstart": "1536m"}
    for name, service in document["services"].items():
        service.pop("ports", None)
        if name == "datahub-gms-quickstart":
            service["ports"] = ["127.0.0.1:18080:8080"]
        elif name == "frontend-quickstart":
            service["ports"] = ["127.0.0.1:19002:9002"]
        # Do not mount ~/.aws or any pre-existing host plugin directories.
        if "volumes" in service:
            service["volumes"] = [mount for mount in service["volumes"] if mount.get("type") != "bind"]
        service["mem_limit"] = limits[name]
        environment = service.get("environment", {})
        if "UI_INGESTION_DEFAULT_CLI_VERSION" in environment:
            environment["UI_INGESTION_DEFAULT_CLI_VERSION"] = "1.7.0.17"
        if "DATAHUB_SYSTEM_CLIENT_SECRET" in environment:
            environment["DATAHUB_SYSTEM_CLIENT_SECRET"] = "${DATAHUB_SYSTEM_CLIENT_SECRET:?required}"
        if name in {"datahub-gms-quickstart", "frontend-quickstart", "system-update-quickstart"}:
            environment["METADATA_SERVICE_AUTH_ENABLED"] = "true"
        if name == "frontend-quickstart":
            environment["DATAHUB_SECRET"] = "${DATAHUB_FRONTEND_SECRET:?required}"
        if name == "mysql":
            service["command"] = ["--innodb-buffer-pool-size=128M", "--performance-schema=OFF"]
    for name, volume in document.get("volumes", {}).items():
        volume["name"] = "sakila-metadata-" + name
    for name, network in document.get("networks", {}).items():
        network["name"] = "sakila-metadata-" + name
    image_lock_path = ROOT / "infra/datahub/image-lock.json"
    if image_lock_path.is_file():
        lock = json.loads(image_lock_path.read_bytes())
        if lock["release"] != VERSION or set(lock["services"]) != set(document["services"]):
            raise ValueError("Image lock differs from the pinned deployment topology")
        for name, service in document["services"].items():
            if lock["services"][name]["original_reference"] != service["image"]:
                raise ValueError("Upstream image reference differs from the verified lock")
            service["image"] = lock["services"][name]["locked_reference"]
    derived = ROOT / "infra/datahub/compose.yaml"
    derived.write_text(yaml.safe_dump(document, sort_keys=False))
    secret_path = ROOT / "secrets/datahub.env"
    if not secret_path.exists():
        secret_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        values = {"DATAHUB_VERSION": VERSION, "DATAHUB_SYSTEM_CLIENT_SECRET": secrets.token_hex(32), "DATAHUB_TOKEN_SERVICE_SIGNING_KEY": secrets.token_hex(32), "DATAHUB_TOKEN_SERVICE_SALT": secrets.token_hex(32), "DATAHUB_FRONTEND_SECRET": secrets.token_hex(32)}
        fd = os.open(secret_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as handle:
            for key, value in values.items():
                handle.write(f"{key}={value}\n")
    result = subprocess.run(["docker", "compose", "--env-file", str(secret_path), "-f", str(derived), "--profile", "quickstart", "config", "--quiet"], capture_output=True)
    if result.returncode:
        print("Derived DataHub Compose configuration failed validation; no services started")
        return 1
    manifest = {"source_url": SOURCE, "release": VERSION, "source_sha256": hashlib.sha256(content).hexdigest(), "derived_sha256": hashlib.sha256(derived.read_bytes()).hexdigest(), "changes": ["loopback-only GMS and frontend ports", "unpublished internal service ports", "isolated named volumes and network", "removed host AWS/plugin mounts", "removed unused Actions worker", "enabled metadata-service authentication", "random local authentication secrets", "bounded container memory"], "runtime_verified": False}
    if image_lock_path.is_file():
        manifest["image_lock_sha256"] = hashlib.sha256(image_lock_path.read_bytes()).hexdigest()
    (ROOT / "infra/datahub/deployment-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"status": "prepared_and_config_validated", "release": VERSION, "runtime_verified": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

